from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.local_service import handle_request
from redaction_assistant.office_converter import convert_legacy_office_files
from redaction_assistant.user_batch import collect_user_inputs


class M23OfficeConversionAndJobControlTests(unittest.TestCase):
    def test_input_plan_marks_legacy_office_as_convertible_not_unsupported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "legacy.doc").write_bytes(b"legacy")
            (root / "legacy.xls").write_bytes(b"legacy")
            (root / "legacy.wps").write_bytes(b"legacy")
            (root / "notes.txt").write_text("项目名称：南网示范项目", encoding="utf-8")

            plan = collect_user_inputs([root])

        self.assertEqual(plan["processable_count"], 1)
        self.assertEqual(plan["convertible_count"], 3)
        self.assertEqual(plan["unsupported_count"], 0)
        self.assertEqual(
            {item["target_extension"] for item in plan["convertible_files"]},
            {".docx", ".xlsx"},
        )

    def test_office_converter_invokes_converter_and_returns_converted_paths(self):
        calls = []

        def fake_runner(command, **_kwargs):
            calls.append(command)
            outdir = Path(command[command.index("--outdir") + 1])
            source = Path(command[-1])
            target_suffix = ".xlsx" if source.suffix.lower() == ".xls" else ".docx"
            (outdir / f"{source.stem}{target_suffix}").write_bytes(_minimal_docx_bytes("项目名称：转换后项目"))
            return type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "legacy.doc"
            source.write_bytes(b"legacy")
            converter = root / "soffice.exe"
            converter.write_bytes(b"fake")

            result = convert_legacy_office_files(
                [source],
                workspace=root / "converted",
                converter=converter,
                runner=fake_runner,
            )

        self.assertEqual(result["converted_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(Path(result["converted_files"][0]["converted_path"]).suffix, ".docx")
        self.assertIn("--headless", calls[0])

    def test_local_service_can_cancel_running_job(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            for idx in range(20):
                (source / f"file_{idx:02d}.txt").write_text(f"项目名称：南网示范项目{idx}", encoding="utf-8")

            def slow_build(*args, **kwargs):
                progress_cb = kwargs.get("progress_cb")
                for idx in range(1, 21):
                    if progress_cb:
                        progress_cb({"stage": "start", "current": idx, "total": 20, "file_name": f"file_{idx:02d}.txt"})
                    time.sleep(0.02)
                return {"source_file_manifest": [], "redacted_text_blocks": []}, {"items": []}

            with patch("redaction_assistant.local_service.build_redaction_package", side_effect=slow_build):
                started = handle_request({
                    "action": "start_build_package",
                    "input_paths": [str(source)],
                    "project_alias_id": "M23-CANCEL",
                    "out": str(root / "out"),
                    "ocr_mode": "quick",
                })
                self.assertTrue(started["success"], started)
                job_id = started["result"]["job_id"]
                cancelled = handle_request({"action": "cancel_job", "job_id": job_id})
                self.assertTrue(cancelled["success"], cancelled)

                final = {}
                for _ in range(80):
                    final = handle_request({"action": "job_status", "job_id": job_id})
                    if final.get("result", {}).get("status") in {"cancelled", "completed", "failed"}:
                        break
                    time.sleep(0.02)

        self.assertEqual(final["result"]["status"], "cancelled")

    def test_local_service_can_retry_failed_job_with_same_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "project.txt").write_text("项目名称：南网示范项目", encoding="utf-8")
            attempts = {"count": 0}

            def flaky_outputs(*args, **kwargs):
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise PermissionError("first failure")
                output = Path(args[1])
                output.mkdir(parents=True, exist_ok=True)
                package = output / "redaction_upload_package.json"
                package.write_text("{}", encoding="utf-8")
                return {"package": package, "output_dir": output}

            with patch("redaction_assistant.local_service._build_outputs", side_effect=flaky_outputs):
                started = handle_request({
                    "action": "start_build_package",
                    "input_paths": [str(source)],
                    "project_alias_id": "M23-RETRY",
                    "out": str(root / "out"),
                    "ocr_mode": "quick",
                })
                job_id = started["result"]["job_id"]
                failed = _wait_for_terminal(job_id)
                self.assertEqual(failed["result"]["status"], "failed")

                retried = handle_request({"action": "retry_job", "job_id": job_id})
                self.assertTrue(retried["success"], retried)
                retry_id = retried["result"]["job_id"]
                completed = _wait_for_terminal(retry_id)

        self.assertEqual(completed["result"]["status"], "completed")
        self.assertEqual(attempts["count"], 2)

    def test_desktop_shell_exposes_cancel_retry_and_auto_conversion(self):
        with tempfile.TemporaryDirectory() as td:
            shell = build_desktop_shell(Path(td), version="0.23.0-m23", service_url="http://127.0.0.1:8765")
            index = (shell / "index.html").read_text(encoding="utf-8")

        self.assertIn("/cancel-job", index)
        self.assertIn("/retry-job", index)
        self.assertIn("enable_conversion: true", index)
        self.assertIn("取消当前任务", index)
        self.assertIn("重试失败任务", index)


def _wait_for_terminal(job_id: str) -> dict:
    status = {}
    for _ in range(80):
        status = handle_request({"action": "job_status", "job_id": job_id})
        if status.get("result", {}).get("status") in {"completed", "failed", "cancelled"}:
            return status
        time.sleep(0.02)
    return status


def _minimal_docx_bytes(text: str) -> bytes:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        zf.writestr(
            "word/document.xml",
            f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>',
        )
    return buf.getvalue()


if __name__ == "__main__":
    unittest.main()

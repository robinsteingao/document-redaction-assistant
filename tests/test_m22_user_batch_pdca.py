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
from redaction_assistant.registration import build_registration_request, write_registration_request
from redaction_assistant.ocr_adapter import extract_text_with_ocr
from redaction_assistant.rules import amount_range
from redaction_assistant.user_batch import collect_user_inputs, ocr_max_pages_for_mode
from redaction_assistant.workflow import build_redaction_package


class M22UserBatchPDCATest(unittest.TestCase):
    def test_directory_input_plan_marks_doc_for_conversion_and_skips_noise(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "project.docx").write_bytes(_docx_bytes("项目名称：南网示范项目"))
            (root / "legacy.doc").write_bytes(b"legacy office content")
            (root / "archive.zip").write_bytes(b"zip")
            (root / "copy_manifest.json").write_text("{}", encoding="utf-8")
            (root / "Thumbs.db").write_bytes(b"db")
            nested = root / "nested"
            nested.mkdir()
            (nested / "evidence.pdf").write_bytes("%PDF-1.4\nBT (合同金额：100万元) Tj ET\n%%EOF".encode("utf-8"))

            plan = collect_user_inputs([root])

        self.assertEqual(plan["processable_count"], 2)
        self.assertEqual(plan["convertible_count"], 1)
        self.assertEqual(plan["unsupported_count"], 0)
        self.assertEqual(plan["skipped_count"], 3)
        self.assertEqual(plan["by_extension"][".docx"], 1)
        self.assertEqual(plan["by_extension"][".pdf"], 1)
        self.assertEqual(plan["convertible_files"][0]["extension"], ".doc")
        self.assertEqual(plan["convertible_files"][0]["reason"], "office_conversion_required")

    def test_ocr_quick_mode_limits_pdf_pages_without_global_environment(self):
        class FakeOcr:
            def __call__(self, path):
                return [([0, 0, 1, 1], Path(path).stem, 0.9)], None

        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "scan.pdf"
            pdf.write_bytes(b"%PDF-1.4\n/Image\n%%EOF")

            with patch.dict("os.environ", {"DRA_OCR_ENGINE": "rapidocr"}):
                result = extract_text_with_ocr(
                    pdf,
                    engine_loader=lambda _name: FakeOcr(),
                    max_pages=ocr_max_pages_for_mode("quick"),
                )

        self.assertIn(result["status"], {"ok", "empty", "unsupported", "failed"})
        if result["status"] == "ok":
            self.assertEqual(result["pages_processed"], 1)

    def test_workflow_progress_callback_reports_each_file_and_ocr_mode(self):
        events = []
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / "a.txt"
            second = root / "b.txt"
            first.write_text("项目名称：南网示范项目\n合同金额：100万元", encoding="utf-8")
            second.write_text("承担单位：广东电网有限责任公司", encoding="utf-8")

            package, _mapping = build_redaction_package(
                [first, second],
                project_alias_id="M22-PROGRESS",
                ocr_max_pages=1,
                progress_cb=lambda event: events.append(event),
            )

        self.assertEqual(package["project_alias_id"], "M22-PROGRESS")
        self.assertEqual([e["stage"] for e in events], ["start", "done", "start", "done"])
        self.assertEqual(events[-1]["current"], 2)
        self.assertEqual(events[-1]["total"], 2)

    def test_local_service_starts_background_job_and_reports_progress(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "project.txt").write_text("项目名称：南网示范项目\n合同金额：100万元", encoding="utf-8")
            out = root / "out"
            registration_dir = root / "registration"
            write_registration_request(registration_dir, build_registration_request(email="tester@example.com"))

            started = handle_request({
                "action": "start_build_package",
                "input_paths": [str(source)],
                "project_alias_id": "M22-JOB",
                "out": str(out),
                "ocr_mode": "quick",
                "registration_dir": str(registration_dir),
            })
            self.assertTrue(started["success"], started)
            job_id = started["result"]["job_id"]

            status = {}
            for _ in range(50):
                status = handle_request({"action": "job_status", "job_id": job_id})
                if status.get("result", {}).get("status") in {"completed", "failed"}:
                    break
                time.sleep(0.05)

            self.assertTrue(status["success"], status)
            self.assertEqual(status["result"]["status"], "completed")
            self.assertTrue(Path(status["result"]["outputs"]["package"]).exists())
            self.assertGreaterEqual(status["result"]["progress"]["total"], 1)
            self.assertIn("duration_seconds", status["result"])
            self.assertIn("output_dir", status["result"]["outputs"])

    def test_relative_output_dir_is_written_under_user_output_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            output_root = root / "user_documents_output"
            source.mkdir()
            (source / "project.txt").write_text("项目名称：南网示范项目", encoding="utf-8")
            registration_dir = root / "registration"
            write_registration_request(registration_dir, build_registration_request(email="tester@example.com"))

            with patch.dict("os.environ", {"DRA_OUTPUT_ROOT": str(output_root)}):
                response = handle_request({
                    "action": "build_package",
                    "input_paths": [str(source)],
                    "project_alias_id": "M22-RELATIVE-OUT",
                    "out": "desktop_output",
                    "ocr_mode": "quick",
                    "registration_dir": str(registration_dir),
                })

            self.assertTrue(response["success"], response)
            output_dir = Path(response["result"]["output_dir"])
            self.assertEqual(output_dir, output_root / "desktop_output")
            self.assertTrue((output_dir / "redaction_upload_package.json").exists())

    def test_plan_inputs_endpoint_matches_no_developer_user_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "project.txt").write_text("项目名称：南网示范项目", encoding="utf-8")
            response = handle_request({"action": "plan_inputs", "input_paths": [str(root)]})

        self.assertTrue(response["success"], response)
        self.assertEqual(response["result"]["processable_count"], 1)
        self.assertIn("quick", response["result"]["recommended_ocr_modes"])

    def test_desktop_shell_exposes_pdca_user_flow_controls(self):
        with tempfile.TemporaryDirectory() as td:
            shell = build_desktop_shell(Path(td), version="0.22.0-m22", service_url="http://127.0.0.1:8765")
            index = (shell / "index.html").read_text(encoding="utf-8")

        self.assertIn("inputPaths", index)
        self.assertIn("ocrMode", index)
        self.assertIn("/plan-inputs", index)
        self.assertIn("/start-build", index)
        self.assertIn("/job-status", index)
        self.assertIn("预检文件", index)
        self.assertIn("处理进度摘要", index)
        self.assertIn("文档安全脱敏助手输出", index)
        self.assertIn("outputs.output_dir", index)
        self.assertIn("formatPlanResult", index)
        self.assertIn("formatJobStatus", index)
        self.assertIn("原始详情（供技术支持复制", index)

    def test_amount_range_hint_does_not_republish_original_amount_string(self):
        originals = ["3万元", "5万元", "10万元", "100万元"]
        replacements = [amount_range(value) for value in originals]
        for replacement in replacements:
            for original in originals:
                self.assertNotIn(original, replacement)


def _docx_bytes(text: str) -> bytes:
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

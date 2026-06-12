import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.local_service import handle_request
from redaction_assistant.registration import build_registration_request, write_registration_request
from redaction_assistant.ocr_adapter import extract_text_with_ocr, get_ocr_status
from redaction_assistant.workflow import build_redaction_package


class FakeOcrEngine:
    name = "fake_ocr"

    def extract_text(self, path: Path) -> dict:
        return {
            "status": "ok",
            "engine": self.name,
            "text": "项目名称：扫描件项目。合同金额：120万元。技术指标：现场试运行30天。",
            "confidence": 0.91,
        }


class FakeRenderedPage:
    def to_pil(self):
        return self

    def save(self, path: str):
        Path(path).write_bytes(b"fake-rendered-image")


class FakePdfPage:
    def render(self, scale: float = 2.0):
        return FakeRenderedPage()


class FakePdfDocument:
    def __init__(self, path: str):
        self.path = path

    def __len__(self):
        return 1

    def __getitem__(self, index: int):
        if index != 0:
            raise IndexError(index)
        return FakePdfPage()

    def close(self):
        return None


class M6OcrAndComponentsTests(unittest.TestCase):
    def test_injected_ocr_engine_extracts_text_for_scanned_file(self):
        with tempfile.TemporaryDirectory() as td:
            scan = Path(td) / "scan.pdf"
            scan.write_bytes(b"%PDF-1.4\n/Type /XObject /Subtype /Image\nstream\nbinary\nendstream\n%%EOF")

            result = extract_text_with_ocr(scan, engine=FakeOcrEngine())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["engine"], "fake_ocr")
        self.assertIn("扫描件项目", result["text"])
        self.assertGreater(result["confidence"], 0.9)

    def test_rapidocr_pdf_input_is_rendered_to_image_before_ocr(self):
        previous_engine = os.environ.get("DRA_OCR_ENGINE")
        previous_pdfium = sys.modules.get("pypdfium2")
        captured_targets: list[Path] = []

        class FakeRapidOcr:
            def __call__(self, target: str):
                captured_targets.append(Path(target))
                return [[None, "PDF OCR TEXT", 0.88]], None

        try:
            os.environ["DRA_OCR_ENGINE"] = "rapidocr"
            sys.modules["pypdfium2"] = types.SimpleNamespace(PdfDocument=FakePdfDocument)
            with tempfile.TemporaryDirectory() as td:
                pdf = Path(td) / "scan.pdf"
                pdf.write_bytes(b"%PDF-1.7\n/Type /XObject /Subtype /Image\n%%EOF")

                result = extract_text_with_ocr(pdf, engine_loader=lambda name: FakeRapidOcr())

            self.assertEqual(result["status"], "ok")
            self.assertIn("PDF OCR TEXT", result["text"])
            self.assertTrue(captured_targets)
            self.assertEqual(captured_targets[0].suffix.lower(), ".png")
        finally:
            if previous_engine is None:
                os.environ.pop("DRA_OCR_ENGINE", None)
            else:
                os.environ["DRA_OCR_ENGINE"] = previous_engine
            if previous_pdfium is None:
                sys.modules.pop("pypdfium2", None)
            else:
                sys.modules["pypdfium2"] = previous_pdfium

    def test_local_service_build_package_and_ocr_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "input.txt"
            out = root / "out"
            registration_dir = root / "registration"
            write_registration_request(registration_dir, build_registration_request(email="tester@example.com"))
            source.write_text("项目名称：配网智能监测项目。合同金额：350万元。技术指标：10kV试运行30天。", encoding="utf-8")

            status_response = handle_request({"action": "ocr_status"})
            package_response = handle_request({
                "action": "build_package",
                "project_alias_id": "project_m6",
                "files": [str(source)],
                "out": str(out),
                "registration_dir": str(registration_dir),
            })

            self.assertTrue(status_response["success"])
            self.assertEqual(status_response["result"]["required_for_text_pdf"], False)
            self.assertTrue(package_response["success"])
            self.assertTrue(Path(package_response["result"]["package"]).exists())
            package = json.loads(Path(package_response["result"]["package"]).read_text(encoding="utf-8"))
            serialized = json.dumps(package, ensure_ascii=False)
            self.assertNotIn("配网智能监测项目", serialized)
            self.assertIn("10kV", serialized)

    def test_build_package_uses_available_ocr_for_scanned_pdf(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scan = root / "scan.pdf"
            scan.write_bytes(b"%PDF-1.7\n/Type /XObject /Subtype /Image\n%%EOF")

            with patch(
                "redaction_assistant.workflow.extract_text_with_ocr",
                return_value={
                    "status": "ok",
                    "engine": "rapidocr",
                    "text": "扫描件项目合同金额120万元，技术指标试运行30天。",
                    "confidence": 0.93,
                    "pages_processed": 1,
                },
                create=True,
            ):
                package, _mapping = build_redaction_package([scan], project_alias_id="ocr_pdf")

            self.assertEqual(package["source_file_manifest"][0]["parser_status"], "ok")
            self.assertIn("ocr_applied", package["source_file_manifest"][0]["warnings"])
            serialized = json.dumps(package, ensure_ascii=False)
            self.assertIn("扫描件项目", serialized)
            self.assertIn("试运行30天", serialized)

    def test_desktop_shell_binds_to_local_service_contract(self):
        with tempfile.TemporaryDirectory() as td:
            shell = build_desktop_shell(Path(td), version="0.6.0-m6", service_url="http://127.0.0.1:8765")
            index = (shell / "index.html").read_text(encoding="utf-8")
            config = json.loads((shell / "app_config.json").read_text(encoding="utf-8"))

        self.assertEqual(config["backend"], "local_service")
        self.assertEqual(config["service_url"], "http://127.0.0.1:8765")
        self.assertIn("fetch", index)
        self.assertIn("/ocr-status", index)
        self.assertIn("/plan-inputs", index)
        self.assertIn("/start-build", index)
        self.assertIn("serviceStatus", index)


if __name__ == "__main__":
    unittest.main()

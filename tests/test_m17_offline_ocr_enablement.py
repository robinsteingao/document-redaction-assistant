import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.commercial_package import build_commercial_install_package
from redaction_assistant.offline_ocr_install import (
    build_offline_ocr_install_plan,
    validate_offline_ocr_enablement,
)


class M17OfflineOcrEnablementTests(unittest.TestCase):
    def test_builds_offline_ocr_install_plan_from_wheelhouse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app_dir = root / "app"
            wheelhouse = app_dir / "ocr_engines" / "wheelhouse"
            wheelhouse.mkdir(parents=True)
            (wheelhouse / "paddlepaddle-2.6.2-cp311-cp311-win_amd64.whl").write_bytes(b"wheel")
            (wheelhouse / "paddleocr-2.8.1.tar.gz").write_bytes(b"source")
            (wheelhouse / "ch_PP-OCRv4_det_infer.tar").write_bytes(b"model")
            (app_dir / "runtime" / "python").mkdir(parents=True)
            (app_dir / "runtime" / "python" / "python.exe").write_bytes(b"python")

            result = build_offline_ocr_install_plan(app_dir, engine="paddleocr")
            plan = json.loads(result["plan"].read_text(encoding="utf-8"))
            env = result["env"].read_text(encoding="utf-8")

            self.assertEqual(plan["schema_version"], "document_redaction_offline_ocr_install_plan.v1")
            self.assertEqual(plan["engine"], "paddleocr")
            self.assertTrue(plan["install_commands"])
            self.assertIn("--no-index", plan["install_commands"][0])
            self.assertIn("DRA_OCR_ENGINE=paddleocr", env)
            self.assertIn("ch_PP-OCRv4_det_infer.tar", [item["name"] for item in plan["model_files"]])

    def test_validate_offline_ocr_enablement_reports_missing_install_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app_dir = root / "app"
            wheelhouse = app_dir / "ocr_engines" / "wheelhouse"
            wheelhouse.mkdir(parents=True)
            (wheelhouse / "paddlepaddle-2.6.2-cp311-cp311-win_amd64.whl").write_bytes(b"wheel")
            (wheelhouse / "paddleocr-2.8.1.tar.gz").write_bytes(b"source")
            (app_dir / "runtime" / "python").mkdir(parents=True)
            (app_dir / "runtime" / "python" / "python.exe").write_bytes(b"python")
            build_offline_ocr_install_plan(app_dir, engine="paddleocr")

            validation = validate_offline_ocr_enablement(app_dir)

            self.assertEqual(validation["status"], "not_enabled")
            reasons = {issue["reason"] for issue in validation["issues"]}
            self.assertIn("missing_install_marker", reasons)

    def test_rapidocr_install_plan_includes_pdf_renderer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app_dir = root / "app"
            wheelhouse = app_dir / "ocr_engines" / "wheelhouse"
            wheelhouse.mkdir(parents=True)
            (wheelhouse / "rapidocr_onnxruntime-1.4.4-py3-none-any.whl").write_bytes(b"rapidocr")
            (wheelhouse / "pypdfium2-5.0.0-py3-none-win_amd64.whl").write_bytes(b"pdfium")
            (app_dir / "runtime" / "python").mkdir(parents=True)
            (app_dir / "runtime" / "python" / "python.exe").write_bytes(b"python")

            result = build_offline_ocr_install_plan(app_dir, engine="rapidocr")
            plan = json.loads(result["plan"].read_text(encoding="utf-8"))

            self.assertIn("rapidocr-onnxruntime", plan["install_commands"][0])
            self.assertIn("pypdfium2", plan["install_commands"][0])

    def test_commercial_package_contains_offline_ocr_enablement_scripts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            python_runtime = root / "python_runtime"
            ocr_wheelhouse = root / "ocr_wheelhouse"
            office_runtime = root / "office_runtime"
            python_runtime.mkdir()
            ocr_wheelhouse.mkdir()
            office_runtime.mkdir()
            (python_runtime / "python.exe").write_bytes(b"python-runtime")
            (ocr_wheelhouse / "paddlepaddle-2.6.2-cp311-cp311-win_amd64.whl").write_bytes(b"wheel")
            (ocr_wheelhouse / "paddleocr-2.8.1.tar.gz").write_bytes(b"source")
            (office_runtime / "soffice.exe").write_bytes(b"office-runtime")

            result = build_commercial_install_package(
                root / "release",
                version="0.17.0-m17",
                python_runtime_dir=python_runtime,
                ocr_wheelhouse_dir=ocr_wheelhouse,
                office_runtime_dir=office_runtime,
            )
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["commands"]["offline_ocr_install"], "app\\install_offline_ocr.bat")
            self.assertEqual(manifest["commands"]["offline_ocr_validation"], "app\\validate_offline_ocr.bat")
            self.assertTrue((package_dir / "app" / "install_offline_ocr.bat").exists())
            self.assertTrue((package_dir / "app" / "validate_offline_ocr.bat").exists())
            self.assertTrue((package_dir / "app" / "ocr_engines" / "offline_ocr_install_plan.json").exists())


if __name__ == "__main__":
    unittest.main()

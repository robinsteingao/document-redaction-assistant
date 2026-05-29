import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.commercial_package import (
    build_commercial_install_package,
    validate_commercial_install_package,
)


class M16CommercialOfflinePackageTests(unittest.TestCase):
    def test_commercial_package_can_embed_required_offline_components(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            python_runtime = root / "python_runtime"
            ocr_wheelhouse = root / "ocr_wheelhouse"
            office_runtime = root / "office_runtime"
            python_runtime.mkdir()
            ocr_wheelhouse.mkdir()
            office_runtime.mkdir()
            (python_runtime / "python.exe").write_bytes(b"python-runtime")
            (ocr_wheelhouse / "rapidocr_onnxruntime-1.0.0-py3-none-any.whl").write_bytes(b"rapidocr-wheel")
            (office_runtime / "soffice.exe").write_bytes(b"office-runtime")

            result = build_commercial_install_package(
                root / "release",
                version="0.16.0-m16",
                python_runtime_dir=python_runtime,
                ocr_wheelhouse_dir=ocr_wheelhouse,
                office_runtime_dir=office_runtime,
            )
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "commercial_release_manifest.json").read_text(encoding="utf-8"))
            install_manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            validation = validate_commercial_install_package(package_dir)

            self.assertEqual(manifest["offline_status"], "complete_offline")
            self.assertTrue((package_dir / "app" / "runtime" / "python" / "python.exe").exists())
            self.assertTrue((package_dir / "app" / "ocr_engines" / "wheelhouse" / "rapidocr_onnxruntime-1.0.0-py3-none-any.whl").exists())
            self.assertTrue((package_dir / "app" / "office_runtime" / "soffice.exe").exists())
            self.assertEqual(install_manifest["package_type"], "complete_offline_commercial_package")
            self.assertEqual(validation["status"], "valid")

    def test_commercial_package_validation_reports_missing_components(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = build_commercial_install_package(root / "release", version="0.16.0-m16")
            package_dir = result["package_dir"]

            manifest = json.loads((package_dir / "commercial_release_manifest.json").read_text(encoding="utf-8"))
            validation = validate_commercial_install_package(package_dir)

            self.assertEqual(manifest["offline_status"], "staging_required")
            self.assertEqual(validation["status"], "invalid")
            reasons = {issue["reason"] for issue in validation["issues"]}
            self.assertIn("missing_embedded_python", reasons)
            self.assertIn("missing_ocr_wheelhouse", reasons)
            self.assertIn("missing_office_converter", reasons)

    def test_commercial_package_exposes_customer_friendly_offline_scripts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            python_runtime = root / "python_runtime"
            ocr_wheelhouse = root / "ocr_wheelhouse"
            office_runtime = root / "office_runtime"
            python_runtime.mkdir()
            ocr_wheelhouse.mkdir()
            office_runtime.mkdir()
            (python_runtime / "python.exe").write_bytes(b"python-runtime")
            (ocr_wheelhouse / "rapidocr_demo-0.0.1-py3-none-any.whl").write_bytes(b"rapidocr-wheel")
            (office_runtime / "soffice.exe").write_bytes(b"office-runtime")

            result = build_commercial_install_package(
                root / "release",
                version="0.16.0-m16",
                python_runtime_dir=python_runtime,
                ocr_wheelhouse_dir=ocr_wheelhouse,
                office_runtime_dir=office_runtime,
            )
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["commands"]["commercial_validation"], "app\\validate_commercial_package.bat")
            self.assertEqual(manifest["commands"]["offline_app"], "app\\start_offline_app.bat")
            self.assertIn("complete_offline_commercial_package", manifest["capabilities"])
            self.assertTrue((package_dir / "app" / "validate_commercial_package.bat").exists())
            self.assertTrue((package_dir / "app" / "start_offline_app.bat").exists())

    def test_office_runtime_keeps_libreoffice_parent_layout_when_program_dir_is_provided(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            python_runtime = root / "python_runtime"
            ocr_wheelhouse = root / "ocr_wheelhouse"
            libreoffice = root / "LibreOffice"
            program = libreoffice / "program"
            share = libreoffice / "share"
            python_runtime.mkdir()
            ocr_wheelhouse.mkdir()
            program.mkdir(parents=True)
            share.mkdir()
            (python_runtime / "python.exe").write_bytes(b"python-runtime")
            (ocr_wheelhouse / "rapidocr_demo-0.0.1-py3-none-any.whl").write_bytes(b"rapidocr-wheel")
            (program / "soffice.exe").write_bytes(b"office-runtime")
            (share / "registry.xcd").write_bytes(b"share")

            result = build_commercial_install_package(
                root / "release",
                version="0.23.0-m23",
                python_runtime_dir=python_runtime,
                ocr_wheelhouse_dir=ocr_wheelhouse,
                office_runtime_dir=program,
            )
            package_dir = result["package_dir"]
            office_manifest = json.loads(
                (package_dir / "app" / "office_runtime" / "office_runtime_manifest.json").read_text(encoding="utf-8")
            )

            self.assertTrue((package_dir / "app" / "office_runtime" / "program" / "soffice.exe").exists())
            self.assertTrue((package_dir / "app" / "office_runtime" / "share" / "registry.xcd").exists())
            self.assertEqual(office_manifest["converter"], "program/soffice.exe")


if __name__ == "__main__":
    unittest.main()

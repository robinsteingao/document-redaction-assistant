import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.offline_runtime import build_ocr_wheelhouse_bundle, stage_python_runtime
from redaction_assistant.install_package import build_install_package


class M12RuntimeOcrBundleTests(unittest.TestCase):
    def test_stage_python_runtime_copies_executable_and_updates_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "python.exe"
            runtime_dir = root / "runtime"
            source.write_bytes(b"fake-python-runtime")

            result = stage_python_runtime(source, runtime_dir, version="0.12.0-m12")
            manifest = json.loads((runtime_dir / "runtime_manifest.json").read_text(encoding="utf-8"))
            files_manifest = json.loads((runtime_dir / "runtime_files_manifest.json").read_text(encoding="utf-8"))

        self.assertTrue(result["python_exe"].name == "python.exe")
        self.assertTrue(manifest["bundled_python"])
        self.assertEqual(manifest["runtime_mode"], "embedded_python")
        self.assertIn("python/python.exe", [item["path"] for item in files_manifest["files"]])

    def test_build_ocr_wheelhouse_bundle_indexes_local_dependency_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wheelhouse = root / "wheelhouse"
            out = root / "ocr_engines"
            wheelhouse.mkdir()
            (wheelhouse / "rapidocr_onnxruntime-1.0.0-py3-none-any.whl").write_bytes(b"rapidocr-wheel")
            (wheelhouse / "onnxruntime-1.0.0-py3-none-any.whl").write_bytes(b"onnxruntime-wheel")

            result = build_ocr_wheelhouse_bundle(wheelhouse, out, version="0.12.0-m12")
            manifest = json.loads((out / "ocr_wheelhouse_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["schema_version"], "document_redaction_ocr_wheelhouse_manifest.v1")
            self.assertEqual(manifest["version"], "0.12.0-m12")
            self.assertTrue(manifest["bundled"])
            self.assertEqual(len(manifest["files"]), 2)
            self.assertTrue(result["wheelhouse_dir"].exists())

    def test_install_package_contains_m12_runtime_and_ocr_bundle_scripts(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.12.0-m12")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((package_dir / "app" / "stage_python_runtime.bat").exists())
            self.assertTrue((package_dir / "app" / "build_ocr_wheelhouse.bat").exists())
            self.assertIn("runtime_stage", manifest["commands"])
            self.assertIn("ocr_wheelhouse", manifest["commands"])


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.crypto import decrypt_mapping_file, encrypt_mapping_file
from redaction_assistant.install_package import build_install_package
from redaction_assistant.ocr_adapter import extract_text_with_ocr


class FakeRapidOcr:
    def __call__(self, path):
        return [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "项目名称：OCR真实路径项目", 0.93),
            ([[0, 12], [10, 12], [10, 20], [0, 20]], "合同金额：100万元", 0.87),
        ], None


class M10OcrRuntimeTests(unittest.TestCase):
    def test_mapping_encryption_roundtrip_emits_no_deprecation_warning(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "local_mapping.private.json"
            target = Path(td) / "local_mapping.private.enc"
            source.write_text(json.dumps({"A": "原始项目"}, ensure_ascii=False), encoding="utf-8")

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                encrypt_mapping_file(source, target, passphrase="local-secret")
                restored = decrypt_mapping_file(target, passphrase="local-secret")

        self.assertEqual(restored, {"A": "原始项目"})
        self.assertFalse(any(item.category is DeprecationWarning for item in caught))

    def test_rapidocr_adapter_uses_lazy_loader_when_configured(self):
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "scan.png"
            image.write_bytes(b"fake-image")
            with patch.dict("os.environ", {"DRA_OCR_ENGINE": "rapidocr"}):
                result = extract_text_with_ocr(image, engine_loader=lambda name: FakeRapidOcr())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["engine"], "rapidocr")
        self.assertIn("OCR真实路径项目", result["text"])
        self.assertGreater(result["confidence"], 0.8)

    def test_install_package_contains_m10_runtime_launcher_and_ocr_setup_docs(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.10.0-m10")
            package_dir = result["package_dir"]
            runtime_manifest = json.loads((package_dir / "app" / "runtime" / "runtime_manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((package_dir / "app" / "runtime" / "run_with_embedded_python.bat").exists())
            self.assertTrue((package_dir / "app" / "ocr_engines" / "OCR_SETUP.md").exists())
            self.assertIn("embedded_python_launcher", runtime_manifest)
            self.assertEqual(runtime_manifest["embedded_python_launcher"], "run_with_embedded_python.bat")


if __name__ == "__main__":
    unittest.main()

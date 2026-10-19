import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package


class M9OfflineRuntimeWithoutLicenseTests(unittest.TestCase):
    """0.27.0：安装包不再包含本地授权文件与授权校验；离线运行时/OCR/规则资产保留。"""

    def test_install_package_drops_license_assets_but_keeps_runtime_assets(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.27.0")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            runtime_manifest = json.loads((package_dir / "app" / "runtime" / "runtime_manifest.json").read_text(encoding="utf-8"))
            ocr_manifest = json.loads((package_dir / "app" / "ocr_engines" / "ocr_engine_manifest.json").read_text(encoding="utf-8"))
            rules_update = json.loads((package_dir / "app" / "rules" / "rules_update_manifest.json").read_text(encoding="utf-8"))

            self.assertFalse((package_dir / "app" / "license").exists())
            self.assertNotIn("local_license", manifest["capabilities"])
            self.assertNotIn("registration_trial_gate", manifest["capabilities"])
            self.assertNotIn("local_license", manifest["runtime_assets"])
            self.assertEqual(runtime_manifest["schema_version"], "document_redaction_runtime_bundle_manifest.v1")
            self.assertEqual(ocr_manifest["schema_version"], "document_redaction_ocr_engine_bundle_manifest.v1")
            self.assertEqual(rules_update["schema_version"], "document_redaction_rules_update_manifest.v1")
            self.assertFalse(runtime_manifest["bundled_python"])
            self.assertIn("rapidocr", ocr_manifest["supported_engines"])

    def test_legacy_bats_are_deprecation_notices_only(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.27.0")
            app = result["package_dir"] / "app"
            activate = (app / "activate_local_license.bat").read_text(encoding="utf-8")
            register = (app / "register_community.bat").read_text(encoding="utf-8")
            self.assertIn("0.27.0", activate)
            self.assertIn("不执行任何操作", activate)
            self.assertIn("0.27.0", register)
            self.assertIn("不执行任何操作", register)
            self.assertNotIn("validate-license", activate)
            self.assertNotIn("--edition", register)


if __name__ == "__main__":
    unittest.main()

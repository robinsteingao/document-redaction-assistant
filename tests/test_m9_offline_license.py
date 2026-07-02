import json
import base64
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package
from redaction_assistant.local_license import create_local_license, validate_local_license


class M9OfflineLicenseTests(unittest.TestCase):
    def test_local_license_validation_distinguishes_valid_and_expired(self):
        private_key = Ed25519PrivateKey.generate()
        private_key_b64 = base64.b64encode(private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode("ascii")
        public_key_b64 = base64.b64encode(private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode("ascii")
        valid = create_local_license("试点客户", expires_on="2099-12-31", issuer_private_key_b64=private_key_b64)
        expired = create_local_license("试点客户", expires_on="2000-01-01", issuer_private_key_b64=private_key_b64)

        valid_result = validate_local_license(valid, public_key_b64=public_key_b64)
        expired_result = validate_local_license(expired, public_key_b64=public_key_b64)

        self.assertEqual(valid["schema_version"], "document_redaction_local_license.v2")
        self.assertIn("signature", valid)
        self.assertEqual(valid_result["status"], "valid")
        self.assertIn("build_package", valid_result["features"])
        self.assertEqual(expired_result["status"], "expired")

    def test_install_package_contains_offline_runtime_license_and_update_assets(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.9.0-m9")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            license_data = json.loads((package_dir / "app" / "license" / "local_license.json").read_text(encoding="utf-8"))
            runtime_manifest = json.loads((package_dir / "app" / "runtime" / "runtime_manifest.json").read_text(encoding="utf-8"))
            ocr_manifest = json.loads((package_dir / "app" / "ocr_engines" / "ocr_engine_manifest.json").read_text(encoding="utf-8"))
            rules_update = json.loads((package_dir / "app" / "rules" / "rules_update_manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((package_dir / "app" / "activate_local_license.bat").exists())
            self.assertEqual(license_data["schema_version"], "document_redaction_local_license.v2")
            self.assertTrue(license_data["license_required"])
            self.assertNotIn("signature", license_data)
            self.assertEqual(runtime_manifest["schema_version"], "document_redaction_runtime_bundle_manifest.v1")
            self.assertEqual(ocr_manifest["schema_version"], "document_redaction_ocr_engine_bundle_manifest.v1")
            self.assertEqual(rules_update["schema_version"], "document_redaction_rules_update_manifest.v1")
            self.assertFalse(runtime_manifest["bundled_python"])
            self.assertIn("rapidocr", ocr_manifest["supported_engines"])
            self.assertIn("local_license", manifest["capabilities"])
            self.assertIn("rules_update_manifest", manifest["rules"])
            self.assertIn("runtime_manifest", manifest["runtime_assets"])


if __name__ == "__main__":
    unittest.main()

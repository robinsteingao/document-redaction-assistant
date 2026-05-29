import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package
from redaction_assistant.offline_runtime import build_ocr_wheelhouse_bundle, validate_ocr_wheelhouse_manifest
from redaction_assistant.pilot_feedback import build_pilot_issue_ledger
from redaction_assistant.production_sandbox import (
    build_production_sandbox_config,
    validate_production_sandbox_config,
)


class M15PilotOperationsTests(unittest.TestCase):
    def test_pilot_issue_ledger_has_actionable_schema_without_sensitive_payloads(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_pilot_issue_ledger(Path(td), version="0.15.0-m15")
            ledger = json.loads(result["ledger_json"].read_text(encoding="utf-8"))
            ledger_md = result["ledger_markdown"].read_text(encoding="utf-8")

            self.assertEqual(ledger["schema_version"], "document_redaction_pilot_issue_ledger.v1")
            self.assertEqual(ledger["version"], "0.15.0-m15")
            self.assertGreaterEqual(len(ledger["issues"]), 3)
            self.assertTrue(all("raw_file_path" not in issue for issue in ledger["issues"]))
            self.assertTrue(all(issue["status"] in {"open", "in_progress", "resolved", "deferred"} for issue in ledger["issues"]))
            self.assertIn("客户试点问题台账", ledger_md)
            self.assertIn("P1", ledger_md)

    def test_ocr_wheelhouse_manifest_validation_detects_hash_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            wheel = wheelhouse / "rapidocr_onnxruntime-1.0.0-py3-none-any.whl"
            wheel.write_bytes(b"local wheel bytes")

            result = build_ocr_wheelhouse_bundle(wheelhouse, root / "ocr_engines", version="0.15.0-m15")
            valid = validate_ocr_wheelhouse_manifest(result["ocr_wheelhouse_manifest"])
            self.assertEqual(valid["status"], "valid")
            self.assertEqual(valid["file_count"], 1)

            (root / "ocr_engines" / "wheelhouse" / wheel.name).write_bytes(b"changed")
            invalid = validate_ocr_wheelhouse_manifest(result["ocr_wheelhouse_manifest"])
            self.assertEqual(invalid["status"], "invalid")
            self.assertIn("sha256_mismatch", invalid["issues"][0]["reason"])

    def test_production_sandbox_config_validates_no_secret_and_no_original_upload(self):
        with tempfile.TemporaryDirectory() as td:
            config_path = build_production_sandbox_config(
                Path(td),
                endpoint="http://localhost:7272/api/redaction-sandbox/import",
                environment="pilot",
            )
            valid = validate_production_sandbox_config(config_path)
            config = json.loads(config_path.read_text(encoding="utf-8"))

            self.assertEqual(valid["status"], "valid")
            self.assertTrue(config["payload_policy"]["redacted_payload_only"])
            self.assertFalse(config["payload_policy"]["allow_original_files"])
            self.assertFalse(config["payload_policy"]["allow_local_mapping"])

            config["headers"]["Authorization"] = "Bearer real-token"
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            invalid = validate_production_sandbox_config(config_path)
            self.assertEqual(invalid["status"], "invalid")
            self.assertIn("secret_like_value", invalid["issues"][0]["reason"])

    def test_install_package_exposes_m15_pilot_operations_commands_and_assets(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.15.0-m15")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["commands"]["pilot_feedback_ledger"], "app\\record_pilot_feedback.bat")
            self.assertEqual(manifest["commands"]["ocr_package_validation"], "app\\validate_ocr_package.bat")
            self.assertEqual(manifest["commands"]["production_sandbox_config"], "app\\build_production_sandbox_config.bat")
            self.assertIn("pilot_operations", manifest["capabilities"])
            self.assertTrue((package_dir / "customer_acceptance" / "PILOT_ISSUE_LEDGER_TEMPLATE.md").exists())
            self.assertTrue((package_dir / "app" / "validate_ocr_package.bat").exists())
            self.assertTrue((package_dir / "app" / "record_pilot_feedback.bat").exists())
            self.assertTrue((package_dir / "app" / "build_production_sandbox_config.bat").exists())


if __name__ == "__main__":
    unittest.main()

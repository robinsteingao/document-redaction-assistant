import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package
from redaction_assistant.rules_package import build_rules_assets
from redaction_assistant.rules_update import apply_rules_update_package, validate_rules_update_package


class M11RulesRuntimeBundleTests(unittest.TestCase):
    def test_rules_update_applies_valid_package_and_rejects_blocked_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            active = root / "active_rules"
            update = root / "update"
            build_rules_assets(active, version="0.11.0-m11")
            updated_rules = {
                "schema_version": "document_redaction_rules_manifest.v1",
                "version": "0.11.1",
                "strategy": "assessment_preserving_redaction",
                "field_groups": [
                    {"name": "identity", "default_action": "pseudonym", "examples": ["项目名称"]},
                    {"name": "amount", "default_action": "range", "examples": ["合同金额"]},
                    {"name": "technical_metric", "default_action": "keep", "examples": ["10kV"]},
                ],
                "guardrails": ["本地映射表不得上传", "金额字段不默认清空", "技术指标和验证阶段默认保留"],
            }
            update.mkdir()
            (update / "rules_manifest.json").write_text(json.dumps(updated_rules, ensure_ascii=False), encoding="utf-8-sig")

            validation = validate_rules_update_package(update)
            result = apply_rules_update_package(update, active)

            self.assertEqual(validation["status"], "valid")
            self.assertEqual(result["status"], "applied")
            self.assertEqual(json.loads((active / "rules_manifest.json").read_text(encoding="utf-8"))["version"], "0.11.1")

            blocked = json.loads((update / "rules_manifest.json").read_text(encoding="utf-8-sig"))
            for group in blocked["field_groups"]:
                if group["name"] == "technical_metric":
                    group["default_action"] = "mask"
            (update / "rules_manifest.json").write_text(json.dumps(blocked, ensure_ascii=False), encoding="utf-8")

            blocked_validation = validate_rules_update_package(update)
            self.assertEqual(blocked_validation["status"], "blocked")

    def test_install_package_contains_runtime_and_ocr_dependency_bundle_assets(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.11.0-m11")
            package_dir = result["package_dir"]
            runtime_files = json.loads((package_dir / "app" / "runtime" / "runtime_files_manifest.json").read_text(encoding="utf-8"))
            ocr_files = json.loads((package_dir / "app" / "ocr_engines" / "ocr_files_manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((package_dir / "app" / "apply_rules_update.bat").exists())
            self.assertTrue((package_dir / "app" / "runtime" / "python" / "README_RUNTIME.txt").exists())
            self.assertTrue((package_dir / "app" / "ocr_engines" / "requirements-ocr.txt").exists())
            self.assertEqual(runtime_files["schema_version"], "document_redaction_runtime_files_manifest.v1")
            self.assertEqual(ocr_files["schema_version"], "document_redaction_ocr_files_manifest.v1")
            self.assertIn("requirements-ocr.txt", [item["path"] for item in ocr_files["files"]])


if __name__ == "__main__":
    unittest.main()

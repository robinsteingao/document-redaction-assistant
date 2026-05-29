import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package
from redaction_assistant.runtime_preflight import run_runtime_preflight


class M8InstallReadinessTests(unittest.TestCase):
    def test_runtime_preflight_reports_required_checks(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_runtime_preflight(Path(td))

        self.assertEqual(report["schema_version"], "document_redaction_runtime_preflight.v1")
        self.assertIn(report["overall_status"], {"ready", "warning", "failed"})
        check_names = {check["name"] for check in report["checks"]}
        self.assertIn("python_version", check_names)
        self.assertIn("source_package_import", check_names)
        self.assertIn("write_permission", check_names)
        self.assertIn("ocr_adapter", check_names)
        self.assertIn("rules_manifest", check_names)
        self.assertIn("ocr", report)

    def test_install_package_contains_runtime_readiness_and_rules_assets(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.8.0-m8")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            rules_manifest = json.loads((package_dir / "app" / "rules" / "rules_manifest.json").read_text(encoding="utf-8"))
            ocr_manifest = json.loads((package_dir / "app" / "rules" / "ocr_plugin_manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((package_dir / "app" / "check_runtime.bat").exists())
            self.assertTrue((package_dir / "app" / "install_local.bat").exists())
            self.assertTrue((package_dir / "app" / "rules" / "rules_manifest.json").exists())
            self.assertTrue((package_dir / "app" / "rules" / "ocr_plugin_manifest.json").exists())
            self.assertEqual(rules_manifest["schema_version"], "document_redaction_rules_manifest.v1")
            self.assertEqual(ocr_manifest["schema_version"], "document_redaction_ocr_plugin_manifest.v1")
            self.assertEqual(manifest["package_type"], "testable_install_readiness_package")
            self.assertIn("app\\check_runtime.bat", manifest["commands"]["runtime_preflight"])
            self.assertIn("rapidocr", ocr_manifest["supported_engines"])


if __name__ == "__main__":
    unittest.main()

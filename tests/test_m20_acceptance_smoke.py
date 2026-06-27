import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.acceptance import run_acceptance_smoke
from redaction_assistant.install_package import build_install_package


class M20AcceptanceSmokeTests(unittest.TestCase):
    def test_install_package_contains_repeatable_acceptance_smoke_script(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.20.0-m20")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["commands"]["acceptance_smoke"], "app\\run_acceptance_smoke.bat")
            self.assertIn("acceptance_smoke", manifest["capabilities"])
            self.assertTrue((package_dir / "app" / "run_acceptance_smoke.bat").exists())
            start_here = (package_dir / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("run_acceptance_smoke.bat", start_here)

    def test_acceptance_smoke_writes_report_for_sample_documents(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = build_install_package(root, version="0.20.0-m20")
            package_dir = result["package_dir"]
            app_dir = package_dir / "app"
            output_dir = package_dir / "generated" / "acceptance"

            report = run_acceptance_smoke(app_dir, output_dir=output_dir, project_alias_id="m20_acceptance")
            report_path = output_dir / "acceptance_report.json"

            self.assertEqual(report["status"], "passed")
            self.assertTrue(report_path.exists())
            self.assertTrue(report["checks"]["redaction_package"]["passed"])
            self.assertFalse(report["checks"]["redaction_package"]["original_files_uploaded"])
            self.assertFalse(report["checks"]["redaction_package"]["mapping_uploaded"])
            self.assertGreater(report["checks"]["redaction_package"]["block_count"], 0)
            self.assertTrue((output_dir / "redaction_upload_package.json").exists())
            self.assertTrue((output_dir / "local_mapping.private.enc").exists())
            self.assertFalse((output_dir / "local_mapping.private.json").exists())
            self.assertIn("encrypted_mapping", report["checks"]["redaction_package"])

    def test_acceptance_smoke_fails_invalid_commercial_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = build_install_package(root, version="0.20.0-m20")
            package_dir = result["package_dir"]
            app_dir = package_dir / "app"
            (package_dir / "commercial_release_manifest.json").write_text(
                json.dumps({"offline_status": "complete_offline"}, ensure_ascii=False),
                encoding="utf-8",
            )

            report = run_acceptance_smoke(app_dir, output_dir=package_dir / "generated" / "acceptance")

            self.assertEqual(report["status"], "failed")
            self.assertFalse(report["checks"]["commercial_package"]["passed"])

    def test_acceptance_smoke_resolves_relative_app_dir_from_app_working_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = build_install_package(root, version="0.20.0-m20")
            package_dir = result["package_dir"]
            app_dir = package_dir / "app"
            (package_dir / "commercial_release_manifest.json").write_text(
                json.dumps({"offline_status": "complete_offline"}, ensure_ascii=False),
                encoding="utf-8",
            )

            with patch("os.getcwd", return_value=str(app_dir)):
                report = run_acceptance_smoke(".", output_dir=package_dir / "generated" / "acceptance")

            self.assertFalse(report["checks"]["commercial_package"]["skipped"])


if __name__ == "__main__":
    unittest.main()

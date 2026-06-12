import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package


class M7InstallPackageTests(unittest.TestCase):
    def test_build_install_package_creates_testable_windows_package(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.7.0-m7")

            package_dir = result["package_dir"]
            archive = result["archive"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            archive_names = set(zipfile.ZipFile(archive).namelist())

            self.assertTrue(package_dir.exists())
            self.assertTrue(archive.exists())
            self.assertEqual(archive.name, "document_redaction_assistant_install_0.7.0-m7.zip")
            self.assertEqual(manifest["schema_version"], "document_redaction_install_manifest.v1")
            self.assertEqual(manifest["version"], "0.7.0-m7")
            self.assertEqual(manifest["entrypoint"], "START_HERE.md")
            self.assertIn("run_sample_self_test.bat", manifest["smoke_test"])
            self.assertTrue((package_dir / "START_HERE.md").exists())
            self.assertTrue((package_dir / "app" / "run_cli.bat").exists())
            self.assertTrue((package_dir / "app" / "register_community.bat").exists())
            self.assertTrue((package_dir / "app" / "start_local_service.bat").exists())
            self.assertTrue((package_dir / "app" / "run_sample_self_test.bat").exists())
            self.assertTrue((package_dir / "app" / "src" / "redaction_assistant" / "cli.py").exists())
            self.assertTrue((package_dir / "app" / "desktop_shell" / "index.html").exists())
            self.assertTrue((package_dir / "sample_data" / "project_alpha" / "input.txt").exists())
            self.assertFalse((package_dir / "app" / "local_mapping.private.json").exists())
            self.assertIn(f"{package_dir.name}/START_HERE.md", archive_names)
            self.assertIn(f"{package_dir.name}/app/run_cli.bat", archive_names)
            self.assertIn(f"{package_dir.name}/app/register_community.bat", archive_names)
            self.assertIn(f"{package_dir.name}/app/desktop_shell/index.html", archive_names)

            run_cli = (package_dir / "app" / "run_cli.bat").read_text(encoding="utf-8")
            register = (package_dir / "app" / "register_community.bat").read_text(encoding="utf-8")
            self_test = (package_dir / "app" / "run_sample_self_test.bat").read_text(encoding="utf-8")
            start_here = (package_dir / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("DRA_REGISTRATION_DIR", run_cli)
            self.assertIn("registration-request", register)
            self.assertIn("80元/年", register)
            self.assertIn("registration-request", self_test)
            self.assertIn("--registration-dir", self_test)
            self.assertIn("50 个文件", start_here)
            self.assertEqual(manifest["commands"]["registration"], "app\\register_community.bat")
            self.assertIn("registration_trial_gate", manifest["capabilities"])


if __name__ == "__main__":
    unittest.main()

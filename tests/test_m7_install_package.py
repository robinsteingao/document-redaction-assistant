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
            self.assertTrue((package_dir / "app" / "start_local_service.bat").exists())
            self.assertTrue((package_dir / "app" / "run_sample_self_test.bat").exists())
            self.assertTrue((package_dir / "app" / "src" / "redaction_assistant" / "cli.py").exists())
            self.assertTrue((package_dir / "app" / "desktop_shell" / "index.html").exists())
            self.assertTrue((package_dir / "sample_data" / "project_alpha" / "input.txt").exists())
            self.assertFalse((package_dir / "app" / "local_mapping.private.json").exists())
            self.assertIn(f"{package_dir.name}/START_HERE.md", archive_names)
            self.assertIn(f"{package_dir.name}/app/run_cli.bat", archive_names)
            self.assertIn(f"{package_dir.name}/app/desktop_shell/index.html", archive_names)


if __name__ == "__main__":
    unittest.main()

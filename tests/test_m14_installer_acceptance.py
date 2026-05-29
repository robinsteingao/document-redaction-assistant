import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package


class M14InstallerAcceptanceTests(unittest.TestCase):
    def test_install_package_contains_installer_shell_and_acceptance_assets(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.14.0-m14")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            wizard = (package_dir / "installer_wizard" / "index.html").read_text(encoding="utf-8")
            checklist = (package_dir / "customer_acceptance" / "ACCEPTANCE_CHECKLIST.md").read_text(encoding="utf-8")
            record = (package_dir / "install_records" / "INSTALL_RECORD_TEMPLATE.md").read_text(encoding="utf-8")

            self.assertTrue((package_dir / "setup.bat").exists())
            self.assertTrue((package_dir / "uninstall.bat").exists())
            self.assertTrue((package_dir / "installer_wizard" / "index.html").exists())
            self.assertTrue((package_dir / "customer_acceptance" / "PILOT_SIGNOFF.md").exists())
            self.assertTrue((package_dir / "install_records" / "INSTALL_RECORD_TEMPLATE.md").exists())
            self.assertIn("installer_shell", manifest["capabilities"])
            self.assertEqual(manifest["commands"]["setup"], "setup.bat")
            self.assertIn("安装预检", wizard)
            self.assertIn("报告交付演示", checklist)
            self.assertIn("试装结论", record)


if __name__ == "__main__":
    unittest.main()

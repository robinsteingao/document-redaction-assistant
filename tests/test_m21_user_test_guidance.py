import sys
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.install_package import build_install_package


class M21UserTestGuidanceTests(unittest.TestCase):
    def test_desktop_shell_explains_failed_fetch_as_local_service_not_started(self):
        with tempfile.TemporaryDirectory() as td:
            shell = build_desktop_shell(Path(td), version="0.21.0-m21", service_url="http://127.0.0.1:8765")
            index = (shell / "index.html").read_text(encoding="utf-8")

        self.assertIn("本地服务未连接", index)
        self.assertIn("start_offline_app.bat", index)
        self.assertIn("start_local_service.bat", index)
        self.assertIn("Failed to fetch", index)

    def test_desktop_shell_contains_minimum_interactive_redaction_form(self):
        with tempfile.TemporaryDirectory() as td:
            shell = build_desktop_shell(Path(td), version="0.21.0-m21", service_url="http://127.0.0.1:8765")
            index = (shell / "index.html").read_text(encoding="utf-8")

        self.assertIn("projectAlias", index)
        self.assertIn("inputPaths", index)
        self.assertIn("outputDir", index)
        self.assertIn("生成脱敏结果包", index)
        self.assertIn("runBuildPackage", index)
        self.assertIn("buildResult", index)
        self.assertIn("/plan-inputs", index)
        self.assertIn("/start-build", index)
        self.assertIn("/job-status", index)

    def test_install_package_contains_desktop_app_launcher_that_starts_service_first(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.21.0-m21")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            launcher = (package_dir / "app" / "start_desktop_app.bat").read_text(encoding="utf-8")
            start_here = (package_dir / "START_HERE.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["commands"]["desktop_app"], "app\\start_desktop_app.bat")
        self.assertIn("desktop_app_launcher", manifest["capabilities"])
        self.assertIn("start_desktop_app.bat", start_here)
        self.assertIn("launch-desktop-app", launcher)
        self.assertIn("desktop_shell\\index.html", launcher)
        self.assertNotIn("cmd /k", launcher.lower())
        self.assertNotIn("检查端口", start_here)

    def test_cli_exposes_one_click_desktop_launcher_command(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.21.0-m21")
            cli = (result["package_dir"] / "app" / "src" / "redaction_assistant" / "cli.py").read_text(encoding="utf-8")

        self.assertIn("launch-desktop-app", cli)
        self.assertIn("launch_desktop_app", cli)


if __name__ == "__main__":
    unittest.main()

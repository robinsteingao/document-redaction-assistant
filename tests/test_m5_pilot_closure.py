import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(WORKSPACE / "prototype" / "src" / "backend"))

from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.ocr_adapter import get_ocr_status
from redaction_assistant.sandbox import build_sandbox_import_package
from redaction_assistant.workflow import build_redaction_package
from routers.redaction_sandbox import import_redaction_sandbox_package


class FakeDataManager:
    def __init__(self):
        self.projects = {}
        self.files = {}

    def upsert_project(self, project):
        project_id = project["id"]
        self.projects[project_id] = dict(project)
        return project_id

    def replace_project_files(self, project_id, files):
        self.files[project_id] = list(files)

    def add_log(self, project_id, actor, action):
        return None


class M5PilotClosureTests(unittest.TestCase):
    def test_sandbox_import_package_persists_project_and_redacted_files(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "input.txt"
            source.write_text(
                "项目名称：配网智能监测项目。\n合同金额：350万元。\n技术指标：10kV试运行30天。\n",
                encoding="utf-8",
            )
            package, _mapping = build_redaction_package([source], project_alias_id="project_m5")
            sandbox = build_sandbox_import_package(package)
            dm = FakeDataManager()

            result = import_redaction_sandbox_package(sandbox, dm)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["project_id"], "redacted_project_m5")
        self.assertIn("redacted_project_m5", dm.projects)
        self.assertEqual(dm.projects["redacted_project_m5"]["name"], "project_m5")
        files = dm.files["redacted_project_m5"]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["category"], "redacted_sandbox")
        self.assertIn("项目A", files[0]["desc"])
        self.assertNotIn("配网智能监测项目", json.dumps(files, ensure_ascii=False))
        self.assertIn("10kV", files[0]["desc"])

    def test_desktop_shell_and_ocr_status_are_available_for_pilot(self):
        with tempfile.TemporaryDirectory() as td:
            shell_dir = build_desktop_shell(Path(td), version="0.5.0-m5")
            index = shell_dir / "index.html"
            config = shell_dir / "app_config.json"

            html = index.read_text(encoding="utf-8")
            cfg = json.loads(config.read_text(encoding="utf-8"))
            status = get_ocr_status()

        self.assertIn("文档安全脱敏助手", html)
        self.assertIn("导入文件", html)
        self.assertIn("字段复核", html)
        self.assertIn("生成结果包", html)
        self.assertEqual(cfg["version"], "0.5.0-m5")
        self.assertIn(status["status"], {"not_configured", "available"})
        self.assertFalse(status["required_for_text_pdf"])


if __name__ == "__main__":
    unittest.main()

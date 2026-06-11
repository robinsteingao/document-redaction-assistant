from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.install_package import build_install_package
from redaction_assistant.review import export_review_workspace
from redaction_assistant.workflow import build_redaction_package


class M24UserExperienceFeedbackTest(unittest.TestCase):
    def test_install_package_contains_must_read_txt_and_doc(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.24.1-m24-ux")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            must_read = (package_dir / "使用必读.txt").read_text(encoding="utf-8")
            start_here = (package_dir / "START_HERE.md").read_text(encoding="utf-8")
            has_doc = (package_dir / "使用必读.doc").exists()

        self.assertTrue(has_doc)
        self.assertEqual(manifest["commands"]["must_read_txt"], "使用必读.txt")
        self.assertEqual(manifest["commands"]["must_read_doc"], "使用必读.doc")
        self.assertIn("未配置 OCR 引擎", must_read)
        self.assertIn("the application cant be start,user installation couldn't be completed", must_read)
        self.assertIn("review_decisions.json", must_read)
        self.assertIn("批量脱敏", must_read)
        self.assertIn("使用必读.txt", start_here)

    def test_desktop_shell_uses_customer_friendly_terms_and_summaries(self):
        with tempfile.TemporaryDirectory() as td:
            shell = build_desktop_shell(Path(td), version="0.24.1-m24-ux", service_url="http://127.0.0.1:8765")
            index = (shell / "index.html").read_text(encoding="utf-8")

        self.assertIn("生成脱敏结果包", index)
        self.assertIn("评价影响提醒（生成前必看）", index)
        self.assertIn("自定义字段处理方式（可选）", index)
        self.assertIn("formatPlanResult", index)
        self.assertIn("formatJobStatus", index)
        self.assertIn("原始详情（供技术支持复制", index)
        self.assertNotIn("上传前评价影响门禁", index)
        self.assertNotIn("客户自定义脱敏决策 JSON", index)

    def test_review_workspace_uses_readable_column_and_strategy_labels(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "input.txt"
            source.write_text("项目名称：配网智能监测项目\n合同金额：100万元\n试运行30天", encoding="utf-8")
            package, mapping = build_redaction_package([source], project_alias_id="M24-UX")
            outputs = export_review_workspace(Path(td) / "out", package, mapping)
            html = outputs["review_html"].read_text(encoding="utf-8")

        self.assertIn("字段类别", html)
        self.assertIn("脱敏显示名", html)
        self.assertIn("处理方式", html)
        self.assertIn("保留的评价信息", html)
        self.assertIn("映射表是否上传", html)
        self.assertIn("技术评价信息是否保留", html)
        self.assertIn("效益评价信息是否保留", html)
        self.assertNotIn(">True<", html)
        self.assertNotIn(">False<", html)
        self.assertIn("金额信息", html)
        self.assertIn("保留区间", html)
        self.assertIn("验证/试验信息", html)
        self.assertIn("保留原样", html)
        self.assertNotIn("<th>类型</th>", html)
        self.assertNotIn("<th>占位符</th>", html)
        self.assertNotIn("<th>策略</th>", html)


if __name__ == "__main__":
    unittest.main()

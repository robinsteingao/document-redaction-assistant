import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.review import (
    build_review_workspace,
    export_review_workspace,
    review_decisions_from_mapping,
)
from redaction_assistant.workflow import build_redaction_package, build_restore_preview


class M2ReviewWorkspaceTests(unittest.TestCase):
    def test_customer_dictionary_and_decisions_control_redaction_strategy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "input.txt"
            source.write_text(
                "项目名称：配网智能监测项目。\n"
                "承担单位：蜀能创新中心。\n"
                "合同编号：HT-2026-001。\n"
                "合同金额：350万元。\n"
                "技术指标：10kV线路故障定位误差≤1%，现场试运行30天。\n",
                encoding="utf-8",
            )
            dictionary = root / "customer_dictionary.json"
            dictionary.write_text(
                json.dumps({"organization": ["蜀能创新中心"]}, ensure_ascii=False),
                encoding="utf-8",
            )

            workspace = build_review_workspace(
                [source],
                project_alias_id="2026-STPE-M2",
                customer_dictionary=dictionary,
            )
            candidates = workspace["review_candidates"]
            org = next(item for item in candidates if item["original"] == "蜀能创新中心")
            amount = next(item for item in candidates if item["kind"] == "amount")
            contract = next(item for item in candidates if item["kind"] == "contract_id")
            decisions = review_decisions_from_mapping({
                org["candidate_id"]: {"action": "redact", "strategy": "pseudonym"},
                amount["candidate_id"]: {"action": "redact", "strategy": "mask"},
                contract["candidate_id"]: {"action": "keep"},
            })

            package, mapping = build_redaction_package(
                [source],
                project_alias_id="2026-STPE-M2",
                customer_dictionary=dictionary,
                review_decisions=decisions,
            )

        serialized_package = json.dumps(package, ensure_ascii=False)
        self.assertIn("单位A", serialized_package)
        self.assertIn("HT-2026-001", serialized_package)
        self.assertNotIn("蜀能创新中心", serialized_package)
        self.assertNotIn("350万元", serialized_package)
        self.assertNotIn("100万至500万", serialized_package)
        self.assertIn("经济效益分析可能降级", "\n".join(package["review_warnings"]))
        self.assertTrue(any(item["original"] == "蜀能创新中心" for item in mapping["items"]))

    def test_export_review_workspace_writes_html_and_restore_preview(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "input.txt"
            source.write_text(
                "项目名称：配网智能监测项目。\n"
                "承担单位：国网四川省电力公司。\n"
                "合同金额：350万元。\n"
                "技术指标：10kV线路故障定位误差≤1%，现场试运行30天。\n",
                encoding="utf-8",
            )
            package, mapping = build_redaction_package([source], project_alias_id="2026-STPE-M2")
            preview = build_restore_preview(package, mapping)
            outputs = export_review_workspace(root / "workspace", package, mapping)

            html = outputs["review_html"].read_text(encoding="utf-8")
            self.assertIn("字段复核", html)
            self.assertIn("项目A", html)
            self.assertIn("评估影响", html)
            self.assertIn("本地还原预演", html)
            self.assertIn("配网智能监测项目", preview["restored_preview"])
            self.assertIn("项目A", preview["redacted_preview"])
            self.assertIn("350万元", preview["restored_preview"])
            self.assertNotIn("350万元（100万至500万）", preview["restored_preview"])
            self.assertTrue(outputs["review_candidates"].exists())
            self.assertTrue(outputs["restore_preview"].exists())


if __name__ == "__main__":
    unittest.main()

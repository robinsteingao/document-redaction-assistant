from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.local_service import handle_request
from redaction_assistant.redactor import candidate_id_for
from redaction_assistant.rules import Entity, amount_range, detect_entities
from redaction_assistant.workflow import build_redaction_package, write_package
from redaction_assistant.review import export_review_workspace


class M24CustomRedactionGateTest(unittest.TestCase):
    def test_rules_cover_person_cn_patent_and_english_amount(self):
        text = "联系人：张三\nPatent: CN202410123456.7\nAmount: 320.50\n试运行30天，效率96.5%。"
        entities = detect_entities([text])
        by_kind = {entity.kind: entity.original for entity in entities}

        self.assertEqual(by_kind["person"], "张三")
        self.assertEqual(by_kind["patent_id"], "CN202410123456.7")
        self.assertIn("320.50", by_kind["amount"])
        self.assertIn("technical_metric", {entity.kind for entity in entities})

    def test_default_keeps_assessment_metrics_and_redacts_privacy(self):
        text = "联系人：张三\n专利 CN202410123456.7\n合同金额：320.50万元\n试运行30天，效率96.5%。"
        package, mapping = build_redaction_package([_write_text(text)], project_alias_id="M24-GATE")
        redacted = "\n".join(block["text"] for block in package["redacted_text_blocks"])

        self.assertNotIn("张三", redacted)
        self.assertNotIn("CN202410123456.7", redacted)
        self.assertIn("试运行30天", redacted)
        self.assertIn("96.5%", redacted)
        self.assertIn("redaction_impact_summary", package)
        self.assertEqual(package["redaction_impact_summary"]["trl_impact"], "none")
        self.assertEqual(package["redaction_impact_summary"]["benefit_impact"], "low")
        self.assertEqual(package["redaction_impact_summary"]["overall_level"], "pass")
        self.assertIn("technical_metric", package["redaction_impact_summary"]["preserved_assessment_factors"])
        self.assertGreaterEqual(mapping["mapping_hash"].__len__(), 16)

    def test_default_amount_range_is_not_blocking_gate(self):
        package, _mapping = build_redaction_package([_write_text("合同金额：320.50万元")], project_alias_id="M24-AMOUNT")
        impact = package["redaction_impact_summary"]

        self.assertNotEqual(impact["overall_level"], "blocked_requires_confirmation")
        self.assertEqual(impact["benefit_impact"], "low")

    def test_label_patterns_stop_at_chinese_comma_to_avoid_swallowing_fields(self):
        text = "承担单位：甲公司，合同金额：320万元，联系人：张三"
        entities = detect_entities([text])
        organizations = [entity.original for entity in entities if entity.kind == "organization"]
        amounts = [entity.original for entity in entities if entity.kind == "amount"]
        persons = [entity.original for entity in entities if entity.kind == "person"]

        self.assertEqual(organizations, ["甲公司"])
        self.assertIn("320万元", amounts)
        self.assertEqual(persons, ["张三"])

        package, _mapping = build_redaction_package([_write_text(text)], project_alias_id="M24-COMMA")
        redacted = "\n".join(block["text"] for block in package["redacted_text_blocks"])
        self.assertIn("合同金额：金额区间", redacted)
        self.assertIn("联系人：人员", redacted)

    def test_organization_label_keeps_enumeration_comma_inside_name(self):
        text = "承担单位：甲、乙联合体，合同金额：320万元"
        entities = detect_entities([text])
        organizations = [entity.original for entity in entities if entity.kind == "organization"]
        amounts = [entity.original for entity in entities if entity.kind == "amount"]

        self.assertEqual(organizations, ["甲、乙联合体"])
        self.assertIn("320万元", amounts)

    def test_unmatched_review_decisions_are_reported_in_impact_summary(self):
        package, _mapping = build_redaction_package(
            [_write_text("联系人：张三")],
            project_alias_id="M24-UNMATCHED",
            review_decisions={"bad-candidate-id": {"action": "keep"}},
        )

        impact = package["redaction_impact_summary"]
        redacted = "\n".join(block["text"] for block in package["redacted_text_blocks"])
        self.assertIn("bad-candidate-id", impact["unmatched_decisions"])
        self.assertTrue(impact["customer_decisions_present"])
        self.assertFalse(impact["customer_confirmed"])
        self.assertNotIn("张三", redacted)

    def test_customer_can_force_redact_metric_and_gate_records_degradation(self):
        metric = Entity("technical_metric", "96.5%", "技术指标", "keep")
        decisions = {candidate_id_for(metric): {"action": "redact", "strategy": "mask"}}
        text = "效率96.5%，试运行30天。"

        package, _mapping = build_redaction_package([_write_text(text)], project_alias_id="M24-FORCE", review_decisions=decisions)
        redacted = "\n".join(block["text"] for block in package["redacted_text_blocks"])
        impact = package["redaction_impact_summary"]

        self.assertNotIn("96.5%", redacted)
        self.assertEqual(impact["overall_level"], "blocked_requires_confirmation")
        self.assertEqual(impact["trl_impact"], "high")
        self.assertTrue(impact["customer_decisions_present"])
        self.assertFalse(impact["customer_confirmed"])
        self.assertIsNone(impact["customer_confirmation_source"])
        self.assertIsNone(impact["customer_confirmation_recorded_at"])
        self.assertIn("technical_metric", impact["redacted_assessment_fields"])

    def test_customer_confirmation_requires_explicit_degradation_risk_signal(self):
        metric = Entity("technical_metric", "96.5%", "技术指标", "keep")
        decisions = {candidate_id_for(metric): {"action": "redact", "strategy": "mask"}}

        package, _mapping = build_redaction_package(
            [_write_text("效率96.5%，试运行30天。")],
            project_alias_id="M24-FORCE-CONFIRMED",
            review_decisions=decisions,
            customer_confirmed_degradation_risk=True,
        )
        impact = package["redaction_impact_summary"]

        self.assertEqual(impact["overall_level"], "blocked_requires_confirmation")
        self.assertTrue(impact["customer_decisions_present"])
        self.assertTrue(impact["customer_confirmed"])
        self.assertEqual(impact["customer_confirmation_source"], "explicit_customer_confirmed_degradation_risk")
        self.assertTrue(impact["customer_confirmation_recorded_at"])

    def test_keep_only_decisions_do_not_confirm_degradation_risk(self):
        metric = Entity("technical_metric", "96.5%", "技术指标", "keep")
        decisions = {candidate_id_for(metric): {"action": "keep", "strategy": "keep"}}

        package, _mapping = build_redaction_package(
            [_write_text("效率96.5%，试运行30天。")],
            project_alias_id="M24-KEEP-ONLY",
            review_decisions=decisions,
        )
        impact = package["redaction_impact_summary"]

        self.assertTrue(impact["customer_decisions_present"])
        self.assertFalse(impact["customer_confirmed"])

    def test_force_redact_default_keep_field_without_strategy_uses_mapping_strategy(self):
        metric = Entity("technical_metric", "96.5%", "技术指标", "keep")
        package, mapping = build_redaction_package(
            [_write_text("效率96.5%，试运行30天。")],
            project_alias_id="M24-FORCE-NO-STRATEGY",
            review_decisions={candidate_id_for(metric): {"action": "redact"}},
        )
        impact = package["redaction_impact_summary"]
        mapped_item = next(item for item in mapping["items"] if item["kind"] == "technical_metric")
        impact_item = next(item for item in impact["items"] if item["kind"] == "technical_metric")

        self.assertEqual(mapped_item["strategy"], "mask")
        self.assertEqual(impact_item["strategy"], "mask")
        self.assertIn("technical_metric", impact["strongly_redacted_fields"])

    def test_review_workspace_exports_kept_assessment_candidates_for_customer_choice(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "project.txt"
            source.write_text("联系人：张三\n试运行30天，效率96.5%。", encoding="utf-8")
            package, mapping = build_redaction_package([source], project_alias_id="M24-REVIEW")
            write_package(td, package, mapping)
            outputs = export_review_workspace(td, package, mapping)
            candidates = json.loads(outputs["review_candidates"].read_text(encoding="utf-8"))
            html = outputs["review_html"].read_text(encoding="utf-8")

        kinds = {item["kind"] for item in candidates["items"]}
        self.assertIn("person", kinds)
        self.assertIn("technical_metric", kinds)
        self.assertIn("评价影响提示", html)
        self.assertIn("action", html)

    def test_local_service_accepts_customer_review_decisions(self):
        metric = Entity("technical_metric", "96.5%", "技术指标", "keep")
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "project.txt"
            source.write_text("效率96.5%，试运行30天。", encoding="utf-8")
            response = handle_request({
                "action": "build_package",
                "files": [str(source)],
                "project_alias_id": "M24-SERVICE",
                "out": str(Path(td) / "out"),
                "review_decisions": {candidate_id_for(metric): {"action": "redact", "strategy": "mask"}},
            })

            self.assertTrue(response["success"], response)
            package = json.loads(Path(response["result"]["package"]).read_text(encoding="utf-8"))

        self.assertEqual(package["redaction_impact_summary"]["trl_impact"], "high")
        self.assertFalse(package["redaction_impact_summary"]["customer_confirmed"])

    def test_local_service_requires_explicit_degradation_risk_confirmation(self):
        metric = Entity("technical_metric", "96.5%", "技术指标", "keep")
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "project.txt"
            source.write_text("效率96.5%，试运行30天。", encoding="utf-8")
            response = handle_request({
                "action": "build_package",
                "files": [str(source)],
                "project_alias_id": "M24-SERVICE-CONFIRMED",
                "out": str(Path(td) / "out"),
                "review_decisions": {candidate_id_for(metric): {"action": "redact", "strategy": "mask"}},
                "customer_confirmed_degradation_risk": True,
            })

            self.assertTrue(response["success"], response)
            package = json.loads(Path(response["result"]["package"]).read_text(encoding="utf-8"))

        self.assertTrue(package["redaction_impact_summary"]["customer_confirmed"])

    def test_local_service_string_false_does_not_confirm_degradation_risk(self):
        metric = Entity("technical_metric", "96.5%", "技术指标", "keep")
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "project.txt"
            source.write_text("效率96.5%，试运行30天。", encoding="utf-8")
            response = handle_request({
                "action": "build_package",
                "files": [str(source)],
                "project_alias_id": "M24-SERVICE-STRING-FALSE",
                "out": str(Path(td) / "out"),
                "review_decisions": {candidate_id_for(metric): {"action": "redact", "strategy": "mask"}},
                "customer_confirmed_degradation_risk": "false",
            })

            self.assertTrue(response["success"], response)
            package = json.loads(Path(response["result"]["package"]).read_text(encoding="utf-8"))

        self.assertFalse(package["redaction_impact_summary"]["customer_confirmed"])

    def test_desktop_shell_exposes_customer_optional_redaction_gate(self):
        with tempfile.TemporaryDirectory() as td:
            shell = build_desktop_shell(Path(td), version="0.24.0-m24", service_url="http://127.0.0.1:8765")
            index = (shell / "index.html").read_text(encoding="utf-8")

        self.assertIn("reviewDecisions", index)
        self.assertIn("confirmDegradationRisk", index)
        self.assertIn("评价影响提醒（生成前必看）", index)
        self.assertIn("自定义字段处理方式", index)
        self.assertIn("review_workspace.html", index)

    def test_amount_range_foreign_currency_conversion(self):
        self.assertEqual(amount_range("$1234"), "低于10万")
        self.assertEqual(amount_range("$50000"), "10万至50万")
        self.assertEqual(amount_range("$100"), "低于10万")
        self.assertEqual(amount_range("USD 1234"), "低于10万")
        self.assertEqual(amount_range("50000 dollars"), "10万至50万")


def _write_text(text: str) -> Path:
    td = tempfile.TemporaryDirectory()
    path = Path(td.name) / "input.txt"
    path.write_text(text, encoding="utf-8")
    _TEMP_DIRS.append(td)
    return path


_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []


if __name__ == "__main__":
    unittest.main()

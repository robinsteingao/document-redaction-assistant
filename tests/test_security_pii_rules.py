from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.rules import detect_entities
from redaction_assistant.workflow import build_redaction_package


def test_detects_high_sensitivity_pii_rules():
    text = (
        "身份证号：11010119900307421X；银行卡号：6222021234567890123；"
        "地址：北京市海淀区中关村大街27号；护照号：E12345678；"
        "统一社会信用代码：91330100MA27X12345。"
    )

    entities = detect_entities([text])
    by_kind = {entity.kind: entity.original for entity in entities}

    assert by_kind["id_card"] == "11010119900307421X"
    assert by_kind["bank_card"] == "6222021234567890123"
    assert "北京市海淀区中关村大街27号" in by_kind["address"]
    assert by_kind["passport"] == "E12345678"
    assert by_kind["unified_social_credit_code"] == "91330100MA27X12345"


def test_high_sensitivity_pii_is_redacted_from_package(tmp_path: Path):
    source = tmp_path / "pii.txt"
    source.write_text("姓名：张三，身份证号：11010119900307421X，银行卡号：6222021234567890123，地址：北京市海淀区中关村大街27号。", encoding="utf-8")

    package, mapping = build_redaction_package([source], project_alias_id="PII")
    redacted = "\n".join(block["text"] for block in package["redacted_text_blocks"])
    kinds = {item["kind"] for item in mapping["items"]}

    assert "11010119900307421X" not in redacted
    assert "6222021234567890123" not in redacted
    assert "北京市海淀区中关村大街27号" not in redacted
    assert {"id_card", "bank_card", "address"}.issubset(kinds)

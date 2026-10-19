"""P2-1: Tests for span-based redact_text/restore_text.

Verifies that sub-string collisions, cascading replacements and overlap
edge-cases are handled correctly by the span-based approach.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.redactor import redact_text, restore_text, _collect_spans, _apply_spans


def test_basic_single_replacement():
    mapping = {"items": [{"original": "张三", "replacement": "人员A", "placeholder": "人员A"}]}
    assert redact_text("联系人：张三，电话12345678901", mapping) == "联系人：人员A，电话12345678901"


def test_multiple_distinct_replacements():
    mapping = {"items": [
        {"original": "张三", "replacement": "人员A", "placeholder": "人员A"},
        {"original": "13800138000", "replacement": "电话A", "placeholder": "电话A"},
    ]}
    redacted = redact_text("联系人张三，电话13800138000", mapping)
    assert "张三" not in redacted
    assert "13800138000" not in redacted
    assert "人员A" in redacted
    assert "电话A" in redacted


def test_substring_collision_longer_wins():
    """If '张三' and '张三丰' are both in mapping, '张三丰' in text should be
    replaced as a whole, not partially as '人员A丰'."""
    mapping = {"items": [
        {"original": "张三", "replacement": "人员A", "placeholder": "人员A"},
        {"original": "张三丰", "replacement": "人员B", "placeholder": "人员B"},
    ]}
    redacted = redact_text("张三丰是武林高手，张三是普通人", mapping)
    assert "张三丰" not in redacted
    assert "人员B" in redacted
    assert "人员A" in redacted
    # "张三丰" should not become "人员A丰"
    assert "人员A丰" not in redacted


def test_multiple_occurrences_of_same_original():
    mapping = {"items": [{"original": "项目A", "replacement": "代号X", "placeholder": "代号X"}]}
    redacted = redact_text("项目A启动，项目A验收，项目A结题", mapping)
    assert redacted == "代号X启动，代号X验收，代号X结题"


def test_cascading_replacement_avoided():
    """Ensure replacement text is not re-matched by a later item."""
    mapping = {"items": [
        {"original": "ABC", "replacement": "人员A", "placeholder": "人员A"},
        {"original": "人员A", "replacement": "人员B", "placeholder": "人员B"},
    ]}
    redacted = redact_text("ABC和DEF", mapping)
    # "ABC" should become "人员A", NOT "人员B" (no cascading)
    assert redacted == "人员A和DEF"


def test_restore_roundtrip():
    mapping = {"items": [
        {"original": "张三", "replacement": "人员A", "placeholder": "人员A"},
        {"original": "13800138000", "replacement": "电话A", "placeholder": "电话A"},
    ]}
    original_text = "联系人张三，电话13800138000"
    redacted = redact_text(original_text, mapping)
    restored = restore_text(redacted, mapping)
    assert restored == original_text


def test_restore_with_range_replacement():
    """Range strategy produces replacement like '金额A（10万至50万）'."""
    mapping = {"items": [
        {"original": "100万元", "replacement": "金额A（10万至50万）", "placeholder": "金额A"},
        {"original": "张三", "replacement": "人员A", "placeholder": "人员A"},
    ]}
    original_text = "金额100万元，经手人张三"
    redacted = redact_text(original_text, mapping)
    assert "100万元" not in redacted
    assert "张三" not in redacted
    restored = restore_text(redacted, mapping)
    assert restored == original_text


def test_empty_mapping():
    assert redact_text("hello world", {"items": []}) == "hello world"
    assert restore_text("hello world", {"items": []}) == "hello world"


def test_original_not_in_text():
    mapping = {"items": [{"original": "不存在", "replacement": "X", "placeholder": "X"}]}
    assert redact_text("这里没有目标", mapping) == "这里没有目标"


def test_collect_spans_non_overlapping():
    text = "AAAABBBB"
    pairs = [("AAAA", "X"), ("AA", "Y")]
    spans = _collect_spans(text, pairs)
    # "AAAA" at 0-4 should win, "AA" within it should be skipped
    assert (0, 4, "X") in spans
    assert not any(s[2] == "Y" and s[0] < 4 for s in spans)


def test_apply_spans_back_to_front():
    text = "ABCDEFGH"
    spans = [(0, 1, "X"), (4, 5, "Y")]
    result = _apply_spans(text, spans)
    # Back-to-front: (4,5,"Y") replaces E→Y, then (0,1,"X") replaces A→X
    assert result == "XBCDYFGH"

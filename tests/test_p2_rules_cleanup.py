"""P2-5: Tests for amount_range dead code cleanup."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.rules import amount_range


def test_amount_range_yuan():
    assert amount_range("5万元") == "低于10万"


def test_amount_range_billion():
    assert amount_range("2亿元") == "高于5000万"


def test_amount_range_small():
    assert amount_range("5万元") == "低于10万"


def test_amount_range_large():
    assert amount_range("6000万元") == "高于5000万"


def test_amount_range_unknown():
    assert amount_range("无数字") == "金额区间未知"


def test_amount_range_usd():
    result = amount_range("$10000")
    assert isinstance(result, str)
    assert "万" in result

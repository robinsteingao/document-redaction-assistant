from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.review import export_review_workspace
from redaction_assistant.workflow import build_redaction_package


def test_review_workspace_has_clickable_decision_controls(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("联系人：张三\n合同金额：300万元\n试运行30天，电压10kV。", encoding="utf-8")
    package, mapping = build_redaction_package([source], project_alias_id="M242-REVIEW")
    outputs = export_review_workspace(tmp_path / "out", package, mapping)
    html = outputs["review_html"].read_text(encoding="utf-8")

    assert "data-candidate-id" in html
    assert "保留原样" in html
    assert "遮盖隐藏" in html
    assert "替换为假名" in html
    assert "保留区间" in html
    assert "refreshDecisions" in html
    assert "导出复核选择文件" in html
    assert "高影响字段" in html


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.desktop_shell import build_desktop_shell


def test_desktop_shell_exposes_m242_customer_controls(tmp_path: Path):
    shell = build_desktop_shell(tmp_path, version="0.24.2-mvp", service_url="http://127.0.0.1:8765")
    html = (shell / "index.html").read_text(encoding="utf-8")

    assert "技术支持包" in html
    assert "supportBundleResult" in html
    assert "buildSupportBundle" in html
    assert "/support-bundle" in html
    assert "可直接处理" in html
    assert "需先转换" in html
    assert "路径不存在" in html
    assert "输出目录" in html


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

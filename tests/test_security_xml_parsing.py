from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.parsers import parse_file


def test_docx_with_doctype_is_rejected_without_entity_expansion(tmp_path: Path):
    docx = tmp_path / "evil.docx"
    xml = b'''<?xml version="1.0"?>
<!DOCTYPE w:document [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body>
</w:document>'''
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("word/document.xml", xml)

    blocks, manifest = parse_file(docx)

    assert blocks == []
    assert manifest["parser_status"] == "failed"
    assert any("parse_failed" in warning for warning in manifest["warnings"])


def test_dependencies_include_defusedxml():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "defusedxml" in requirements
    assert "defusedxml" in pyproject

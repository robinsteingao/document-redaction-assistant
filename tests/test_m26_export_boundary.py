from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.external_release import write_external_release
from redaction_assistant.hidden_channels import inspect_hidden_channels
from redaction_assistant.residual_scan import scan_residuals
from redaction_assistant.support_bundle import build_support_bundle
from redaction_assistant.workflow import build_redaction_package, write_package


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
X_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def test_readme_does_not_overclaim_identifiers_or_safety():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "不是已销毁原文" in readme
    assert "身份证号、银行卡号、护照号、统一社会信用代码和地址" in readme
    assert "候选识别" in readme
    assert "漏报或误报" in readme
    assert "不要把任何字段写成已验收能力" in readme
    assert "不承诺材料已经安全" in readme


def test_header_only_sensitive_text_is_not_a_clean_report(tmp_path: Path):
    source = tmp_path / "header.docx"
    _write_docx(
        source,
        body="技术指标：10kV试运行30天。",
        extra={
            "word/header1.xml": _paragraph_xml("联系人：张三"),
            "docProps/core.xml": _core_xml("张三"),
            "word/comments.xml": _paragraph_xml("批注张三"),
        },
    )

    report = inspect_hidden_channels([source])
    package, _mapping = build_redaction_package([source], project_alias_id="M26-HEADER")

    assert report["overall_status"] == "found"
    assert report["channel_counts"]["header"] >= 1
    assert report["channel_counts"]["document_properties"] >= 1
    assert "张三" not in json.dumps(report, ensure_ascii=False)
    assert "张三" not in json.dumps(package["hidden_channel_report"], ensure_ascii=False)
    assert package["release_readiness"]["text_package_direct_release"] is False
    assert any("不可直接外发" in warning for warning in package["review_warnings"])


def test_hidden_sheet_and_legacy_office_are_not_clear(tmp_path: Path):
    workbook = tmp_path / "hidden.xlsx"
    _write_xlsx(workbook, hidden=True)
    legacy = tmp_path / "old.doc"
    legacy.write_bytes(b"not a real doc")

    report = inspect_hidden_channels([workbook, legacy])
    by_name = {item["file_name"]: item for item in report["files"]}

    assert report["overall_status"] != "clear"
    assert any(channel["kind"] == "hidden_sheet" for channel in by_name["hidden.xlsx"]["channels"])
    assert by_name["old.doc"]["status"] == "conversion_required"


def test_pdf_metadata_is_not_reported_as_clear(tmp_path: Path):
    pypdf = pytest.importorskip("pypdf")
    source = tmp_path / "meta.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Author": "SecretAuthor"})
    with source.open("wb") as handle:
        writer.write(handle)

    report = inspect_hidden_channels([source])

    assert report["overall_status"] == "found"
    assert report["channel_counts"]["document_properties"] >= 1
    assert "SecretAuthor" not in json.dumps(report, ensure_ascii=False)


def test_residual_scan_fails_when_a_replaced_value_remains():
    scan = scan_residuals("人员A仍有张三", {"items": [{"kind": "person", "original": "张三"}]})

    assert scan["status"] == "residual_found"
    assert scan["hit_count"] == 1
    assert "张三" not in json.dumps(scan, ensure_ascii=False)


def test_kept_technical_metric_is_not_residual_and_stays_in_text(tmp_path: Path):
    source = tmp_path / "metric.txt"
    source.write_text("技术指标：10kV试运行30天。", encoding="utf-8")

    package, mapping = build_redaction_package([source], project_alias_id="M26-KEEP")
    scan = scan_residuals(
        package["redacted_text_blocks"][0]["text"],
        mapping,
        kept_values=["10kV"],
        extra_needles=["10kV"],
    )

    assert "10kV" in package["redacted_text_blocks"][0]["text"]
    assert scan["status"] == "clear"
    assert not any(item.get("kind") == "technical_metric" for item in mapping["items"])


def test_workflow_flags_incomplete_replacement(monkeypatch, tmp_path: Path):
    def replace_once(text, mapping):
        original = "张三"
        if original not in text:
            return text
        return text.replace(original, "人员A", 1)

    monkeypatch.setattr("redaction_assistant.workflow.redact_text", replace_once)
    source = tmp_path / "twice.txt"
    source.write_text("联系人：张三。抄送张三。", encoding="utf-8")

    package, _mapping = build_redaction_package([source], project_alias_id="M26-RESIDUAL")

    assert package["residual_scan"]["status"] == "residual_found"
    assert any("不可直接外发" in warning for warning in package["review_warnings"])


def test_external_docx_removes_confirmed_text_and_keeps_mapping_out(tmp_path: Path):
    source = tmp_path / "letter.docx"
    _write_docx(
        source,
        body="联系人：张三。技术指标：10kV。",
        extra={
            "word/header1.xml": _paragraph_xml("联系人：张三"),
            "docProps/core.xml": _core_xml("张三"),
            "word/comments.xml": _paragraph_xml("批注张三"),
        },
    )
    out = tmp_path / "out"
    package, mapping = build_redaction_package([source], project_alias_id="M26-EXPORT")
    outputs = write_package(out, package, mapping, source_files=[source])
    release_dir = outputs["external_release"]
    manifest = json.loads((release_dir / "external_release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"][0]["status"] == "exported", manifest["files"][0]
    exported = release_dir / manifest["files"][0]["output_name"]

    assert exported.exists()
    assert "张三" not in _zip_text(exported)
    assert "10kV" in _zip_text(exported)
    assert not list(release_dir.rglob("local_mapping*"))
    assert manifest["direct_release_claim"] is False
    assert manifest["files"][0]["status"] == "exported"


def test_hidden_sheet_and_unrenderable_pdf_do_not_enter_external_release(tmp_path: Path):
    workbook = tmp_path / "hidden.xlsx"
    _write_xlsx(workbook, [["联系人", "张三"]], hidden=True)
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    out = tmp_path / "out"
    package, mapping = build_redaction_package([workbook, pdf], project_alias_id="M26-BLOCK")

    outputs = write_external_release(
        out,
        [workbook, pdf],
        package,
        mapping,
        pdf_engine=lambda source, dest, needles: {"status": "blocked", "reason": "render_dependency_unavailable"},
    )
    manifest = json.loads(outputs["external_release_manifest"].read_text(encoding="utf-8"))
    assert manifest["files"][0]["status"] == "blocked"
    assert manifest["files"][0]["reason"] == "hidden_sheet"
    assert manifest["files"][1]["status"] == "blocked"
    assert manifest["files"][1]["reason"] == "pdf_external_release_disabled"
    assert not list(outputs["external_release"].glob("*.xlsx"))
    assert not list(outputs["external_release"].glob("*.pdf"))
    assert not list(outputs["external_release"].rglob("local_mapping*"))


def test_text_pdf_external_release_is_conservatively_disabled(tmp_path: Path):
    source = tmp_path / "text.pdf"
    source.write_bytes(_latin_pdf(b"ZhangSanPhone"))
    out = tmp_path / "out"
    outputs = write_external_release(
        out,
        [source],
        {
            "residual_scan": {"status": "clear"},
            "hidden_channel_report": {
                "files": [{"source_index": 0, "file_name": "text.pdf", "status": "clear", "channels": []}]
            },
        },
        {"items": [{"kind": "person", "original": "ZhangSanPhone"}]},
    )
    manifest = json.loads(outputs["external_release_manifest"].read_text(encoding="utf-8"))

    assert manifest["files"][0]["status"] == "blocked"
    assert manifest["files"][0]["reason"] == "pdf_external_release_disabled"
    assert not list(outputs["external_release"].glob("*.pdf"))


def test_support_bundle_keeps_channel_counts_without_channel_text():
    bundle = build_support_bundle(
        {"processable_count": 1},
        {
            "status": "completed",
            "release_summary": {
                "hidden_channel_status": "found",
                "residual_status": "clear",
                "residual_hit_count": 0,
                "channel_counts": {"header": 1},
                "sample": "张三",
            },
        },
    )

    assert bundle["release_summary"]["channel_counts"] == {"header": 1}
    assert "张三" not in json.dumps(bundle, ensure_ascii=False)


def test_desktop_shell_says_package_is_not_directly_releasable(tmp_path: Path):
    shell = build_desktop_shell(tmp_path, version="m26", service_url="http://127.0.0.1:8765")
    html = (shell / "index.html").read_text(encoding="utf-8")

    assert "不可直接外发" in html
    assert "不是已销毁原文的文件" in html


def _write_docx(path: Path, body: str, extra: dict[str, str] | None = None) -> None:
    from docx import Document

    document = Document()
    document.add_paragraph(body)
    document.save(path)
    with zipfile.ZipFile(path) as handle:
        payload = {name: handle.read(name) for name in handle.namelist()}
    payload.update(extra or {})
    with zipfile.ZipFile(path, "w") as handle:
        for name, data in payload.items():
            handle.writestr(name, data)


def _write_xlsx(path: Path, rows: list[list[str]] | None = None, hidden: bool = False) -> None:
    rows = rows or [["指标", "数值"]]
    values = [cell for row in rows for cell in row]
    shared = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<sst xmlns="{X_NS}">'
        + "".join(f"<si><t>{value}</t></si>" for value in values)
        + "</sst>"
    )
    state = ' state="hidden"' if hidden else ""
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<workbook xmlns="{X_NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="隐藏表" sheetId="1"{state} r:id="rId1"/></sheets></workbook>'
    )
    with zipfile.ZipFile(path, "w") as handle:
        handle.writestr("[Content_Types].xml", "<Types/>")
        handle.writestr("xl/sharedStrings.xml", shared)
        handle.writestr("xl/workbook.xml", workbook)
        handle.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{X_NS}"><sheetData/></worksheet>')


def _paragraph_xml(text: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
    )


def _core_xml(author: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:creator>{author}</dc:creator><dc:title>{author}</dc:title></cp:coreProperties>"
    )


def _latin_pdf(text: bytes) -> bytes:
    stream = b"BT /F1 18 Tf 40 100 Td (" + text + b") Tj ET"
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length " + str(len(stream)).encode("ascii") + b" >> stream\n" + stream + b"\nendstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )


def _zip_text(path: Path) -> str:
    chunks = []
    with zipfile.ZipFile(path) as handle:
        for name in handle.namelist():
            if name.endswith(".xml"):
                root = ET.fromstring(handle.read(name))
                for node in root.iter():
                    if node.text:
                        chunks.append(node.text)
    return "\n".join(chunks)

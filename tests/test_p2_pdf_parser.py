"""P2-2 / P2-7: Tests for pypdf-based PDF text extraction and improved scanned PDF detection."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.parsers import _looks_like_scanned_pdf, _parse_text_pdf, parse_file


class _FakePdfPage:
    def extract_text(self) -> str:
        return "压缩文本项目 合同金额120万元"


class _FakePdfReader:
    def __init__(self, path: str):
        self.pages = [_FakePdfPage()]


def test_scanned_pdf_detection_with_text_stream_is_not_scanned(tmp_path: Path):
    """A PDF with BT/ET text operators should NOT be classified as scanned."""
    pdf = tmp_path / "text_with_image.pdf"
    # Minimal PDF with both a text stream (BT...ET) and an image XObject
    pdf.write_bytes(b"%PDF-1.4\nBT /F1 12 Tf (Hello) Tj ET\n/Subtype /Image\n%%EOF")
    assert _looks_like_scanned_pdf(pdf) is False


def test_scanned_pdf_detection_image_only_is_scanned(tmp_path: Path):
    """A PDF with only images and no text streams should be classified as scanned."""
    pdf = tmp_path / "scanned.pdf"
    pdf.write_bytes(b"%PDF-1.4\n/Subtype /Image\n/DCTFilter\n%%EOF")
    assert _looks_like_scanned_pdf(pdf) is True


def test_scanned_pdf_detection_with_text_marker_not_scanned(tmp_path: Path):
    """A PDF with /Text marker should NOT be classified as scanned."""
    pdf = tmp_path / "text_pdf.pdf"
    pdf.write_bytes(b"%PDF-1.4\n/Text\nsome content\n%%EOF")
    assert _looks_like_scanned_pdf(pdf) is False


def test_parse_text_pdf_returns_blocks_for_simple_pdf(tmp_path: Path):
    """Even without pypdf, the regex fallback should extract literal text."""
    pdf = tmp_path / "simple.pdf"
    pdf.write_bytes(b"%PDF-1.4\n(Hello World) Tj\n%%EOF")
    blocks = _parse_text_pdf(pdf)
    assert len(blocks) == 1
    assert "Hello World" in blocks[0]["text"]


def test_pypdf_dependency_declared():
    """requirements.txt should declare pypdf as a dependency."""
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "pypdf" in requirements


def test_parse_file_pdf_manifest_ok(tmp_path: Path):
    """parse_file should return ok status for a text-based PDF."""
    pdf = tmp_path / "text.pdf"
    pdf.write_bytes(b"%PDF-1.4\nBT /F1 12 Tf (Test Content) Tj ET\n%%EOF")
    blocks, manifest = parse_file(pdf)
    assert manifest["parser_status"] == "ok"
    assert manifest["file_type"] == "pdf"


def test_parse_file_pdf_prefers_pypdf_before_scanned_detection(tmp_path: Path, monkeypatch):
    """A text PDF with image markers and compressed text should not be forced to OCR."""
    import redaction_assistant.parsers as parsers

    pdf = tmp_path / "compressed_text_with_image.pdf"
    pdf.write_bytes(b"%PDF-1.4\n/Subtype /Image\n/Filter /FlateDecode\nstream\nx\x9c...\nendstream\n%%EOF")
    monkeypatch.setattr(parsers, "_PYPDF_AVAILABLE", True)
    monkeypatch.setattr(parsers.pypdf, "PdfReader", _FakePdfReader)

    blocks, manifest = parse_file(pdf)

    assert manifest["parser_status"] == "ok"
    assert blocks
    assert "压缩文本项目" in blocks[0]["text"]

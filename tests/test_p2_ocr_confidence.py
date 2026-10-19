"""P2-6: Tests for OCR confidence threshold gate."""
from __future__ import annotations

import sys
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant import workflow
from redaction_assistant.workflow import OCR_CONFIDENCE_THRESHOLD, _ocr_blocks_for_file, _review_warnings


def test_low_confidence_ocr_adds_warning(tmp_path: Path, monkeypatch):
    """OCR result with confidence below threshold should add a low_confidence warning."""
    scan_path = tmp_path / "scan.pdf"
    scan_path.write_bytes(b"%PDF-1.4 dummy")

    def mock_extract(path, **kwargs):
        return {
            "status": "ok",
            "engine": "test-engine",
            "text": "Some OCR text with sensitive info",
            "confidence": 0.3,
            "pages_processed": 1,
        }

    monkeypatch.setattr(workflow, "extract_text_with_ocr", mock_extract)

    manifest_item: dict = {}
    blocks = _ocr_blocks_for_file(scan_path, manifest_item, ocr_max_pages=5)

    assert len(blocks) == 1
    assert manifest_item["ocr_status"] == "ok"
    assert manifest_item["ocr_confidence"] == 0.3
    assert any("ocr_low_confidence" in w for w in manifest_item.get("warnings", []))


def test_high_confidence_ocr_no_low_confidence_warning(tmp_path: Path, monkeypatch):
    """OCR result with confidence above threshold should NOT add a low_confidence warning."""
    scan_path = tmp_path / "scan.pdf"
    scan_path.write_bytes(b"%PDF-1.4 dummy")

    def mock_extract(path, **kwargs):
        return {
            "status": "ok",
            "engine": "test-engine",
            "text": "High quality OCR text",
            "confidence": 0.95,
            "pages_processed": 1,
        }

    monkeypatch.setattr(workflow, "extract_text_with_ocr", mock_extract)

    manifest_item: dict = {}
    blocks = _ocr_blocks_for_file(scan_path, manifest_item, ocr_max_pages=5)

    assert len(blocks) == 1
    assert not any("ocr_low_confidence" in w for w in manifest_item.get("warnings", []))


def test_review_warnings_includes_low_confidence_files():
    """_review_warnings should mention files with low OCR confidence."""
    manifest = [
        {
            "file_name": "scan1.pdf",
            "parser_status": "ok",
            "warnings": ["ocr_applied", "ocr_low_confidence:0.30"],
        },
        {
            "file_name": "text1.txt",
            "parser_status": "ok",
            "warnings": [],
        },
    ]
    warnings = _review_warnings("some redacted text", {"items": []}, manifest)
    low_conf_warning = [w for w in warnings if "OCR" in w and "置信度" in w]
    assert len(low_conf_warning) == 1
    assert "scan1.pdf" in low_conf_warning[0]


def test_threshold_is_configurable(monkeypatch):
    """Threshold should be read from DRA_OCR_CONFIDENCE_THRESHOLD env var."""
    monkeypatch.setattr(workflow, "OCR_CONFIDENCE_THRESHOLD", 0.8)
    assert workflow.OCR_CONFIDENCE_THRESHOLD == 0.8


def test_invalid_threshold_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("DRA_OCR_CONFIDENCE_THRESHOLD", "not-a-number")

    reloaded = importlib.reload(workflow)

    assert reloaded.OCR_CONFIDENCE_THRESHOLD == 0.5

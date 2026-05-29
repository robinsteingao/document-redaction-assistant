from __future__ import annotations

from typing import Any


def assess_ocr_quality(manifest: dict[str, Any], extracted_text: str = "") -> dict[str, Any]:
    warnings = set(manifest.get("warnings") or [])
    text_len = len((extracted_text or "").strip())
    if manifest.get("parser_status") == "ocr_required" or "ocr_required" in warnings:
        return {
            "status": "blocked",
            "reason": "ocr_required",
            "allow_upload": False,
            "text_length": text_len,
            "message": "疑似扫描件或图片型 PDF，需要 OCR 处理后再生成正式上传包。",
        }
    if text_len < 20 and manifest.get("file_type") == "pdf":
        return {
            "status": "warning",
            "reason": "low_text_yield",
            "allow_upload": True,
            "text_length": text_len,
            "message": "PDF 文本抽取量较低，建议人工复核。"
        }
    return {
        "status": "ok",
        "reason": "text_available",
        "allow_upload": True,
        "text_length": text_len,
        "message": "文本抽取可用于本地脱敏。"
    }

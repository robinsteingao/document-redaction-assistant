from __future__ import annotations

import hashlib
import re
import zipfile
from html import unescape
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET

try:
    import pypdf  # type: ignore[import-untyped]
    _PYPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _PYPDF_AVAILABLE = False


TEXT_SUFFIXES = {".txt", ".md"}

# security: 防止 DOCX/XLSX (ZIP 容器) ZIP 炸弹资源耗尽
_MAX_ZIP_MEMBERS = 2048
_MAX_ZIP_MEMBER_SIZE = 64 * 1024 * 1024  # 单成员展开 64MiB
_MAX_ZIP_TOTAL_SIZE = 256 * 1024 * 1024  # 总展开 256MiB


def _check_zip_budget(zf: zipfile.ZipFile) -> None:
    """校验 ZIP 容器成员数与展开大小预算，防 ZIP 炸弹内存/磁盘耗尽。"""
    infos = zf.infolist()
    if len(infos) > _MAX_ZIP_MEMBERS:
        raise ValueError("zip member count exceeds limit")
    total = 0
    for info in infos:
        total += info.file_size
        if info.file_size > _MAX_ZIP_MEMBER_SIZE:
            raise ValueError("zip member too large")
        if total > _MAX_ZIP_TOTAL_SIZE:
            raise ValueError("zip expansion exceeds limit")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_file(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = Path(path)
    suffix = path.suffix.lower()
    manifest = {
        "file_name": path.name,
        "file_hash": file_sha256(path),
        "file_type": suffix.lstrip("."),
        "parser_status": "ok",
        "warnings": [],
    }
    try:
        if suffix in TEXT_SUFFIXES:
            blocks = _parse_text(path)
        elif suffix == ".docx":
            blocks = _parse_docx(path)
        elif suffix == ".xlsx":
            blocks = _parse_xlsx(path)
        elif suffix == ".pdf":
            blocks = _parse_text_pdf(path, allow_visible_fallback=False)
            if blocks:
                pass
            elif _looks_like_scanned_pdf(path):
                blocks = []
                manifest["parser_status"] = "ocr_required"
                manifest["warnings"].append("ocr_required")
            else:
                blocks = _parse_text_pdf(path, allow_visible_fallback=True)
        else:
            blocks = []
            manifest["parser_status"] = "unsupported"
            manifest["warnings"].append(f"unsupported_format:{suffix}")
    except Exception as exc:  # keep local tool recoverable per file
        blocks = []
        manifest["parser_status"] = "failed"
        manifest["warnings"].append(f"parse_failed:{type(exc).__name__}")

    for idx, block in enumerate(blocks, start=1):
        block.setdefault("block_id", f"{path.stem}-{idx}")
        block.setdefault("file_name", path.name)
    return blocks, manifest


def _parse_text(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [{"location": "text:1", "text": text}]


def _parse_docx(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        _check_zip_budget(zf)
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    blocks: list[dict[str, Any]] = []
    for p_idx, p in enumerate(root.findall(".//w:p", ns), start=1):
        parts = [node.text or "" for node in p.findall(".//w:t", ns)]
        text = "".join(parts).strip()
        if text:
            blocks.append({"location": f"paragraph:{p_idx}", "text": text})
    return blocks


def _parse_xlsx(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        _check_zip_budget(zf)
        shared = _read_shared_strings(zf)
        sheet_names = sorted(
            name for name in zf.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        )
        blocks: list[dict[str, Any]] = []
        for sheet_idx, sheet_name in enumerate(sheet_names, start=1):
            root = ET.fromstring(zf.read(sheet_name))
            ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for row in root.findall(".//x:row", ns):
                values: list[str] = []
                refs: list[str] = []
                for cell in row.findall("x:c", ns):
                    ref = cell.attrib.get("r", "")
                    value = _cell_text(cell, shared, ns)
                    if value:
                        refs.append(ref)
                        values.append(value)
                if values:
                    row_no = row.attrib.get("r", "?")
                    blocks.append({
                        "location": f"sheet{sheet_idx}:row{row_no}:{','.join(refs)}",
                        "text": " | ".join(values),
                        "structure": {
                            "kind": "table_row",
                            "sheet": sheet_idx,
                            "row": row_no,
                            "cells": [
                                {"ref": ref, "text": value}
                                for ref, value in zip(refs, values)
                            ],
                        },
                    })
    return blocks


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = []
    for si in root.findall(".//x:si", ns):
        texts = [node.text or "" for node in si.findall(".//x:t", ns)]
        values.append("".join(texts))
    return values


def _cell_text(cell: ET.Element, shared: list[str], ns: dict[str, str]) -> str:
    value_node = cell.find("x:v", ns)
    if value_node is None or value_node.text is None:
        inline = cell.find(".//x:t", ns)
        return (inline.text or "").strip() if inline is not None else ""
    raw = value_node.text.strip()
    if cell.attrib.get("t") == "s":
        try:
            return shared[int(raw)].strip()
        except (ValueError, IndexError):
            return ""
    return raw


def _parse_text_pdf(path: Path, *, allow_visible_fallback: bool = True) -> list[dict[str, Any]]:
    # Prefer pypdf for proper FlateDecode text extraction
    if _PYPDF_AVAILABLE:
        text = _extract_pdf_text_pypdf(path)
        if text.strip():
            return [{"location": "pdf:text", "text": text.strip()}]
    # Fallback: regex scan for unencrypted/uncompressed PDF text operators
    raw = path.read_bytes().decode("utf-8", errors="ignore")
    literal_texts = re.findall(r"\((.*?)\)\s*Tj", raw, flags=re.DOTALL)
    array_texts = []
    for arr in re.findall(r"\[(.*?)\]\s*TJ", raw, flags=re.DOTALL):
        array_texts.extend(re.findall(r"\((.*?)\)", arr, flags=re.DOTALL))
    text = "\n".join(unescape(t.replace(r"\)", ")").replace(r"\(", "(")) for t in literal_texts + array_texts)
    if not text.strip() and allow_visible_fallback:
        # Last-resort fallback for text-based PDFs generated by simple tools.
        visible = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9:：,，.。;%％≤>=\-\s]", " ", raw)
        text = re.sub(r"\s+", " ", visible)
    return [{"location": "pdf:text", "text": text.strip()}] if text.strip() else []


def _extract_pdf_text_pypdf(path: Path) -> str:
    """Extract text from a text-based PDF using pypdf."""
    try:
        reader = pypdf.PdfReader(str(path))
    except Exception:
        return ""
    parts: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            parts.append(page_text)
    return "\n".join(parts)


def _looks_like_scanned_pdf(path: Path) -> bool:
    raw = path.read_bytes()
    # If the PDF contains text content streams (BT/ET operators or /Text),
    # treat it as a text-based PDF, not a scanned image.
    if b"BT" in raw and b"ET" in raw:
        return False
    if b"/Text" in raw:
        return False
    # No text streams found — if it has images, it's likely a scanned PDF.
    return b"/Subtype /Image" in raw or b"/Image" in raw

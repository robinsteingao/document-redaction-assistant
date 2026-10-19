from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

from .parsers import _check_zip_budget


X_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

LEGACY_SUFFIXES = {".doc", ".xls", ".wps"}
PLAIN_SUFFIXES = {".txt", ".md"}
PROPERTY_KEYS = ("/Author", "/Title", "/Creator", "/Producer", "/Subject", "/Keywords")


def ooxml_safety_channels(zf: zipfile.ZipFile) -> list[dict[str, Any]]:
    """Inventory opaque/unknown parts and external links; never treat them as text."""
    _check_zip_budget(zf)
    channels = []
    names = zf.namelist()
    if len(names) != len(set(names)):
        raise ValueError("duplicate_zip_member")
    for name in names:
        if name.endswith("/"):
            continue
        if "\\" in name or name.startswith("/") or ".." in name.split("/"):
            raise ValueError("unsafe_zip_member")
        # Only the standard package thumbnail is removable without touching stories.
        if re.fullmatch(r"docProps/thumbnail\.(jpeg|jpg|png|wmf|emf)", name):
            channels.append({"kind": "thumbnail", "count": 1})
            continue
        if name.endswith(".rels"):
            root = ET.fromstring(zf.read(name))
            rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
            if root.tag != f"{{{rel_ns}}}Relationships" or any(
                node.tag != f"{{{rel_ns}}}Relationship" for node in root
            ):
                raise ValueError("unknown_relationship_part")
            if name != "_rels/.rels":
                if "/_rels/" not in name:
                    raise ValueError("unknown_relationship_part")
                owner_dir, owner_file = name.rsplit("/_rels/", 1)
                if f"{owner_dir}/{owner_file[:-5]}" not in names:
                    raise ValueError("orphan_relationship_part")
            if any(node.attrib.get("TargetMode", "").lower() == "external" for node in root):
                channels.append({"kind": "external_relationship", "count": 1})
            continue
        if "/embeddings/" in name or "oleObject" in name:
            kind = "embedded_object"
        elif "/media/" in name:
            kind = "binary_media"
        elif re.fullmatch(r"customXml/(item|itemProps)\d+\.xml", name):
            root = ET.fromstring(zf.read(name))
            if root.tag not in {
                "{http://schemas.openxmlformats.org/officeDocument/2006/bibliography}Sources",
                "{http://schemas.openxmlformats.org/officeDocument/2006/customXml}datastoreItem",
            }:
                channels.append({"kind": "unknown_part", "count": 1})
            continue
        elif not _known_xml_part(name):
            kind = "unknown_part"
        else:
            continue
        channels.append({"kind": kind, "count": 1})
    return channels


def _known_xml_part(name: str) -> bool:
    return bool(re.fullmatch(
        r"\[Content_Types\]\.xml|docProps/(core|app|custom)\.xml|"
        r"word/(document|styles|stylesWithEffects|settings|webSettings|fontTable|numbering|"
        r"comments|footnotes|endnotes|header\d+|footer\d+)\.xml|word/theme/theme\d+\.xml|"
        r"xl/(workbook|styles|sharedStrings|calcChain)\.xml|xl/theme/theme\d+\.xml|"
        r"xl/worksheets/sheet\d+\.xml", name,
    ))


def inspect_hidden_channels(files: Iterable[Path | str]) -> dict[str, Any]:
    """Read-only hidden-channel inventory. The report never includes channel text."""
    inspected = []
    for index, source in enumerate(files):
        path = Path(source)
        inspected.append(_inspect_one(path, index))
    return _public_report(inspected)


def extract_channel_texts(path: Path | str) -> list[str]:
    """Return private detection text; errors must reach the fail-closed exporter."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _docx_texts(path)
    if suffix == ".xlsx":
        return _xlsx_channel_texts(path)
    if suffix == ".pdf":
        return _pdf_property_texts(path)
    return []


def _inspect_one(path: Path, index: int) -> dict[str, Any]:
    record = {
        "source_index": index,
        "file_name": path.name,
        "status": "unverified",
        "reason": "",
        "channels": [],
    }
    suffix = path.suffix.lower()
    if not path.exists() or not path.is_file():
        record["status"] = "unverified"
        record["reason"] = "file_unreadable"
        return record
    if suffix in LEGACY_SUFFIXES:
        record["status"] = "conversion_required"
        record["reason"] = "conversion_required"
        return record
    if suffix in PLAIN_SUFFIXES:
        record["status"] = "clear"
        record["reason"] = "no_container"
        return record
    try:
        if suffix == ".docx":
            channels = _docx_channels(path)
        elif suffix == ".xlsx":
            channels = _xlsx_channels(path)
        elif suffix == ".pdf":
            status, channels, reason = _pdf_channels(path)
            record["channels"] = channels
            record["status"] = status
            record["reason"] = reason
            return record
        else:
            record["status"] = "unsupported"
            record["reason"] = f"unsupported_format:{suffix}"
            return record
    except Exception:
        record["status"] = "unverified"
        record["reason"] = "inspect_failed"
        return record
    record["channels"] = channels
    record["status"] = "found" if channels else "clear"
    record["reason"] = ""
    return record


def _public_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    files = []
    for record in records:
        public_channels = []
        for channel in record.get("channels") or []:
            kind = str(channel.get("kind") or "unknown")
            count = int(channel.get("count") or 0)
            counts[kind] = counts.get(kind, 0) + count
            public_channels.append({"kind": kind, "count": count})
        files.append({
            "source_index": record.get("source_index"),
            "file_name": record.get("file_name"),
            "status": record.get("status"),
            "reason": record.get("reason") or "",
            "channels": public_channels,
        })
    statuses = [item.get("status") for item in files]
    if any(status == "found" for status in statuses):
        overall = "found"
    elif any(status in {"unverified", "conversion_required", "unsupported"} for status in statuses):
        overall = "unverified"
    else:
        overall = "clear"
    return {
        "schema_version": "hidden_channel_report.v1",
        "overall_status": overall,
        "file_count": len(files),
        "channel_counts": dict(sorted(counts.items())),
        "files": files,
    }


def _docx_channels(path: Path) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as zf:
        _check_zip_budget(zf)
        names = zf.namelist()
        channels.extend(ooxml_safety_channels(zf))
        _add_if_text(channels, "header", _xml_texts(zf, [name for name in names if _is_header(name)]))
        _add_if_text(channels, "footer", _xml_texts(zf, [name for name in names if _is_footer(name)]))
        _add_if_text(channels, "footnote", _xml_texts(zf, [name for name in names if name.startswith("word/footnotes")]))
        _add_if_text(channels, "endnote", _xml_texts(zf, [name for name in names if name.startswith("word/endnotes")]))
        _add_if_text(channels, "comment", _xml_texts(zf, [name for name in names if name.startswith("word/comments")]))
        revision_count = 0
        textbox_count = 0
        for name in names:
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            root = ET.fromstring(zf.read(name))
            revision_count += _count_local(root, {"ins", "del", "moveFrom", "moveTo"})
            textbox_count += _count_local(root, {"txbxContent"})
        if revision_count:
            channels.append({"kind": "revision", "count": revision_count})
        if textbox_count:
            channels.append({"kind": "text_box", "count": textbox_count})
        property_count = len(_core_property_texts(zf))
        if property_count:
            channels.append({"kind": "document_properties", "count": property_count})
    return channels


def _xlsx_channels(path: Path) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as zf:
        _check_zip_budget(zf)
        names = zf.namelist()
        channels.extend(ooxml_safety_channels(zf))
        if "xl/workbook.xml" in names:
            root = ET.fromstring(zf.read("xl/workbook.xml"))
            hidden = very_hidden = defined = 0
            for sheet in root.findall(f".//{{{X_NS}}}sheet"):
                state = sheet.attrib.get("state", "visible")
                if state == "hidden":
                    hidden += 1
                elif state == "veryHidden":
                    very_hidden += 1
            for node in root.findall(f".//{{{X_NS}}}definedName"):
                if (node.text or "").strip():
                    defined += 1
            if hidden:
                channels.append({"kind": "hidden_sheet", "count": hidden})
            if very_hidden:
                channels.append({"kind": "very_hidden_sheet", "count": very_hidden})
            if defined:
                channels.append({"kind": "defined_name", "count": defined})
        comment_names = [
            name for name in names
            if name.startswith("xl/comments") or "threadedComment" in name
        ]
        comment_texts = _xml_texts(zf, comment_names)
        if comment_texts:
            channels.append({"kind": "comment", "count": len(comment_texts)})
        property_count = len(_core_property_texts(zf))
        if property_count:
            channels.append({"kind": "document_properties", "count": property_count})
    return channels


def _pdf_channels(path: Path) -> tuple[str, list[dict[str, Any]], str]:
    try:
        import pypdf
    except ImportError:
        return "unverified", [], "pypdf_unavailable"
    try:
        reader = pypdf.PdfReader(str(path))
    except Exception:
        return "unverified", [], "pdf_read_failed"
    channels: list[dict[str, Any]] = []
    try:
        meta = reader.metadata or {}
        count = sum(1 for key in PROPERTY_KEYS if str(meta.get(key) or "").strip())
        if count:
            channels.append({"kind": "document_properties", "count": count})
    except Exception:
        return "unverified", channels, "pdf_metadata_unverified"
    try:
        attached = reader.attachments
    except Exception:
        return "unverified", channels, "pdf_attachment_unverified"
    if attached:
        channels.append({"kind": "attachment", "count": len(attached)})
    try:
        fields = reader.get_fields() or {}
    except Exception:
        return "unverified", channels, "pdf_form_unverified"
    if fields:
        channels.append({"kind": "form", "count": len(fields)})
    annot_count = 0
    try:
        for page in reader.pages:
            annots = page.get("/Annots")
            if annots:
                annot_count += len(annots)
    except Exception:
        return "unverified", channels, "pdf_annotation_unverified"
    if annot_count:
        channels.append({"kind": "annotation", "count": annot_count})
    javascript = _pdf_has_javascript(reader)
    if javascript is None:
        return "unverified", channels, "pdf_javascript_unverified"
    if javascript:
        channels.append({"kind": "javascript", "count": 1})
    return ("found" if channels else "clear"), channels, ""


def _pdf_has_javascript(reader: Any) -> bool | None:
    try:
        root = reader.trailer["/Root"]
        if root is None:
            return False
        root = root.get_object() if hasattr(root, "get_object") else root
        names = root.get("/Names") if hasattr(root, "get") else None
        if names is not None:
            names = names.get_object() if hasattr(names, "get_object") else names
            if hasattr(names, "get") and names.get("/JavaScript") is not None:
                return True
        action = root.get("/OpenAction") if hasattr(root, "get") else None
        if action is not None:
            action = action.get_object() if hasattr(action, "get_object") else action
            if hasattr(action, "get") and (action.get("/JS") is not None or action.get("/JavaScript") is not None):
                return True
    except Exception:
        return None
    return False


def _docx_texts(path: Path) -> list[str]:
    texts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        _check_zip_budget(zf)
        names = zf.namelist()
        interesting = [name for name in names if name.endswith((".xml", ".rels"))]
        texts.extend(_xml_texts(zf, interesting))
    return texts


def _xlsx_channel_texts(path: Path) -> list[str]:
    texts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        _check_zip_budget(zf)
        names = zf.namelist()
        texts.extend(_xml_texts(zf, [name for name in names if name.endswith((".xml", ".rels"))]))
    return texts


def _pdf_property_texts(path: Path) -> list[str]:
    try:
        import pypdf
    except ImportError:
        return []
    try:
        reader = pypdf.PdfReader(str(path))
        meta = reader.metadata or {}
    except Exception:
        return []
    return [str(meta.get(key)).strip() for key in PROPERTY_KEYS if str(meta.get(key) or "").strip()]


def _core_property_texts(zf: zipfile.ZipFile) -> list[str]:
    texts: list[str] = []
    for name in zf.namelist():
        if not name.startswith("docProps/") or not name.endswith(".xml"):
            continue
        root = ET.fromstring(zf.read(name))
        for node in root.iter():
            value = (node.text or "").strip()
            if value and _local(node.tag) in {"creator", "lastModifiedBy", "title", "subject", "description"}:
                texts.append(value)
    return texts


def _xml_texts(zf: zipfile.ZipFile, names: list[str]) -> list[str]:
    texts: list[str] = []
    for name in names:
        if name not in zf.namelist():
            continue
        root = ET.fromstring(zf.read(name))
        for node in root.iter():
            if node.tag in {
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p",
                f"{{{X_NS}}}si", f"{{{X_NS}}}is",
            }:
                joined = "".join(node.itertext())
                if joined.strip():
                    texts.append(joined)
            value = (node.text or "").strip()
            if value:
                texts.append(value)
            texts.extend(value for value in node.attrib.values() if value.strip())
    return texts


def _add_if_text(channels: list[dict[str, Any]], kind: str, texts: list[str]) -> None:
    if texts:
        channels.append({"kind": kind, "count": len(texts)})


def _count_local(root: ET.Element, names: set[str]) -> int:
    return sum(1 for node in root.iter() if _local(node.tag) in names)


def _is_header(name: str) -> bool:
    return name.startswith("word/header")


def _is_footer(name: str) -> bool:
    return name.startswith("word/footer")


def _local(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag

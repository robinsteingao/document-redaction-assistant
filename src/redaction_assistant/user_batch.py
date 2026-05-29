from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable


PROCESSABLE_SUFFIXES = {".docx", ".xlsx", ".pdf", ".txt", ".md"}
CONVERTIBLE_SUFFIXES = {".doc", ".xls", ".wps"}
SKIPPED_SUFFIXES = {".zip", ".rar", ".7z", ".db", ".json", ".jpg", ".jpeg", ".png"}


def collect_user_inputs(inputs: Iterable[str | Path], *, recursive: bool = True) -> dict[str, Any]:
    candidates: list[Path] = []
    missing: list[dict[str, str]] = []
    for raw in inputs:
        path = Path(raw)
        if not path.exists():
            missing.append({"path": str(path), "reason": "path_not_found"})
            continue
        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.iterdir()
            candidates.extend(sorted(p for p in iterator if p.is_file()))
        elif path.is_file():
            candidates.append(path)

    processable: list[Path] = []
    convertible: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for path in sorted(set(candidates)):
        suffix = path.suffix.lower()
        entry = {
            "path": str(path),
            "file_name": path.name,
            "extension": suffix or "(none)",
            "bytes": path.stat().st_size,
        }
        if suffix in PROCESSABLE_SUFFIXES:
            processable.append(path)
        elif suffix in CONVERTIBLE_SUFFIXES:
            convertible.append({**entry, "reason": "office_conversion_required", "target_extension": _target_extension(suffix)})
        elif suffix in SKIPPED_SUFFIXES or not suffix:
            skipped.append({**entry, "reason": "not_document_input"})
        else:
            unsupported.append({**entry, "reason": "unsupported_format"})

    by_extension = Counter(path.suffix.lower() for path in processable)
    return {
        "schema_version": "document_redaction_user_input_plan.v1",
        "processable_files": [str(path) for path in processable],
        "processable_count": len(processable),
        "convertible_files": convertible,
        "convertible_count": len(convertible),
        "unsupported_files": unsupported,
        "unsupported_count": len(unsupported),
        "skipped_files": skipped,
        "skipped_count": len(skipped),
        "missing_paths": missing,
        "missing_count": len(missing),
        "total_bytes": sum(path.stat().st_size for path in processable),
        "by_extension": dict(sorted(by_extension.items())),
        "recommended_ocr_modes": ["quick", "full"],
        "warnings": _warnings(processable, convertible, unsupported, missing),
    }


def ocr_max_pages_for_mode(mode: str | None) -> int | None:
    normalized = (mode or "quick").strip().lower()
    if normalized in {"quick", "preview", "fast"}:
        return 1
    if normalized in {"full", "complete"}:
        return None
    return 1


def _target_extension(suffix: str) -> str:
    if suffix == ".xls":
        return ".xlsx"
    return ".docx"


def _warnings(
    processable: list[Path],
    convertible: list[dict[str, Any]],
    unsupported: list[dict[str, Any]],
    missing: list[dict[str, str]],
) -> list[str]:
    warnings: list[str] = []
    pdf_count = sum(1 for path in processable if path.suffix.lower() == ".pdf")
    if pdf_count >= 10:
        warnings.append(f"检测到 {pdf_count} 个 PDF，建议先使用快速预览模式。")
    if convertible:
        warnings.append(f"检测到 {len(convertible)} 个旧版 Office/WPS 文件，将先尝试本地转换后处理。")
    if unsupported:
        warnings.append(f"有 {len(unsupported)} 个文件格式暂不支持。")
    if missing:
        warnings.append(f"有 {len(missing)} 个路径不存在。")
    return warnings

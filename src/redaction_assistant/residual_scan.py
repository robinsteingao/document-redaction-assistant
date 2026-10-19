from __future__ import annotations

from typing import Any, Iterable


NOT_A_CLEARANCE_NOTE = "自检只覆盖已识别且应替换的字段，不是安全证明。当前结果包不可直接外发。"


def scan_residuals(
    redacted_text: str,
    mapping: dict[str, Any],
    *,
    kept_values: Iterable[str] | None = None,
    extra_needles: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Find replacements that did not land. Hit values stay out of the public report."""
    kept = {value for value in (kept_values or []) if value}
    needles: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in mapping.get("items") or []:
        original = str(item.get("original") or "")
        if not original or original in seen or original in kept:
            continue
        if item.get("kind") == "technical_metric" and item.get("strategy") == "keep":
            continue
        seen.add(original)
        needles.append((original, "mapping"))
    for value in extra_needles or []:
        original = str(value or "")
        if not original or original in seen or original in kept:
            continue
        seen.add(original)
        needles.append((original, "dictionary"))
    hits = [source for original, source in needles if original in (redacted_text or "")]
    status = "residual_found" if hits else "clear"
    return {
        "schema_version": "residual_scan.v1",
        "status": status,
        "hit_count": len(hits),
        "checked_field_count": len(needles),
        "note": NOT_A_CLEARANCE_NOTE,
    }


def residual_warning(scan: dict[str, Any] | None) -> str | None:
    if not scan or scan.get("status") == "not_scanned":
        return "残留自检未执行。当前结果包不可直接外发。"
    if scan.get("status") == "residual_found":
        return f"残留自检发现 {int(scan.get('hit_count') or 0)} 处应替换字段仍留在脱敏文本中。当前结果包不可直接外发。"
    return None

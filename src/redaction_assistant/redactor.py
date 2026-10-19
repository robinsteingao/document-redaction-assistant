from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from .rules import Entity


def build_mapping(entities: list[Entity], review_decisions: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    counters: dict[str, int] = defaultdict(int)
    items: list[dict[str, Any]] = []
    for entity in entities:
        candidate_id = candidate_id_for(entity)
        decision = (review_decisions or {}).get(candidate_id, {})
        action = decision.get("action")
        if action == "keep" or (entity.strategy == "keep" and action != "redact"):
            continue
        strategy = decision.get("strategy") or ("mask" if entity.strategy == "keep" else entity.strategy)
        counters[entity.placeholder_prefix] += 1
        placeholder = f"{entity.placeholder_prefix}{_letter(counters[entity.placeholder_prefix])}"
        replacement = placeholder
        if strategy == "range" and entity.replacement_hint:
            replacement = f"{placeholder}（{entity.replacement_hint}）"
        elif strategy == "mask":
            replacement = placeholder
        items.append({
            "candidate_id": candidate_id,
            "kind": entity.kind,
            "original": entity.original,
            "placeholder": placeholder,
            "replacement": replacement,
            "strategy": strategy,
            "default_strategy": entity.strategy,
            "preservation_value": entity.replacement_hint if strategy == "range" else None,
        })
    return {
        "schema_version": "redaction_mapping.v1",
        "items": items,
        "mapping_hash": mapping_hash({"items": items}),
    }


def mapping_hash(mapping: dict[str, Any]) -> str:
    data = json.dumps(mapping.get("items", []), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def redact_text(text: str, mapping: dict[str, Any]) -> str:
    """Span-based replacement: collect all match positions, then replace back-to-front.

    Unlike naive str.replace, this avoids cascading replacements (where an earlier
    replacement consumes text needed by a later item) and sub-string collisions
    (where a shorter original is a sub-string of a longer one at the same position).
    Longer originals are processed first so they claim their positions before
    shorter sub-strings are considered.
    """
    items = sorted(mapping.get("items", []), key=lambda i: -len(i.get("original", "")))
    pairs = [
        (item.get("original") or "", item.get("replacement") or item.get("placeholder") or "")
        for item in items
    ]
    spans = _collect_spans(text, pairs)
    return _apply_spans(text, spans)


def restore_text(text: str, mapping: dict[str, Any]) -> str:
    """Span-based restoration: collect placeholder/replacement positions, then replace back-to-front.

    Same span strategy as redact_text to avoid cascading or sub-string issues
    when multiple placeholders overlap.
    """
    pairs: list[tuple[str, str]] = []
    for item in mapping.get("items", []):
        placeholder = item.get("placeholder") or ""
        replacement = item.get("replacement") or ""
        original = item.get("original") or ""
        if replacement and replacement != placeholder:
            pairs.append((replacement, original))
        if placeholder:
            pairs.append((placeholder, original))
    pairs.sort(key=lambda p: -len(p[0]))
    spans = _collect_spans(text, pairs)
    return _apply_spans(text, spans)


def _collect_spans(text: str, pairs: list[tuple[str, str]]) -> list[tuple[int, int, str]]:
    """Find all non-overlapping match positions for (search, replacement) pairs.

    Pairs should be pre-sorted by search-string length descending so that
    longer matches claim their positions first.  Overlapping shorter matches
    are skipped.
    """
    spans: list[tuple[int, int, str]] = []
    claimed: list[tuple[int, int]] = []
    for search, replacement in pairs:
        if not search:
            continue
        start = 0
        while start <= len(text) - len(search):
            pos = text.find(search, start)
            if pos == -1:
                break
            end = pos + len(search)
            if not any(not (end <= c_start or pos >= c_end) for c_start, c_end in claimed):
                spans.append((pos, end, replacement))
                claimed.append((pos, end))
            start = end
    return spans


def _apply_spans(text: str, spans: list[tuple[int, int, str]]) -> str:
    """Apply span replacements from back to front to preserve earlier offsets."""
    result = text
    for start, end, replacement in sorted(spans, key=lambda s: -s[0]):
        result = result[:start] + replacement + result[end:]
    return result


def public_mapping_stats(mapping: dict[str, Any]) -> dict[str, Any]:
    by_kind: dict[str, int] = defaultdict(int)
    for item in mapping.get("items", []):
        by_kind[item.get("kind") or "unknown"] += 1
    return {
        "total_fields": len(mapping.get("items", [])),
        "by_kind": dict(sorted(by_kind.items())),
    }


def candidate_id_for(entity: Entity) -> str:
    raw = f"{entity.kind}|{entity.original}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _letter(index: int) -> str:
    # A, B, ... Z, AA, AB...
    if index <= 0:
        return "A"
    chars = []
    n = index
    while n:
        n -= 1
        chars.append(chr(ord("A") + (n % 26)))
        n //= 26
    return "".join(reversed(chars))

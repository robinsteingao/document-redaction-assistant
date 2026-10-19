from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

from .rules import Entity


def build_mapping(entities: list[Entity], review_decisions: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    counters: dict[str, int] = defaultdict(int)
    used: set[str] = set()
    items: list[dict[str, Any]] = []
    for entity in entities:
        decision = (review_decisions or {}).get(candidate_id_for(entity), {})
        item = _mapping_item(entity, decision, counters, used)
        if item is not None:
            items.append(item)
    return {
        "schema_version": "redaction_mapping.v1",
        "items": items,
        "mapping_hash": mapping_hash({"items": items}),
    }


def merge_entities_into_mapping(
    mapping: dict[str, Any],
    entities: list[Entity],
    review_decisions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append newly detected entities with globally unique placeholders.

    Existing items are never renumbered or replaced.  New items continue each
    placeholder prefix's letter sequence, so body fields and hidden-channel
    fields (headers/footers, properties, comments...) share one persistent
    mapping instead of colliding with re-used placeholder names.
    """
    items = [dict(item) for item in mapping.get("items", [])]
    counters: dict[str, int] = defaultdict(int)
    used: set[str] = set()
    for item in items:
        counters[_placeholder_prefix_of(item)] += 1
        placeholder = str(item.get("placeholder") or "")
        if placeholder:
            used.add(placeholder)
    seen = {str(item.get("original") or "") for item in items if item.get("original")}
    changed = False
    for entity in entities:
        if not entity.original or entity.original in seen:
            continue
        decision = (review_decisions or {}).get(candidate_id_for(entity), {})
        item = _mapping_item(entity, decision, counters, used)
        if item is None:
            continue
        items.append(item)
        seen.add(entity.original)
        changed = True
    if not changed:
        return mapping
    return {**mapping, "items": items, "mapping_hash": mapping_hash({"items": items})}


def _mapping_item(
    entity: Entity,
    decision: dict[str, Any],
    counters: dict[str, int],
    used: set[str],
) -> dict[str, Any] | None:
    action = decision.get("action")
    if action == "keep" or (entity.strategy == "keep" and action != "redact"):
        return None
    strategy = decision.get("strategy") or ("mask" if entity.strategy == "keep" else entity.strategy)
    while True:
        counters[entity.placeholder_prefix] += 1
        placeholder = f"{entity.placeholder_prefix}{_letter(counters[entity.placeholder_prefix])}"
        if placeholder not in used:
            break
    used.add(placeholder)
    replacement = placeholder
    if strategy == "range" and entity.replacement_hint:
        replacement = f"{placeholder}（{entity.replacement_hint}）"
    elif strategy == "mask":
        replacement = placeholder
    return {
        "candidate_id": candidate_id_for(entity),
        "kind": entity.kind,
        "original": entity.original,
        "placeholder": placeholder,
        "replacement": replacement,
        "strategy": strategy,
        "default_strategy": entity.strategy,
        "preservation_value": entity.replacement_hint if strategy == "range" else None,
    }


def _placeholder_prefix_of(item: dict[str, Any]) -> str:
    for key in ("placeholder", "replacement"):
        text = str(item.get(key) or "")
        text = re.sub(r"（[^）]*）\s*$", "", text)
        match = re.match(r"^(.*?)([A-Z]+)$", text)
        if match and match.group(1):
            return match.group(1)
    return ""


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

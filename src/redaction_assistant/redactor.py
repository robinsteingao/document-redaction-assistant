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
        if decision.get("action") == "keep":
            continue
        strategy = decision.get("strategy") or entity.strategy
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
    result = text
    items = sorted(mapping.get("items", []), key=lambda i: -len(i.get("original", "")))
    for item in items:
        original = item.get("original") or ""
        replacement = item.get("replacement") or item.get("placeholder") or ""
        if original:
            result = result.replace(original, replacement)
    return result


def restore_text(text: str, mapping: dict[str, Any]) -> str:
    result = text
    items = sorted(mapping.get("items", []), key=lambda i: -len(i.get("placeholder", "")))
    for item in items:
        placeholder = item.get("placeholder") or ""
        replacement = item.get("replacement") or ""
        original = item.get("original") or ""
        if replacement and replacement != placeholder:
            result = result.replace(replacement, original)
        if placeholder:
            result = result.replace(placeholder, original)
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

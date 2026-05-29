from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_GUARDRAILS = ["本地映射表不得上传", "金额字段不默认清空", "技术指标和验证阶段默认保留"]


def validate_rules_update_package(update_dir: Path | str) -> dict[str, Any]:
    root = Path(update_dir)
    path = root / "rules_manifest.json"
    if not path.exists():
        return {"status": "invalid", "message": "缺少 rules_manifest.json。"}
    try:
        rules = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {"status": "invalid", "message": str(exc)}
    if rules.get("schema_version") != "document_redaction_rules_manifest.v1":
        return {"status": "invalid", "message": "规则 schema_version 不匹配。"}
    guardrails = rules.get("guardrails") or []
    missing = [item for item in REQUIRED_GUARDRAILS if item not in guardrails]
    if missing:
        return {"status": "blocked", "message": f"缺少强制保护规则: {'; '.join(missing)}"}
    for group in rules.get("field_groups") or []:
        if group.get("name") == "technical_metric" and group.get("default_action") != "keep":
            return {"status": "blocked", "message": "技术指标默认策略不得改为非 keep。"}
        if group.get("name") == "amount" and group.get("default_action") not in {"range", "keep"}:
            return {"status": "blocked", "message": "金额字段默认策略不得改为不可计算策略。"}
    return {"status": "valid", "message": "规则更新包可应用。", "version": rules.get("version")}


def apply_rules_update_package(update_dir: Path | str, active_rules_dir: Path | str) -> dict[str, Any]:
    validation = validate_rules_update_package(update_dir)
    if validation["status"] != "valid":
        return validation
    target_root = Path(active_rules_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    rules = json.loads((Path(update_dir) / "rules_manifest.json").read_text(encoding="utf-8-sig"))
    (target_root / "rules_manifest.json").write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "applied", "message": "规则更新已应用。", "version": validation.get("version")}

from __future__ import annotations

from datetime import datetime
from typing import Any

from .redactor import candidate_id_for
from .rules import Entity


ASSESSMENT_IMPACT: dict[str, dict[str, str]] = {
    "technical_metric": {"domain": "trl", "level": "high", "message": "技术指标被脱敏会影响 TRL、技术成熟度和成果先进性判断。"},
    "validation_evidence": {"domain": "trl", "level": "high", "message": "试验、试运行或验收信息被脱敏会影响应用验证和完成度判断。"},
    "amount": {"domain": "benefit", "level": "high", "message": "金额或效益数据被强脱敏会影响经济效益分析。"},
    "patent_id": {"domain": "evidence", "level": "medium", "message": "专利号被脱敏会影响成果证明和外部证据核验，可用稳定占位符保留数量关系。"},
    "software_copyright": {"domain": "evidence", "level": "medium", "message": "软著号被脱敏会影响成果证明和外部证据核验，可用稳定占位符保留数量关系。"},
    "organization": {"domain": "transfer_readiness", "level": "medium", "message": "单位名称被脱敏可能影响应用场景、推广主体和协同关系判断。"},
    "project_name": {"domain": "context", "level": "low", "message": "项目名称脱敏通常可接受，但建议使用稳定项目代号保持材料对应关系。"},
    "contract_id": {"domain": "traceability", "level": "low", "message": "合同编号脱敏通常不影响核心评价，但可能影响证据追溯。"},
    "person": {"domain": "privacy", "level": "none", "message": "人员姓名通常不参与评价，建议默认脱敏。"},
    "phone": {"domain": "privacy", "level": "none", "message": "手机号通常不参与评价，建议默认脱敏。"},
    "email": {"domain": "privacy", "level": "none", "message": "邮箱通常不参与评价，建议默认脱敏。"},
}

LEVEL_SCORE = {"none": 0, "low": 1, "medium": 2, "high": 3}


def build_redaction_impact_summary(
    entities: list[Entity],
    mapping: dict[str, Any],
    review_decisions: dict[str, dict[str, Any]] | None = None,
    customer_confirmed_degradation_risk: bool = False,
) -> dict[str, Any]:
    decisions = review_decisions or {}
    explicit_confirmation = customer_confirmed_degradation_risk is True
    mapped_by_id = {item.get("candidate_id"): item for item in mapping.get("items", []) if item.get("candidate_id")}
    entity_ids = {candidate_id_for(entity) for entity in entities}
    unmatched_decisions = sorted(str(candidate_id) for candidate_id in decisions if str(candidate_id) not in entity_ids)
    impacts: list[dict[str, Any]] = []
    preserved: list[str] = []
    strongly_redacted: list[str] = []
    redacted_assessment_fields: list[str] = []
    kept_sensitive_fields: list[str] = []

    for entity in entities:
        candidate_id = candidate_id_for(entity)
        decision = decisions.get(candidate_id, {})
        mapped_item = mapped_by_id.get(candidate_id)
        is_redacted = mapped_item is not None
        action = "redact" if is_redacted else "keep"
        strategy = str(mapped_item.get("strategy")) if mapped_item else (decision.get("strategy") or entity.strategy)
        profile = ASSESSMENT_IMPACT.get(entity.kind, {"domain": "other", "level": "low", "message": "请复核该字段脱敏后是否影响评价。"})
        effective_level = _effective_level(entity.kind, strategy, profile["level"] if is_redacted else "none")
        if not is_redacted:
            preserved.append(entity.kind)
        elif strategy == "mask":
            strongly_redacted.append(entity.kind)
        if is_redacted and effective_level in {"medium", "high"}:
            redacted_assessment_fields.append(entity.kind)
        if not is_redacted and profile["domain"] == "privacy":
            kept_sensitive_fields.append(entity.kind)
        impacts.append({
            "candidate_id": candidate_id,
            "kind": entity.kind,
            "action": "redact" if is_redacted else "keep",
            "strategy": strategy,
            "impact_domain": profile["domain"],
            "impact_level": effective_level,
            "message": profile["message"],
        })

    max_score = max((LEVEL_SCORE.get(item["impact_level"], 1) for item in impacts if item["action"] == "redact"), default=0)
    if any(item["impact_level"] == "high" and item["action"] == "redact" for item in impacts):
        overall = "blocked_requires_confirmation"
    elif max_score >= 2 or kept_sensitive_fields:
        overall = "warning"
    else:
        overall = "pass"
    return {
        "schema_version": "redaction_impact_summary.v1",
        "overall_level": overall,
        "customer_decisions_present": bool(decisions),
        "customer_confirmed": explicit_confirmation,
        "customer_confirmation_source": "explicit_customer_confirmed_degradation_risk" if explicit_confirmation else None,
        "customer_confirmation_recorded_at": datetime.now().isoformat(timespec="seconds") if explicit_confirmation else None,
        "trl_impact": _domain_level(impacts, "trl"),
        "benefit_impact": _domain_level(impacts, "benefit"),
        "evidence_impact": _domain_level(impacts, "evidence"),
        "transfer_readiness_impact": _domain_level(impacts, "transfer_readiness"),
        "strongly_redacted_fields": sorted(set(strongly_redacted)),
        "redacted_assessment_fields": sorted(set(redacted_assessment_fields)),
        "preserved_assessment_factors": sorted(set(preserved)),
        "kept_sensitive_fields": sorted(set(kept_sensitive_fields)),
        "unmatched_decisions": unmatched_decisions,
        "items": impacts,
        "upload_gate_message": _gate_message(overall),
    }


def _domain_level(impacts: list[dict[str, Any]], domain: str) -> str:
    values = [item["impact_level"] for item in impacts if item["impact_domain"] == domain and item["action"] == "redact"]
    if not values:
        return "none"
    return max(values, key=lambda value: LEVEL_SCORE.get(value, 0))


def _effective_level(kind: str, strategy: str, base_level: str) -> str:
    if base_level == "none":
        return "none"
    if kind == "amount" and strategy == "range":
        return "low"
    if kind in {"patent_id", "software_copyright", "organization", "project_name", "contract_id"} and strategy == "pseudonym":
        return "low"
    return base_level


def _gate_message(overall: str) -> str:
    if overall == "blocked_requires_confirmation":
        return "存在会影响 STPE-AI 评价审查的关键字段脱敏，建议返回复核；如继续上传，需客户确认接受评价降级风险。"
    if overall == "warning":
        return "存在一般评价影响或隐私字段保留，请客户复核后再上传。"
    return "未发现明显评价影响门禁风险。"

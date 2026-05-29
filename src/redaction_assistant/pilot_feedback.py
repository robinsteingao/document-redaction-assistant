from __future__ import annotations

import json
from pathlib import Path


DEFAULT_ISSUES = [
    {
        "id": "M15-PILOT-001",
        "severity": "P1",
        "status": "open",
        "category": "ocr",
        "title": "扫描件 OCR 低置信结果复核",
        "project_alias_id": "未指定",
        "impact": "可能导致扫描版合同或证明材料无法进入脱敏上传包。",
        "next_action": "登记文件类型、OCR 引擎、置信度和人工复核结论；不得记录原始文件路径或原文片段。",
        "owner": "实施人员",
    },
    {
        "id": "M15-PILOT-002",
        "severity": "P1",
        "status": "open",
        "category": "sandbox",
        "title": "生产沙箱导入配置确认",
        "project_alias_id": "未指定",
        "impact": "沙箱地址、环境名或上传边界错误会阻断专家评审前的材料流转。",
        "next_action": "使用生产沙箱配置校验脚本确认 redacted_payload_only、no_mapping 和 no_originals。",
        "owner": "产品/交付",
    },
    {
        "id": "M15-PILOT-003",
        "severity": "P2",
        "status": "open",
        "category": "customer_training",
        "title": "客户本地映射表保管确认",
        "project_alias_id": "未指定",
        "impact": "映射表丢失会影响后续评审报告本地还原。",
        "next_action": "在试点签收单中确认映射表本地保存位置和备份责任人。",
        "owner": "客户代表",
    },
]


def build_pilot_issue_ledger(
    output_dir: Path | str,
    *,
    version: str,
    issues: list[dict] | None = None,
) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    normalized = [_normalize_issue(item) for item in (issues or DEFAULT_ISSUES)]
    ledger = {
        "schema_version": "document_redaction_pilot_issue_ledger.v1",
        "version": version,
        "sensitive_data_policy": {
            "no_raw_file_path": True,
            "no_original_text_snippet": True,
            "project_alias_only": True,
        },
        "allowed_statuses": ["open", "in_progress", "resolved", "deferred"],
        "allowed_severity": ["P0", "P1", "P2", "P3"],
        "issues": normalized,
    }
    ledger_json = root / "pilot_issue_ledger.json"
    ledger_markdown = root / "PILOT_ISSUE_LEDGER.md"
    ledger_json.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    ledger_markdown.write_text(_ledger_markdown(ledger), encoding="utf-8")
    return {"ledger_json": ledger_json, "ledger_markdown": ledger_markdown}


def _normalize_issue(issue: dict) -> dict:
    allowed = {
        "id",
        "severity",
        "status",
        "category",
        "title",
        "project_alias_id",
        "impact",
        "next_action",
        "owner",
    }
    result = {key: str(issue.get(key, "")).strip() for key in allowed}
    result["severity"] = result["severity"] or "P2"
    result["status"] = result["status"] or "open"
    result["project_alias_id"] = result["project_alias_id"] or "未指定"
    return result


def _ledger_markdown(ledger: dict) -> str:
    lines = [
        "# 客户试点问题台账",
        "",
        "记录试点问题时只能使用项目别名，不记录原始文件路径、原文片段和本地映射内容。",
        "",
        "| ID | 等级 | 状态 | 类别 | 标题 | 下一步 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for issue in ledger["issues"]:
        lines.append(
            "| {id} | {severity} | {status} | {category} | {title} | {next_action} |".format(**issue)
        )
    lines.append("")
    return "\n".join(lines)

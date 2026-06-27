from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from .ocr_adapter import extract_text_with_ocr
from .parsers import parse_file
from .redactor import build_mapping, public_mapping_stats, redact_text, restore_text
from .rules import contains_technical_signal, detect_entities_with_dictionary
from .impact import build_redaction_impact_summary
from .crypto import encrypt_mapping_file


def build_redaction_package(
    files: Iterable[Path | str],
    *,
    project_alias_id: str,
    redaction_policy: str = "assessment_preserving",
    customer_dictionary: Path | str | dict | None = None,
    review_decisions: dict[str, dict[str, Any]] | None = None,
    customer_confirmed_degradation_risk: bool = False,
    ocr_max_pages: int | None = None,
    progress_cb: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    file_list = [Path(file) for file in files]
    total = len(file_list)
    for current, source in enumerate(file_list, start=1):
        if progress_cb:
            progress_cb({
                "stage": "start",
                "current": current,
                "total": total,
                "file_name": source.name,
                "file": str(source),
            })
        parsed_blocks, item = parse_file(source)
        if item.get("parser_status") == "ocr_required":
            ocr_blocks = _ocr_blocks_for_file(source, item, ocr_max_pages=ocr_max_pages)
            if ocr_blocks:
                parsed_blocks = ocr_blocks
        blocks.extend(parsed_blocks)
        manifest.append(item)
        if progress_cb:
            progress_cb({
                "stage": "done",
                "current": current,
                "total": total,
                "file_name": source.name,
                "file": str(source),
                "parser_status": item.get("parser_status"),
                "ocr_status": item.get("ocr_status"),
            })

    entities = detect_entities_with_dictionary(
        (block["text"] for block in blocks),
        customer_dictionary=customer_dictionary,
    )
    mapping = build_mapping(entities, review_decisions=review_decisions)
    redacted_blocks = []
    for idx, block in enumerate(blocks, start=1):
        redacted_blocks.append({
            "block_id": f"blk_{idx:04d}",
            "source_file": block.get("file_name"),
            "source_location": block.get("location"),
            "text": redact_text(block.get("text", ""), mapping),
            "structure": _redact_structure(block.get("structure"), mapping),
        })

    all_redacted_text = "\n".join(block["text"] for block in redacted_blocks)
    package = {
        "schema_version": "stpe_redaction_upload.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_alias_id": project_alias_id,
        "source_file_manifest": manifest,
        "redacted_text_blocks": redacted_blocks,
        "structured_facts": _structured_facts(mapping),
        "field_mappings_hash": mapping.get("mapping_hash"),
        "field_mapping_stats": public_mapping_stats(mapping),
        "redaction_policy": {
            "name": redaction_policy,
            "mode": "local_mapping_not_uploaded",
            "original_files_uploaded": False,
            "mapping_uploaded": False,
        },
        "analysis_preservation_flags": _analysis_flags(all_redacted_text, mapping),
        "review_warnings": _review_warnings(all_redacted_text, mapping, manifest),
        "redaction_impact_summary": build_redaction_impact_summary(
            entities,
            mapping,
            review_decisions,
            customer_confirmed_degradation_risk=customer_confirmed_degradation_risk,
        ),
    }
    return package, mapping


def _ocr_blocks_for_file(path: Path, manifest_item: dict[str, Any], *, ocr_max_pages: int | None = None) -> list[dict[str, Any]]:
    result = extract_text_with_ocr(path, max_pages=ocr_max_pages)
    if result.get("status") != "ok" or not str(result.get("text", "")).strip():
        manifest_item["ocr_status"] = result.get("status")
        if result.get("message"):
            manifest_item.setdefault("warnings", []).append(f"ocr_failed:{result.get('message')}")
        return []
    manifest_item["parser_status"] = "ok"
    manifest_item["ocr_status"] = "ok"
    manifest_item["ocr_engine"] = result.get("engine")
    manifest_item["ocr_confidence"] = result.get("confidence")
    manifest_item["ocr_pages_processed"] = result.get("pages_processed")
    manifest_item.setdefault("warnings", []).append("ocr_applied")
    return [{
        "location": "pdf:ocr",
        "text": str(result.get("text", "")).strip(),
        "file_name": path.name,
        "structure": {
            "kind": "ocr_text",
            "engine": result.get("engine"),
            "confidence": result.get("confidence"),
            "pages_processed": result.get("pages_processed"),
        },
    }]


def write_package(
    output_dir: Path | str,
    package: dict[str, Any],
    mapping: dict[str, Any],
    *,
    mapping_passphrase: str | None = None,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    package_path = output / "redaction_upload_package.json"
    mapping_path = output / "local_mapping.private.json"
    report_path = output / "redaction_review_report.md"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_review_report(package), encoding="utf-8")
    outputs = {
        "package": package_path,
        "review_report": report_path,
    }
    if mapping_passphrase:
        outputs["encrypted_mapping"] = encrypt_mapping_file(
            mapping_path,
            output / "local_mapping.private.enc",
            passphrase=mapping_passphrase,
        )
    else:
        outputs["mapping"] = mapping_path
    return outputs


def build_restore_preview(package: dict[str, Any], mapping: dict[str, Any], limit: int = 600) -> dict[str, str]:
    redacted_text = "\n".join(
        block.get("text", "") for block in package.get("redacted_text_blocks", [])
    )[:limit]
    return {
        "redacted_preview": redacted_text,
        "restored_preview": restore_text(redacted_text, mapping),
    }


def build_review_report(package: dict[str, Any]) -> str:
    stats = package.get("field_mapping_stats", {})
    flags = package.get("analysis_preservation_flags", {})
    warnings = package.get("review_warnings", [])
    impact = package.get("redaction_impact_summary", {})
    lines = [
        "# 文档安全脱敏检查报告",
        "",
        f"- 项目代号: {package.get('project_alias_id')}",
        f"- 脱敏策略: {package.get('redaction_policy', {}).get('name')}",
        f"- 识别字段数: {stats.get('total_fields', 0)}",
        f"- 映射表上传: {package.get('redaction_policy', {}).get('mapping_uploaded')}",
        f"- 原始文件上传: {package.get('redaction_policy', {}).get('original_files_uploaded')}",
        f"- TRL 因子保留: {flags.get('trl_factors_preserved')}",
        f"- 效益因子保留: {flags.get('benefit_factors_preserved')}",
        f"- 评价影响门禁: {impact.get('overall_level')}",
        f"- 门禁提示: {impact.get('upload_gate_message')}",
        "",
        "## 字段统计",
        "",
    ]
    for kind, count in sorted((stats.get("by_kind") or {}).items()):
        lines.append(f"- {kind}: {count}")
    lines.extend(["", "## 上传前提示", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- 未发现阻断性脱敏风险。")
    lines.append("")
    return "\n".join(lines)


def _structured_facts(mapping: dict[str, Any]) -> dict[str, Any]:
    amount_ranges = []
    patent_count = 0
    for item in mapping.get("items", []):
        if item.get("kind") == "amount":
            amount_ranges.append({
                "placeholder": item.get("placeholder"),
                "range": item.get("preservation_value"),
                "strategy": "range_preserved",
            })
        if item.get("kind") == "patent_id":
            patent_count += 1
    return {
        "amount_ranges": amount_ranges,
        "patent_count": patent_count,
    }


def _redact_structure(structure: dict[str, Any] | None, mapping: dict[str, Any]) -> dict[str, Any] | None:
    if not structure:
        return None
    redacted = dict(structure)
    if isinstance(redacted.get("cells"), list):
        redacted["cells"] = [
            {
                **cell,
                "text": redact_text(str(cell.get("text", "")), mapping),
            }
            for cell in redacted["cells"]
        ]
    return redacted


def _analysis_flags(redacted_text: str, mapping: dict[str, Any]) -> dict[str, bool]:
    has_amount_range = any(item.get("kind") == "amount" and item.get("preservation_value") for item in mapping.get("items", []))
    return {
        "trl_factors_preserved": contains_technical_signal(redacted_text),
        "benefit_factors_preserved": has_amount_range,
        "stable_placeholders_used": bool(mapping.get("items")),
    }


def _review_warnings(redacted_text: str, mapping: dict[str, Any], manifest: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not contains_technical_signal(redacted_text):
        warnings.append("未识别到技术指标、验证阶段或试运行信息，TRL 判断可能降级。")
    amount_items = [item for item in mapping.get("items", []) if item.get("kind") == "amount"]
    if not amount_items:
        warnings.append("未识别到金额或效益数值，经济效益分析可能缺少可计算依据。")
    elif not any(item.get("preservation_value") for item in amount_items):
        warnings.append("金额字段未保留区间或比例，经济效益分析可能降级。")
    failed = [item["file_name"] for item in manifest if item.get("parser_status") != "ok"]
    if failed:
        warnings.append("以下文件未完成稳定解析: " + "、".join(failed))
    return warnings

from __future__ import annotations

import json
from pathlib import Path


def build_rules_assets(output_dir: Path | str, *, version: str) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    rules_manifest = {
        "schema_version": "document_redaction_rules_manifest.v1",
        "version": version,
        "strategy": "assessment_preserving_redaction",
        "field_groups": [
            {"name": "identity", "default_action": "pseudonym", "examples": ["项目名称", "单位名称", "合同编号"]},
            {"name": "amount", "default_action": "range", "examples": ["合同金额", "投资金额"]},
            {"name": "technical_metric", "default_action": "keep", "examples": ["电压等级", "误差", "试运行时间"]},
            {"name": "intellectual_property", "default_action": "mask", "examples": ["专利号", "软著登记号"]},
        ],
        "guardrails": [
            "本地映射表不得上传",
            "金额字段不默认清空",
            "技术指标和验证阶段默认保留",
            "扫描件需 OCR 或人工复核后再进入正式上传包",
        ],
    }
    ocr_manifest = {
        "schema_version": "document_redaction_ocr_plugin_manifest.v1",
        "version": version,
        "required": False,
        "supported_engines": ["rapidocr", "paddleocr", "custom"],
        "recommended_first_engine": "rapidocr",
        "plugin_contract": {
            "environment_variable": "DRA_OCR_ENGINE",
            "extract_result_fields": ["status", "engine", "text", "confidence"],
        },
        "boundary": [
            "OCR 只在客户本地执行",
            "未配置 OCR 时不影响 DOCX、XLSX、文本型 PDF 和 TXT",
            "OCR 低置信结果必须进入人工复核",
        ],
    }
    rules_path = root / "rules_manifest.json"
    ocr_path = root / "ocr_plugin_manifest.json"
    update_manifest = {
        "schema_version": "document_redaction_rules_update_manifest.v1",
        "version": version,
        "update_mode": "offline_manifest_replace",
        "compatible_rule_schema": "document_redaction_rules_manifest.v1",
        "allowed_changes": [
            "新增字段识别规则",
            "新增客户词库模板",
            "调整提示文案",
            "新增 OCR 复核阈值说明",
        ],
        "blocked_changes": [
            "删除本地映射表不得上传约束",
            "将金额默认策略改为清空",
            "将技术指标默认策略改为强脱敏",
        ],
    }
    update_path = root / "rules_update_manifest.json"
    rules_path.write_text(json.dumps(rules_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ocr_path.write_text(json.dumps(ocr_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    update_path.write_text(json.dumps(update_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"rules_manifest": rules_path, "ocr_plugin_manifest": ocr_path, "rules_update_manifest": update_path}

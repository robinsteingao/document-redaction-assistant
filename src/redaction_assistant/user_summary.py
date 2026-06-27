from __future__ import annotations

from typing import Any


def _path_record(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {"path": str(value.get("path") or ""), "reason": str(value.get("reason") or "")}
    return {"path": str(value), "reason": ""}


def build_input_plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    counts = {
        "可直接处理": int(plan.get("processable_count") or 0),
        "需先转换": int(plan.get("convertible_count") or 0),
        "暂不支持": int(plan.get("unsupported_count") or 0),
        "跳过文件": int(plan.get("skipped_count") or 0),
        "路径不存在": int(plan.get("missing_count") or 0),
    }
    groups = {
        "可直接处理": [_path_record(path) for path in plan.get("processable_files") or []],
        "需先转换": [_path_record(item) for item in plan.get("convertible_files") or []],
        "暂不支持": [_path_record(item) for item in plan.get("unsupported_files") or []],
        "跳过文件": [_path_record(item) for item in plan.get("skipped_files") or []],
        "路径不存在": [_path_record(path) for path in plan.get("missing_paths") or []],
    }
    next_actions: list[str] = []
    if counts["可直接处理"]:
        next_actions.append("可直接处理文件已就绪，可点击开始生成脱敏结果包。")
    if counts["需先转换"]:
        next_actions.append("旧版 Office/WPS 文件会先尝试本地转换；转换失败文件不会进入结果包。")
    if counts["暂不支持"]:
        next_actions.append("暂不支持文件不会进入结果包，请转换为 DOCX/XLSX/PDF/TXT 后重试。")
    if counts["路径不存在"]:
        next_actions.append("存在路径不存在，请检查路径是否复制完整。")
    if not next_actions:
        next_actions.append("未发现可处理文件，请重新选择文件或文件夹。")
    blocked = counts["可直接处理"] == 0 and counts["需先转换"] == 0
    return {
        "schema_version": "document_redaction_input_plan_summary.v1",
        "status": "blocked_no_inputs" if blocked else "ready_with_warnings" if any(counts[k] for k in ["需先转换", "暂不支持", "跳过文件", "路径不存在"]) else "ready",
        "counts": counts,
        "recommended_ocr_modes": list(plan.get("recommended_ocr_modes") or []),
        "groups": groups,
        "next_actions": next_actions,
    }


def build_batch_job_summary(job: dict[str, Any]) -> dict[str, str]:
    status_map = {"queued": "排队中", "running": "处理中", "completed": "已完成", "failed": "失败", "cancelled": "已取消"}
    progress = job.get("progress") or {}
    outputs = job.get("outputs") or {}
    conversion = job.get("conversion_report") or {}
    converted = conversion.get("converted_count", 0)
    failed = conversion.get("failed_count", 0)
    return {
        "状态": status_map.get(str(job.get("status") or ""), str(job.get("status") or "未知")),
        "进度": f"{progress.get('current') or 0}/{progress.get('total') or 0}",
        "当前文件": str(progress.get("file_name") or "暂无"),
        "输出目录": str(outputs.get("output_dir") or "完成后显示"),
        "转换结果": f"成功转换 {converted} 个，失败 {failed} 个",
        "错误提示": str(job.get("error") or "无"),
    }

from __future__ import annotations

from typing import Any

from .user_summary import build_batch_job_summary, build_input_plan_summary


def _safe_plan_summary(plan: dict[str, Any] | None) -> dict[str, Any]:
    summary = build_input_plan_summary(plan or {})
    groups = summary.get("groups") or {}
    summary["groups"] = {name: len(items or []) for name, items in groups.items()}
    return summary


def _safe_job_metadata(job: dict[str, Any] | None) -> dict[str, Any]:
    job = job or {}
    progress = job.get("progress") or {}
    outputs = job.get("outputs") or {}
    conversion = job.get("conversion_report") or {}
    return {
        "job_id": str(job.get("job_id") or ""),
        "status": str(job.get("status") or ""),
        "progress": {
            "stage": progress.get("stage"),
            "current": progress.get("current"),
            "total": progress.get("total"),
        },
        "output_keys": sorted(str(key) for key in outputs.keys()),
        "conversion": {
            "converted_count": conversion.get("converted_count", 0),
            "failed_count": conversion.get("failed_count", 0),
        },
    }


def _safe_job_for_summary(job: dict[str, Any] | None) -> dict[str, Any]:
    job = job or {}
    progress = job.get("progress") or {}
    conversion = job.get("conversion_report") or {}
    return {
        "status": job.get("status"),
        "progress": {
            "current": progress.get("current"),
            "total": progress.get("total"),
        },
        "outputs": {},
        "conversion_report": {
            "converted_count": conversion.get("converted_count", 0),
            "failed_count": conversion.get("failed_count", 0),
        },
        "error": _safe_error_summary(job.get("error")),
    }


def _safe_error_summary(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    head = text.split(":", 1)[0].strip()
    if head and head.replace("_", "").replace(".", "").isalnum() and len(head) <= 80:
        return f"{head}: 详细错误已隐藏，请结合界面截图和本地日志定位。"
    return "错误详情已隐藏，请结合界面截图和本地日志定位。"


def build_support_bundle(plan: dict[str, Any] | None, job: dict[str, Any] | None, *, version: str = "M24.2") -> dict[str, Any]:
    """Build a support diagnostic payload without source text or private mappings."""
    return {
        "schema_version": "document_redaction_support_bundle.v1",
        "version": version,
        "privacy_note": "技术支持包仅包含计数、状态和错误摘要；不包含原文、映射表或文件内容。",
        "input_plan_summary": _safe_plan_summary(plan),
        "job_summary": build_batch_job_summary(_safe_job_for_summary(job)),
        "job_metadata": _safe_job_metadata(job),
    }

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .workflow import restore_text


def build_report_delivery_package(
    evaluation_result: dict[str, Any],
    mapping_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8-sig"))
    report_text = _build_redacted_report(evaluation_result)
    redacted_report = output / "redacted_evaluation_report.md"
    restored_preview = output / "local_restored_report_preview.md"
    manifest = output / "report_delivery_manifest.json"
    redacted_report.write_text(report_text, encoding="utf-8")
    restored_preview.write_text(restore_text(report_text, mapping), encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "document_redaction_report_delivery.v1",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "project_alias_id": evaluation_result.get("project_alias_id"),
                "redacted_report": redacted_report.name,
                "restored_preview": restored_preview.name,
                "contains_local_mapping": False,
                "contains_original_files": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"redacted_report": redacted_report, "restored_preview": restored_preview, "manifest": manifest}


def _build_redacted_report(evaluation_result: dict[str, Any]) -> str:
    title = evaluation_result.get("report_title") or f"{evaluation_result.get('project_alias_id')} 后评估报告"
    summary = evaluation_result.get("summary") or "暂无评估摘要。"
    recommendations = evaluation_result.get("recommendations") or []
    lines = [
        f"# {title}",
        "",
        "## 评估摘要",
        "",
        str(summary),
        "",
        "## 推进建议",
        "",
    ]
    if recommendations:
        lines.extend(f"- {item}" for item in recommendations)
    else:
        lines.append("- 暂无专项建议。")
    lines.append("")
    return "\n".join(lines)

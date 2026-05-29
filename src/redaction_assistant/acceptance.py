from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .commercial_package import validate_commercial_install_package
from .ocr_adapter import get_ocr_status
from .workflow import build_redaction_package, write_package


def run_acceptance_smoke(
    app_dir: Path | str,
    *,
    output_dir: Path | str | None = None,
    project_alias_id: str = "acceptance-smoke",
) -> dict[str, Any]:
    app = Path(app_dir)
    if not app.is_absolute():
        app = Path(os.getcwd()) / app
    app = app.resolve()
    package_root = app.parent
    output = Path(output_dir) if output_dir else package_root / "generated" / "acceptance_smoke"
    output.mkdir(parents=True, exist_ok=True)
    sample_files = _sample_files(package_root, output)
    package, mapping = build_redaction_package(sample_files, project_alias_id=project_alias_id)
    outputs = write_package(output, package, mapping)
    report = _build_report(app, package, mapping, outputs)
    report_path = output / "acceptance_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = output / "ACCEPTANCE_REPORT.md"
    markdown_path.write_text(_report_markdown(report), encoding="utf-8")
    return report


def _sample_files(package_root: Path, output: Path) -> list[Path]:
    sample_root = package_root / "sample_data"
    found = sorted(path for path in sample_root.rglob("*") if path.is_file() and path.suffix.lower() in {".txt", ".md", ".docx", ".xlsx", ".pdf"})
    if found:
        return found
    fallback = output / "acceptance_sample.txt"
    fallback.write_text(
        "项目名称：配网智能监测项目。合同金额：120万元。技术指标：10kV试运行30天。",
        encoding="utf-8",
    )
    return [fallback]


def _build_report(app_dir: Path, package: dict[str, Any], mapping: dict[str, Any], outputs: dict[str, Path]) -> dict[str, Any]:
    redaction_policy = package.get("redaction_policy", {})
    blocks = package.get("redacted_text_blocks", [])
    stats = package.get("field_mapping_stats", {})
    redaction_passed = (
        bool(blocks)
        and redaction_policy.get("original_files_uploaded") is False
        and redaction_policy.get("mapping_uploaded") is False
        and Path(outputs["package"]).exists()
        and Path(outputs["mapping"]).exists()
    )
    checks = {
        "commercial_package": _commercial_package_check(app_dir.parent),
        "runtime_files": {
            "passed": (app_dir / "run_cli.bat").exists() and (app_dir / "src" / "redaction_assistant" / "cli.py").exists(),
            "run_cli": str(app_dir / "run_cli.bat"),
            "cli_module": str(app_dir / "src" / "redaction_assistant" / "cli.py"),
        },
        "ocr_status": {
            "passed": get_ocr_status().get("status") in {"available", "not_configured"},
            "result": get_ocr_status(),
        },
        "redaction_package": {
            "passed": redaction_passed,
            "package": str(outputs["package"]),
            "mapping": str(outputs["mapping"]),
            "source_file_count": len(package.get("source_file_manifest", [])),
            "block_count": len(blocks),
            "mapping_count": len(mapping.get("items", [])),
            "field_count": stats.get("total_fields", 0),
            "original_files_uploaded": redaction_policy.get("original_files_uploaded"),
            "mapping_uploaded": redaction_policy.get("mapping_uploaded"),
        },
    }
    status = "passed" if all(item["passed"] for item in checks.values()) else "failed"
    return {
        "schema_version": "document_redaction_acceptance_report.v1",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "checks": checks,
    }


def _commercial_package_check(package_root: Path) -> dict[str, Any]:
    manifest = package_root / "commercial_release_manifest.json"
    if not manifest.exists():
        return {
            "passed": True,
            "skipped": True,
            "reason": "not_a_commercial_package",
        }
    result = validate_commercial_install_package(package_root)
    return {
        "passed": result.get("status") == "valid",
        "skipped": False,
        "result": result,
    }


def _report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 文档安全脱敏助手验收自检报告",
        "",
        f"- 状态: {report.get('status')}",
        f"- 时间: {report.get('created_at')}",
        "",
        "## 检查项",
        "",
    ]
    for name, item in report.get("checks", {}).items():
        lines.append(f"- {name}: {'passed' if item.get('passed') else 'failed'}")
    lines.append("")
    return "\n".join(lines)

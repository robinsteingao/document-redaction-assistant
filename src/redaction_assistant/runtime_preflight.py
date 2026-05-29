from __future__ import annotations

import importlib.util
import json
import platform
import sys
from pathlib import Path
from typing import Any

from .ocr_adapter import get_ocr_status


def run_runtime_preflight(base_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    checks: list[dict[str, Any]] = [
        _python_version_check(),
        _source_import_check(),
        _write_permission_check(root),
        _ocr_adapter_check(),
        _rules_manifest_check(root),
    ]
    failed = any(check["status"] == "failed" for check in checks)
    warnings = any(check["status"] == "warning" for check in checks)
    overall = "failed" if failed else "warning" if warnings else "ready"
    return {
        "schema_version": "document_redaction_runtime_preflight.v1",
        "overall_status": overall,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "base_dir": str(root),
        "checks": checks,
        "ocr": get_ocr_status(),
    }


def write_runtime_preflight_report(output: Path | str, base_dir: Path | str | None = None) -> Path:
    report = run_runtime_preflight(base_dir)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _python_version_check() -> dict[str, Any]:
    ok = sys.version_info >= (3, 10)
    return {
        "name": "python_version",
        "status": "ready" if ok else "failed",
        "message": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


def _source_import_check() -> dict[str, Any]:
    available = importlib.util.find_spec("redaction_assistant.cli") is not None
    return {
        "name": "source_package_import",
        "status": "ready" if available else "failed",
        "message": "本地源码包可导入。" if available else "无法导入 redaction_assistant.cli。",
    }


def _write_permission_check(root: Path) -> dict[str, Any]:
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".runtime_preflight_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return {"name": "write_permission", "status": "ready", "message": "当前目录可写。"}
    except OSError as exc:
        return {"name": "write_permission", "status": "failed", "message": str(exc)}


def _ocr_adapter_check() -> dict[str, Any]:
    status = get_ocr_status()
    ready = status["status"] == "available"
    return {
        "name": "ocr_adapter",
        "status": "ready" if ready else "warning",
        "message": status.get("message", ""),
    }


def _rules_manifest_check(root: Path) -> dict[str, Any]:
    candidates = [
        root / "app" / "rules" / "rules_manifest.json",
        root / "rules" / "rules_manifest.json",
        root / "rules_manifest.json",
    ]
    exists = any(path.exists() for path in candidates)
    return {
        "name": "rules_manifest",
        "status": "ready" if exists else "warning",
        "message": "规则包清单存在。" if exists else "未发现规则包清单；源码测试目录可忽略，安装包目录需包含。",
    }

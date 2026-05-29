from __future__ import annotations

import hashlib
import json
from pathlib import Path


def build_offline_ocr_install_plan(app_dir: Path | str, *, engine: str = "paddleocr") -> dict[str, Path]:
    root = Path(app_dir)
    ocr_dir = root / "ocr_engines"
    wheelhouse = ocr_dir / "wheelhouse"
    runtime_python = root / "runtime" / "python" / "python.exe"
    files = [_file_record(path, wheelhouse) for path in sorted(wheelhouse.glob("*")) if path.is_file()] if wheelhouse.exists() else []
    wheels = [item for item in files if item["name"].lower().endswith((".whl", ".zip", ".tar.gz"))]
    models = [item for item in files if item["name"].lower().endswith(".tar") and "infer" in item["name"].lower()]
    if engine == "rapidocr":
        install_target = "rapidocr-onnxruntime pypdfium2"
    else:
        install_target = "paddleocr paddlepaddle"
    install_commands = [
        rf'".\runtime\python\python.exe" -m pip install --no-index --no-build-isolation --find-links ".\ocr_engines\wheelhouse" {install_target}'
    ]
    plan = {
        "schema_version": "document_redaction_offline_ocr_install_plan.v1",
        "engine": engine,
        "python": "app/runtime/python/python.exe",
        "wheelhouse": "app/ocr_engines/wheelhouse",
        "runtime_python_exists": runtime_python.exists(),
        "dependency_files": wheels,
        "model_files": models,
        "install_commands": install_commands,
        "post_install_validation": "app\\validate_offline_ocr.bat",
    }
    plan_path = ocr_dir / "offline_ocr_install_plan.json"
    env_path = ocr_dir / "offline_ocr_env.bat"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    env_path.write_text(_env_bat(engine), encoding="utf-8")
    return {"plan": plan_path, "env": env_path}


def validate_offline_ocr_enablement(app_dir: Path | str) -> dict:
    root = Path(app_dir)
    issues = []
    plan_path = root / "ocr_engines" / "offline_ocr_install_plan.json"
    env_path = root / "ocr_engines" / "offline_ocr_env.bat"
    marker_path = root / "ocr_engines" / "offline_ocr_installed.marker.json"
    if not plan_path.exists():
        issues.append({"component": "offline_ocr", "reason": "missing_install_plan"})
    if not env_path.exists():
        issues.append({"component": "offline_ocr", "reason": "missing_env_config"})
    if not marker_path.exists():
        issues.append({"component": "offline_ocr", "reason": "missing_install_marker"})
    if marker_path.exists():
        marker = json.loads(marker_path.read_text(encoding="utf-8-sig"))
        if marker.get("status") != "installed":
            issues.append({"component": "offline_ocr", "reason": "install_marker_not_installed"})
    return {
        "schema_version": "document_redaction_offline_ocr_validation.v1",
        "status": "enabled" if not issues else "not_enabled",
        "app_dir": str(root),
        "issues": issues,
    }


def write_offline_ocr_install_marker(app_dir: Path | str, *, engine: str = "paddleocr") -> Path:
    root = Path(app_dir)
    marker = {
        "schema_version": "document_redaction_offline_ocr_install_marker.v1",
        "status": "installed",
        "engine": engine,
    }
    path = root / "ocr_engines" / "offline_ocr_installed.marker.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _file_record(path: Path, root: Path) -> dict:
    return {
        "name": path.name,
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
    }


def _env_bat(engine: str) -> str:
    return f"""@echo off
set "DRA_OCR_ENGINE={engine}"
set "DRA_OCR_MODELS=%~dp0wheelhouse"
echo DRA_OCR_ENGINE={engine}
"""

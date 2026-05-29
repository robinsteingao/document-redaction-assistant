from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path


def build_runtime_assets(output_dir: Path | str, *, version: str) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    runtime_manifest = {
        "schema_version": "document_redaction_runtime_bundle_manifest.v1",
        "version": version,
        "bundled_python": False,
        "embedded_python_launcher": "run_with_embedded_python.bat",
        "min_python": "3.10",
        "runtime_mode": "external_or_future_embedded_python",
        "required_stdlib": ["json", "pathlib", "zipfile", "http.server", "sqlite3"],
        "future_bundle_slots": [
            "python_runtime",
            "ocr_runtime",
            "office_conversion_runtime",
        ],
        "boundary": [
            "M9 不内置 Python 运行时",
            "安装预检负责发现客户电脑 Python 可用性",
            "后续正式离线包可将 bundled_python 切换为 true",
        ],
    }
    runtime_path = root / "runtime_manifest.json"
    runtime_path.write_text(json.dumps(runtime_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    launcher = root / "run_with_embedded_python.bat"
    launcher.write_text(_embedded_python_launcher(), encoding="utf-8")
    python_dir = root / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    runtime_readme = python_dir / "README_RUNTIME.txt"
    runtime_readme.write_text(
        "Place embedded Python runtime files in this directory for the formal offline package.\n",
        encoding="utf-8",
    )
    files_manifest = _write_files_manifest(
        root / "runtime_files_manifest.json",
        root,
        "document_redaction_runtime_files_manifest.v1",
        [runtime_path, launcher, runtime_readme],
    )
    return {"runtime_manifest": runtime_path, "embedded_python_launcher": launcher, "runtime_files_manifest": files_manifest}


def build_ocr_engine_assets(output_dir: Path | str, *, version: str) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "document_redaction_ocr_engine_bundle_manifest.v1",
        "version": version,
        "bundled_engine": False,
        "supported_engines": ["rapidocr", "paddleocr", "custom"],
        "preferred_engine": "rapidocr",
        "expected_model_size": "not_bundled_in_m9",
        "install_boundary": [
            "OCR 引擎包必须本地执行",
            "OCR 结果低置信时进入人工复核",
            "未安装 OCR 引擎不影响非扫描件处理",
        ],
    }
    path = root / "ocr_engine_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    setup = root / "OCR_SETUP.md"
    setup.write_text(_ocr_setup_markdown(), encoding="utf-8")
    requirements = root / "requirements-ocr.txt"
    requirements.write_text("rapidocr-onnxruntime\npypdfium2\npaddleocr\n", encoding="utf-8")
    files_manifest = _write_files_manifest(
        root / "ocr_files_manifest.json",
        root,
        "document_redaction_ocr_files_manifest.v1",
        [path, setup, requirements],
    )
    return {"ocr_engine_manifest": path, "ocr_setup": setup, "ocr_requirements": requirements, "ocr_files_manifest": files_manifest}


def stage_python_runtime(source_python: Path | str, output_dir: Path | str, *, version: str) -> dict[str, Path]:
    root = Path(output_dir)
    python_dir = root / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    source = Path(source_python)
    target = python_dir / "python.exe"
    shutil.copy2(source, target)
    runtime_manifest = {
        "schema_version": "document_redaction_runtime_bundle_manifest.v1",
        "version": version,
        "bundled_python": True,
        "embedded_python_launcher": "run_with_embedded_python.bat",
        "min_python": "3.10",
        "runtime_mode": "embedded_python",
        "boundary": [
            "Python 运行时已落入本地 runtime/python 目录",
            "仍需由安装预检确认目标电脑可执行",
        ],
    }
    runtime_path = root / "runtime_manifest.json"
    runtime_path.write_text(json.dumps(runtime_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    launcher = root / "run_with_embedded_python.bat"
    if not launcher.exists():
        launcher.write_text(_embedded_python_launcher(), encoding="utf-8")
    files_manifest = _write_files_manifest(
        root / "runtime_files_manifest.json",
        root,
        "document_redaction_runtime_files_manifest.v1",
        [runtime_path, launcher, target],
    )
    return {"python_exe": target, "runtime_manifest": runtime_path, "runtime_files_manifest": files_manifest}


def build_ocr_wheelhouse_bundle(wheelhouse_dir: Path | str, output_dir: Path | str, *, version: str) -> dict[str, Path]:
    source_root = Path(wheelhouse_dir)
    target_root = Path(output_dir)
    target_wheelhouse = target_root / "wheelhouse"
    target_wheelhouse.mkdir(parents=True, exist_ok=True)
    files = []
    for source in sorted(source_root.iterdir()):
        if source.is_file() and source.suffix.lower() in {".whl", ".zip", ".tar", ".gz"}:
            target = target_wheelhouse / source.name
            shutil.copy2(source, target)
            files.append(target)
    manifest_path = target_root / "ocr_wheelhouse_manifest.json"
    manifest = {
        "schema_version": "document_redaction_ocr_wheelhouse_manifest.v1",
        "version": version,
        "bundled": bool(files),
        "files": [
            {
                "path": file.relative_to(target_root).as_posix(),
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "size": file.stat().st_size,
            }
            for file in files
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"wheelhouse_dir": target_wheelhouse, "ocr_wheelhouse_manifest": manifest_path}


def validate_ocr_wheelhouse_manifest(manifest_path: Path | str) -> dict:
    path = Path(manifest_path)
    root = path.parent
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    issues = []
    if manifest.get("schema_version") != "document_redaction_ocr_wheelhouse_manifest.v1":
        issues.append({"field": "schema_version", "reason": "unsupported_schema"})
    files = manifest.get("files", [])
    if not isinstance(files, list):
        issues.append({"field": "files", "reason": "must_be_list"})
        files = []
    for item in files:
        relative = item.get("path", "")
        file_path = root / relative
        if not file_path.exists():
            issues.append({"path": relative, "reason": "missing_file"})
            continue
        actual_size = file_path.stat().st_size
        actual_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_sha != item.get("sha256"):
            issues.append({"path": relative, "reason": "sha256_mismatch"})
        if actual_size != item.get("size"):
            issues.append({"path": relative, "reason": "size_mismatch"})
    return {
        "status": "valid" if not issues else "invalid",
        "manifest": str(path),
        "file_count": len(files),
        "issues": issues,
    }


def _embedded_python_launcher() -> str:
    return """@echo off
setlocal
set "APP_DIR=%~dp0..\\"
set "EMBEDDED_PY=%~dp0python\\python.exe"
if exist "%EMBEDDED_PY%" (
  set "PYTHONPATH=%APP_DIR%src"
  "%EMBEDDED_PY%" -m redaction_assistant.cli %*
  exit /b
)
echo Embedded Python runtime is not bundled in this package.
echo Falling back to app\\run_cli.bat
call "%APP_DIR%run_cli.bat" %*
"""


def _ocr_setup_markdown() -> str:
    return """# OCR 引擎包接入说明

M10 已提供真实 OCR 适配调用路径，但当前安装包不内置模型和运行库。

推荐顺序:

1. 优先接入 RapidOCR，环境变量设置为 `DRA_OCR_ENGINE=rapidocr`。
2. 如需 PaddleOCR，环境变量设置为 `DRA_OCR_ENGINE=paddleocr`。
3. OCR 仅在客户本地执行，低置信结果进入人工复核。
4. 未安装 OCR 时，DOCX、XLSX、文本型 PDF 和 TXT 不受影响。
"""


def _write_files_manifest(path: Path, root: Path, schema_version: str, files: list[Path]) -> Path:
    manifest = {
        "schema_version": schema_version,
        "files": [
            {
                "path": file.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "size": file.stat().st_size,
            }
            for file in files
        ],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

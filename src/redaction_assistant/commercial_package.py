from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .install_package import build_install_package
from .offline_ocr_install import build_offline_ocr_install_plan
from .offline_runtime import build_ocr_wheelhouse_bundle


def build_commercial_install_package(
    output_root: Path | str,
    *,
    version: str,
    python_runtime_dir: Path | str | None = None,
    ocr_wheelhouse_dir: Path | str | None = None,
    office_runtime_dir: Path | str | None = None,
    service_url: str = "http://127.0.0.1:8765",
) -> dict[str, Path]:
    result = build_install_package(output_root, version=version, service_url=service_url)
    package_dir = result["package_dir"]
    app_dir = package_dir / "app"

    component_status = {
        "embedded_python": _stage_python_dir(python_runtime_dir, app_dir / "runtime", version),
        "ocr_wheelhouse": _stage_ocr_wheelhouse(ocr_wheelhouse_dir, app_dir / "ocr_engines", version),
        "office_converter": _stage_office_runtime(office_runtime_dir, app_dir / "office_runtime", version),
    }
    offline_status = "complete_offline" if all(item["status"] == "bundled" for item in component_status.values()) else "staging_required"
    _write_commercial_scripts(app_dir)
    build_offline_ocr_install_plan(app_dir, engine="rapidocr")
    _copy_blind_test_quick_start(package_dir)
    _write_runtime_ready_start_here(package_dir, version, offline_status)
    _write_commercial_manifest(package_dir, version, offline_status, component_status)
    _patch_install_manifest(package_dir / "install_manifest.json", offline_status)
    archive = _zip_package(package_dir)
    return {"package_dir": package_dir, "archive": archive}


def validate_commercial_install_package(package_dir: Path | str) -> dict:
    root = Path(package_dir)
    issues = []
    python_exe = root / "app" / "runtime" / "python" / "python.exe"
    ocr_manifest = root / "app" / "ocr_engines" / "ocr_wheelhouse_manifest.json"
    office_manifest = root / "app" / "office_runtime" / "office_runtime_manifest.json"
    if not python_exe.exists():
        issues.append({"component": "embedded_python", "reason": "missing_embedded_python"})
    if not ocr_manifest.exists() or not _manifest_has_files(ocr_manifest):
        issues.append({"component": "ocr_wheelhouse", "reason": "missing_ocr_wheelhouse"})
    if not office_manifest.exists() or not _office_manifest_has_converter(office_manifest):
        issues.append({"component": "office_converter", "reason": "missing_office_converter"})
    return {
        "schema_version": "document_redaction_commercial_validation.v1",
        "status": "valid" if not issues else "invalid",
        "package_dir": str(root),
        "issues": issues,
    }


def _stage_python_dir(source_dir: Path | str | None, runtime_dir: Path, version: str) -> dict:
    if source_dir is None:
        return {"status": "missing", "required": True, "path": "app/runtime/python"}
    source = Path(source_dir)
    python_exe = source / "python.exe"
    if not python_exe.exists():
        return {"status": "missing", "required": True, "path": str(source), "reason": "python.exe_not_found"}
    target = runtime_dir / "python"
    if target.exists():
        shutil.rmtree(target)
    _copy_python_runtime(source, target)
    _write_runtime_manifest(runtime_dir, version)
    return {"status": "bundled", "required": True, "path": "app/runtime/python", "file_count": _file_count(target)}


def _stage_ocr_wheelhouse(source_dir: Path | str | None, target_dir: Path, version: str) -> dict:
    if source_dir is None:
        return {"status": "missing", "required": True, "path": "app/ocr_engines/wheelhouse"}
    result = build_ocr_wheelhouse_bundle(source_dir, target_dir, version=version)
    manifest = json.loads(result["ocr_wheelhouse_manifest"].read_text(encoding="utf-8"))
    if not manifest.get("files"):
        return {"status": "missing", "required": True, "path": str(source_dir), "reason": "no_dependency_files"}
    return {"status": "bundled", "required": True, "path": "app/ocr_engines/wheelhouse", "file_count": len(manifest["files"])}


def _stage_office_runtime(source_dir: Path | str | None, target_dir: Path, version: str) -> dict:
    target_dir.mkdir(parents=True, exist_ok=True)
    if source_dir is None:
        manifest = _office_manifest(version, bundled=False, files=[], converter=None)
        _write_json(target_dir / "office_runtime_manifest.json", manifest)
        return {"status": "missing", "required": True, "path": "app/office_runtime"}
    source = Path(source_dir)
    source_root = _office_runtime_copy_root(source)
    converter = _find_office_converter(source_root)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_root, target_dir, ignore=_ignore_cache)
    files = [_file_record(path, target_dir) for path in sorted(target_dir.rglob("*")) if path.is_file()]
    target_converter = _find_office_converter(target_dir)
    converter_name = target_converter.relative_to(target_dir).as_posix() if target_converter else None
    manifest = _office_manifest(version, bundled=target_converter is not None, files=files, converter=converter_name)
    _write_json(target_dir / "office_runtime_manifest.json", manifest)
    if converter is None:
        return {"status": "missing", "required": True, "path": str(source), "reason": "soffice_or_wps_not_found"}
    return {"status": "bundled", "required": True, "path": "app/office_runtime", "file_count": len(files)}


def _office_runtime_copy_root(source: Path) -> Path:
    if source.name.lower() == "program" and (source.parent / "share").exists():
        return source.parent
    return source


def _write_commercial_scripts(app_dir: Path) -> None:
    (app_dir / "validate_commercial_package.bat").write_text(
        """@echo off
setlocal
cd /d "%~dp0"
call run_cli.bat validate-commercial-package --package-dir ".."
exit /b
""",
        encoding="utf-8",
    )
    (app_dir / "start_offline_app.bat").write_text(
        """@echo off
setlocal
cd /d "%~dp0"
call validate_commercial_package.bat
if errorlevel 1 exit /b 1
call run_cli.bat serve-local --host 127.0.0.1 --port 8765
""",
        encoding="utf-8",
    )
    (app_dir / "install_offline_ocr.bat").write_text(
        """@echo off
setlocal
cd /d "%~dp0"
if not exist ".\\runtime\\python\\python.exe" (
  echo Embedded Python runtime not found.
  exit /b 1
)
if not exist ".\\ocr_engines\\wheelhouse" (
  echo OCR wheelhouse not found.
  exit /b 1
)
call ".\\ocr_engines\\offline_ocr_env.bat"
".\\runtime\\python\\python.exe" -m pip install --no-index --no-build-isolation --find-links ".\\ocr_engines\\wheelhouse" rapidocr-onnxruntime pypdfium2
if errorlevel 1 exit /b 1
call run_cli.bat mark-offline-ocr-installed --app-dir "."
exit /b
""",
        encoding="utf-8",
    )
    (app_dir / "validate_offline_ocr.bat").write_text(
        """@echo off
setlocal
cd /d "%~dp0"
call run_cli.bat validate-offline-ocr --app-dir "."
exit /b
""",
        encoding="utf-8",
    )


def _copy_blind_test_quick_start(package_dir: Path) -> None:
    source_root = Path(__file__).resolve().parents[2]
    source = source_root / "docs" / "BLIND_TEST_QUICK_START.md"
    if source.exists():
        shutil.copy2(source, package_dir / "BLIND_TEST_QUICK_START.md")


def _write_runtime_ready_start_here(package_dir: Path, version: str, offline_status: str) -> None:
    package_dir.joinpath("START_HERE.md").write_text(
        f"""# 文档安全脱敏助手 runtime-ready 盲测包

版本: {version}
离线状态: {offline_status}

**盲测人员请优先阅读 `BLIND_TEST_QUICK_START.md`**，该文件是单一上手入口。

验收顺序:

1. 解压到短路径（如 `D:\\DRA`），不要解压到深层中文目录或网络盘。
2. 首次运行 `app\\install_offline_ocr.bat` 安装 OCR 引擎依赖（约 2 分钟，仅首次需要）。
3. 运行 `app\\validate_offline_ocr.bat` 确认 OCR 已启用。
4. 双击 `app\\start_desktop_app.bat`，由脚本启动本地服务并打开产品页面。
5. 如需安装预检，运行 `app\\install_local.bat`。
6. 运行 `app\\run_sample_self_test.bat`，期望输出 `SAMPLE_SELF_TEST_OK`。
7. 如需执行完整验收自检，运行 `app\\run_acceptance_smoke.bat`。

边界:

- 当前是可解压运行的完整离线 runtime-ready 盲测包，不是正式 MSI/EXE 安装器。
- Python 运行时已内置在 `app\\runtime\\python\\`，客户电脑无需另行安装 Python。
- OCR 引擎依赖已内置在 `app\\ocr_engines\\wheelhouse\\`，需运行 `app\\install_offline_ocr.bat` 安装后启用。
- Office/旧版文档转换组件已内置在 `app\\office_runtime\\`。
- 本地映射表以 local_mapping.private.enc 加密保存在客户本机，不进入上传包。
- `commercial_release_manifest.json` 和 `install_manifest.json` 是组件完整性审计入口。
""",
        encoding="utf-8",
    )


def _write_commercial_manifest(package_dir: Path, version: str, offline_status: str, component_status: dict) -> None:
    manifest = {
        "schema_version": "document_redaction_commercial_release_manifest.v1",
        "version": version,
        "package_goal": "complete_offline_commercial_package",
        "offline_status": offline_status,
        "components": component_status,
        "security_boundary": [
            "全部文档解析、OCR 和脱敏处理在客户本地执行",
            "本地加密映射表不进入上传包",
            "生产沙箱只接收脱敏上传包",
        ],
    }
    _write_json(package_dir / "commercial_release_manifest.json", manifest)


def _patch_install_manifest(path: Path, offline_status: str) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["package_type"] = "complete_offline_commercial_package" if offline_status == "complete_offline" else "commercial_staging_package"
    manifest["offline_status"] = offline_status
    manifest["runtime_mode"] = "embedded_python_first"
    manifest["commands"]["commercial_validation"] = "app\\validate_commercial_package.bat"
    manifest["commands"]["offline_app"] = "app\\start_offline_app.bat"
    manifest["commands"]["offline_ocr_install"] = "app\\install_offline_ocr.bat"
    manifest["commands"]["offline_ocr_validation"] = "app\\validate_offline_ocr.bat"
    for capability in [
        "commercial_package_validation",
        "complete_offline_commercial_package",
        "offline_ocr_enablement",
        "embedded_runtime_preferred",
    ]:
        if capability not in manifest["capabilities"]:
            manifest["capabilities"].append(capability)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _manifest_has_files(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return bool(data.get("files"))


def _office_manifest_has_converter(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data.get("bundled") is True and bool(data.get("converter"))


def _office_manifest(version: str, *, bundled: bool, files: list[dict], converter: str | None) -> dict:
    return {
        "schema_version": "document_redaction_office_runtime_manifest.v1",
        "version": version,
        "bundled": bundled,
        "converter": converter,
        "supported_inputs": ["doc", "docx", "xls", "xlsx", "ppt", "pptx", "wps", "pdf"],
        "files": files,
    }


def _write_runtime_manifest(runtime_dir: Path, version: str) -> None:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    launcher = runtime_dir / "run_with_embedded_python.bat"
    launcher.write_text(
        """@echo off
setlocal
set "APP_DIR=%~dp0..\\"
set "EMBEDDED_PY=%~dp0python\\python.exe"
set "PYTHONPATH=%APP_DIR%src"
if exist "%APP_DIR%ocr_engines\\offline_ocr_installed.marker.json" (
  if exist "%APP_DIR%ocr_engines\\offline_ocr_env.bat" (
    call "%APP_DIR%ocr_engines\\offline_ocr_env.bat" >nul
  )
)
"%EMBEDDED_PY%" -m redaction_assistant.cli %*
""",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "document_redaction_runtime_bundle_manifest.v1",
        "version": version,
        "bundled_python": True,
        "embedded_python_launcher": "run_with_embedded_python.bat",
        "min_python": "3.10",
        "runtime_mode": "embedded_python",
        "boundary": [
            "Python 运行时已随商业离线包内置",
            "客户电脑无需另行安装 Python 即可启动本地服务",
        ],
    }
    _write_json(runtime_dir / "runtime_manifest.json", manifest)
    files = [_file_record(path, runtime_dir) for path in sorted(runtime_dir.rglob("*")) if path.is_file()]
    _write_json(
        runtime_dir / "runtime_files_manifest.json",
        {"schema_version": "document_redaction_runtime_files_manifest.v1", "files": files},
    )


def _find_office_converter(root: Path) -> Path | None:
    for name in ("soffice.exe", "wps.exe", "et.exe", "wpp.exe"):
        found = list(root.rglob(name))
        if found:
            return found[0]
    return None


def _copy_python_runtime(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for file in source.iterdir():
        if file.is_file():
            shutil.copy2(file, target / file.name)
    for dirname in ("DLLs", "Lib", "libs", "include"):
        src_dir = source / dirname
        if src_dir.exists():
            if dirname == "Lib":
                _copy_lib_dir(src_dir, target / dirname)
            else:
                shutil.copytree(src_dir, target / dirname, ignore=_ignore_cache)
    scripts = source / "Scripts"
    if scripts.exists():
        shutil.copytree(scripts, target / "Scripts", ignore=_ignore_cache)


def _copy_lib_dir(source: Path, target: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored = _ignore_cache(_dir, names)
        if Path(_dir).name == "Lib" and "site-packages" in names:
            ignored.add("site-packages")
        return ignored

    shutil.copytree(source, target, ignore=ignore)
    site = source / "site-packages"
    target_site = target / "site-packages"
    target_site.mkdir(parents=True, exist_ok=True)
    if site.exists():
        keep_prefixes = ("pip", "setuptools", "wheel", "pkg_resources", "_distutils_hack")
        for child in site.iterdir():
            if child.name.startswith(keep_prefixes):
                destination = target_site / child.name
                if child.is_dir():
                    shutil.copytree(child, destination, ignore=_ignore_cache)
                else:
                    shutil.copy2(child, destination)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _file_record(path: Path, root: Path) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
    }


def _file_count(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file())


def _ignore_cache(_dir: str, names: list[str]) -> set[str]:
    return {name for name in names if name == "__pycache__" or name.endswith((".pyc", ".pyo"))}


def _zip_package(package_dir: Path) -> Path:
    archive = package_dir.parent / f"{package_dir.name}.zip"
    if archive.exists():
        archive.unlink()
    import zipfile

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in package_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(package_dir.parent).as_posix())
    return archive

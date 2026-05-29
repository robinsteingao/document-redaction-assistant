from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from .desktop_shell import build_desktop_shell
from .installer_assets import build_installer_assets
from .local_license import write_local_license
from .offline_runtime import build_ocr_engine_assets, build_runtime_assets
from .rules_package import build_rules_assets


def build_install_package(
    output_root: Path | str,
    *,
    version: str,
    service_url: str = "http://127.0.0.1:8765",
) -> dict[str, Path]:
    source_root = Path(__file__).resolve().parents[2]
    package_dir = Path(output_root) / f"document_redaction_assistant_install_{version}"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    app_dir = package_dir / "app"
    sample_dir = package_dir / "sample_data"
    docs_dir = package_dir / "docs"
    app_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source_root / "src", app_dir / "src", ignore=_ignore_runtime_cache)
    _copy_optional(source_root / "README.md", package_dir / "README.md")
    _copy_optional(source_root / "RELEASE_CHECKLIST.md", docs_dir / "RELEASE_CHECKLIST.md")
    if (source_root / "docs").exists():
        shutil.copytree(source_root / "docs", docs_dir / "release_notes", dirs_exist_ok=True)
    if (source_root / "examples" / "batch_demo").exists():
        shutil.copytree(source_root / "examples" / "batch_demo", sample_dir, dirs_exist_ok=True)
    elif (source_root / "examples" / "sample_project.txt").exists():
        single = sample_dir / "project_alpha"
        single.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / "examples" / "sample_project.txt", single / "input.txt")

    shell_root = build_desktop_shell(app_dir, version=version, service_url=service_url)
    final_shell = app_dir / "desktop_shell"
    if final_shell.exists():
        shutil.rmtree(final_shell)
    shell_root.rename(final_shell)

    _write(app_dir / "run_cli.bat", _run_cli_bat())
    _write(app_dir / "start_desktop_app.bat", _start_desktop_app_bat())
    _write(app_dir / "start_local_service.bat", _start_service_bat())
    _write(app_dir / "run_sample_self_test.bat", _sample_self_test_bat())
    _write(app_dir / "check_runtime.bat", _check_runtime_bat())
    _write(app_dir / "install_local.bat", _install_local_bat())
    _write(app_dir / "activate_local_license.bat", _activate_license_bat())
    _write(app_dir / "apply_rules_update.bat", _apply_rules_update_bat())
    _write(app_dir / "stage_python_runtime.bat", _stage_python_runtime_bat())
    _write(app_dir / "build_ocr_wheelhouse.bat", _build_ocr_wheelhouse_bat())
    _write(app_dir / "validate_ocr_package.bat", _validate_ocr_package_bat())
    _write(app_dir / "build_report_delivery_demo.bat", _report_delivery_demo_bat())
    _write(app_dir / "record_pilot_feedback.bat", _record_pilot_feedback_bat())
    _write(app_dir / "build_production_sandbox_config.bat", _production_sandbox_config_bat())
    _write(app_dir / "run_acceptance_smoke.bat", _acceptance_smoke_bat())
    build_rules_assets(app_dir / "rules", version=version)
    write_local_license(app_dir / "license" / "local_license.json", customer_name="本地试点客户")
    build_runtime_assets(app_dir / "runtime", version=version)
    build_ocr_engine_assets(app_dir / "ocr_engines", version=version)
    build_installer_assets(package_dir, version=version)
    _write(package_dir / "START_HERE.md", _start_here(version))
    manifest = {
        "schema_version": "document_redaction_install_manifest.v1",
        "name": "文档安全脱敏助手",
        "version": version,
        "entrypoint": "START_HERE.md",
        "package_type": "testable_install_readiness_package",
        "runtime": "Python 3.10+ or bundled-compatible Python on customer PC",
        "service_url": service_url,
        "commands": {
            "sample_self_test": "app\\run_sample_self_test.bat",
            "runtime_preflight": "app\\check_runtime.bat",
            "local_install": "app\\install_local.bat",
            "local_license": "app\\activate_local_license.bat",
            "rules_update": "app\\apply_rules_update.bat",
            "runtime_stage": "app\\stage_python_runtime.bat",
            "ocr_wheelhouse": "app\\build_ocr_wheelhouse.bat",
            "ocr_package_validation": "app\\validate_ocr_package.bat",
            "report_delivery_demo": "app\\build_report_delivery_demo.bat",
            "pilot_feedback_ledger": "app\\record_pilot_feedback.bat",
            "production_sandbox_config": "app\\build_production_sandbox_config.bat",
            "acceptance_smoke": "app\\run_acceptance_smoke.bat",
            "setup": "setup.bat",
            "uninstall": "uninstall.bat",
            "installer_wizard": "installer_wizard\\index.html",
            "cli": "app\\run_cli.bat",
            "desktop_app": "app\\start_desktop_app.bat",
            "local_service": "app\\start_local_service.bat",
            "desktop_shell": "app\\desktop_shell\\index.html",
        },
        "smoke_test": [
            "run_sample_self_test.bat",
            "运行 app\\run_sample_self_test.bat",
            "确认 generated\\sample_out\\batch_manifest.json 存在",
            "确认 OCR 状态命令可返回 JSON",
        ],
        "rules": {
            "rules_manifest": "app\\rules\\rules_manifest.json",
            "ocr_plugin_manifest": "app\\rules\\ocr_plugin_manifest.json",
            "rules_update_manifest": "app\\rules\\rules_update_manifest.json",
        },
        "runtime_assets": {
            "runtime_manifest": "app\\runtime\\runtime_manifest.json",
            "ocr_engine_manifest": "app\\ocr_engines\\ocr_engine_manifest.json",
            "local_license": "app\\license\\local_license.json",
        },
        "capabilities": [
            "runtime_preflight",
            "local_license",
            "rules_update_manifest",
            "ocr_engine_bundle_manifest",
            "sample_self_test",
            "installer_shell",
            "customer_acceptance_package",
            "pilot_operations",
            "acceptance_smoke",
            "desktop_app_launcher",
        ],
        "security_boundary": [
            "原始文件只在本地处理",
            "local_mapping.private.json 不得上传",
            "上传 STPE-AI 的文件应为 sandbox_import_package.json 或 redaction_upload_package.json",
        ],
    }
    _write(package_dir / "install_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    archive = _zip_package(package_dir)
    return {"package_dir": package_dir, "archive": archive}


def _copy_optional(source: Path, target: Path) -> None:
    if source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _ignore_runtime_cache(_dir: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name == "__pycache__" or name.endswith((".pyc", ".pyo"))
    }


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_cli_bat() -> str:
    return """@echo off
setlocal
set "APP_DIR=%~dp0"
set "PYTHONPATH=%APP_DIR%src"
set "EMBEDDED_PY=%APP_DIR%runtime\\python\\python.exe"

if exist "%APP_DIR%ocr_engines\\offline_ocr_installed.marker.json" (
  if exist "%APP_DIR%ocr_engines\\offline_ocr_env.bat" (
    call "%APP_DIR%ocr_engines\\offline_ocr_env.bat" >nul
  )
)

if exist "%EMBEDDED_PY%" (
  "%EMBEDDED_PY%" -m redaction_assistant.cli %*
  exit /b
)

where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    python -m redaction_assistant.cli %*
    exit /b
  )
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -3 -m redaction_assistant.cli %*
    exit /b
  )
)

echo Cannot find Python. Please install Python 3.10+ or run with a configured Python environment.
exit /b 1
"""


def _start_service_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
call run_cli.bat serve-local --host 127.0.0.1 --port 8765
"""


def _start_desktop_app_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
rem launch-desktop-app starts the local service and opens desktop_shell\\index.html
call run_cli.bat launch-desktop-app --app-dir "." --host 127.0.0.1 --port 8765 --wait-seconds 12
if errorlevel 1 (
  echo DESKTOP_APP_START_FAILED
  echo See ..\\generated\\desktop_service.log
  pause
  exit /b 1
)
"""


def _sample_self_test_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if not exist "..\\generated" mkdir "..\\generated"
call check_runtime.bat
if errorlevel 1 exit /b 1
call run_cli.bat batch-build --input-root "..\\sample_data" --out "..\\generated\\sample_out" --mapping-passphrase "sample-local-passphrase"
if errorlevel 1 exit /b 1
call run_cli.bat ocr-status
if errorlevel 1 exit /b 1
echo SAMPLE_SELF_TEST_OK
"""


def _check_runtime_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if not exist "..\\generated" mkdir "..\\generated"
call run_cli.bat runtime-preflight --base-dir ".." --output "..\\generated\\runtime_report.json"
exit /b
"""


def _install_local_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
call check_runtime.bat
if errorlevel 1 exit /b 1
call activate_local_license.bat
if errorlevel 1 exit /b 1
echo INSTALL_READINESS_OK
echo Open desktop shell: %~dp0desktop_shell\\index.html
"""


def _activate_license_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
call run_cli.bat validate-license --input ".\\license\\local_license.json"
exit /b
"""


def _apply_rules_update_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: apply_rules_update.bat path_to_update_dir
  exit /b 2
)
call run_cli.bat apply-rules-update --update-dir "%~1" --active-rules-dir ".\\rules"
exit /b
"""


def _stage_python_runtime_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: stage_python_runtime.bat path_to_python_exe
  exit /b 2
)
call run_cli.bat stage-python-runtime --source-python "%~1" --runtime-dir ".\\runtime"
exit /b
"""


def _build_ocr_wheelhouse_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: build_ocr_wheelhouse.bat path_to_wheelhouse_dir
  exit /b 2
)
call run_cli.bat build-ocr-wheelhouse --wheelhouse-dir "%~1" --out ".\\ocr_engines"
exit /b
"""


def _validate_ocr_package_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
set "MANIFEST=.\\ocr_engines\\ocr_wheelhouse_manifest.json"
if not "%~1"=="" set "MANIFEST=%~1"
if not exist "%MANIFEST%" (
  echo OCR wheelhouse manifest not found: %MANIFEST%
  echo Run build_ocr_wheelhouse.bat path_to_wheelhouse_dir first.
  exit /b 2
)
call run_cli.bat validate-ocr-wheelhouse --manifest "%MANIFEST%"
exit /b
"""


def _report_delivery_demo_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if not exist "..\\generated\\report_demo" mkdir "..\\generated\\report_demo"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$r=@{project_alias_id='project_alpha'; report_title='项目A 后评估报告'; summary='项目A 已完成 10kV 现场试运行30天。'; recommendations=@('继续补充效益证明。')} | ConvertTo-Json -Depth 5; Set-Content -Path '..\\generated\\report_demo\\evaluation_result.json' -Value $r -Encoding UTF8"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$m=@{items=@(@{original='配网智能监测项目'; placeholder='项目A'; kind='project_name'})} | ConvertTo-Json -Depth 5; Set-Content -Path '..\\generated\\report_demo\\local_mapping.private.json' -Value $m -Encoding UTF8"
call run_cli.bat build-report-delivery --evaluation-result "..\\generated\\report_demo\\evaluation_result.json" --mapping "..\\generated\\report_demo\\local_mapping.private.json" --out "..\\generated\\report_demo\\delivery"
exit /b
"""


def _record_pilot_feedback_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if not exist "..\\generated\\pilot_feedback" mkdir "..\\generated\\pilot_feedback"
call run_cli.bat build-pilot-feedback-ledger --out "..\\generated\\pilot_feedback"
exit /b
"""


def _production_sandbox_config_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if not exist "..\\generated\\production_sandbox" mkdir "..\\generated\\production_sandbox"
set "ENDPOINT=http://localhost:7272/api/redaction-sandbox/import"
if not "%~1"=="" set "ENDPOINT=%~1"
call run_cli.bat build-production-sandbox-config --out "..\\generated\\production_sandbox" --endpoint "%ENDPOINT%" --environment "pilot"
if errorlevel 1 exit /b 1
call run_cli.bat validate-production-sandbox-config --input "..\\generated\\production_sandbox\\production_sandbox_config.json"
exit /b
"""


def _acceptance_smoke_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
if not exist "..\\generated\\acceptance_smoke" mkdir "..\\generated\\acceptance_smoke"
call run_cli.bat run-acceptance-smoke --app-dir "." --out "..\\generated\\acceptance_smoke" --project-alias-id "acceptance-smoke"
exit /b
"""


def _start_here(version: str) -> str:
    return f"""# 文档安全脱敏助手可测试安装包

版本: {version}

本包用于最小安装验收：解压后不需要理解源码结构，优先运行 `app\\start_desktop_app.bat`、`app\\install_local.bat` 和 `app\\run_sample_self_test.bat`。

验收顺序:

1. 双击或在 PowerShell 中运行 `app\\start_desktop_app.bat`，由脚本启动本地服务并打开产品页面。
2. 如需安装预检，运行 `app\\install_local.bat`，生成 `generated\\runtime_report.json` 并校验本地授权。
3. 运行 `app\\run_sample_self_test.bat`。
4. 查看 `generated\\sample_out\\batch_manifest.json` 是否生成。
5. 如需单独测试本地服务，运行 `app\\start_local_service.bat`，再在桌面壳中检查 OCR。
6. 如需应用规则更新包，运行 `app\\apply_rules_update.bat 更新包目录`。
7. 如需落盘离线 Python 运行时，运行 `app\\stage_python_runtime.bat python.exe路径`。
8. 如需登记 OCR 离线依赖包，运行 `app\\build_ocr_wheelhouse.bat wheelhouse目录`。
9. 如需校验 OCR 离线依赖包，运行 `app\\validate_ocr_package.bat`。
10. 如需演示报告下载与本地还原，运行 `app\\build_report_delivery_demo.bat`。
11. 如需生成试点问题台账，运行 `app\\record_pilot_feedback.bat`。
12. 如需生成生产沙箱联调配置，运行 `app\\build_production_sandbox_config.bat`。
13. 如需执行完整验收自检，运行 `app\\run_acceptance_smoke.bat`。

边界:

- 当前是可测试安装包，不是正式 MSI/EXE 安装器。
- 当前不内置真实 OCR 模型。
- OCR 插件边界见 `app\\rules\\ocr_plugin_manifest.json`。
- 离线运行时边界见 `app\\runtime\\runtime_manifest.json`。
- 本地授权文件见 `app\\license\\local_license.json`。
- 本地映射表只留在客户本机，不进入上传包。
"""


def _zip_package(package_dir: Path) -> Path:
    archive = package_dir.parent / f"{package_dir.name}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in package_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(package_dir.parent).as_posix())
    return archive

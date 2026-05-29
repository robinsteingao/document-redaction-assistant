from __future__ import annotations

import json
from pathlib import Path


def build_installer_assets(package_dir: Path | str, *, version: str) -> dict[str, Path]:
    root = Path(package_dir)
    assets = {
        "setup": root / "setup.bat",
        "uninstall": root / "uninstall.bat",
        "wizard": root / "installer_wizard" / "index.html",
        "acceptance_checklist": root / "customer_acceptance" / "ACCEPTANCE_CHECKLIST.md",
        "pilot_signoff": root / "customer_acceptance" / "PILOT_SIGNOFF.md",
        "pilot_issue_ledger": root / "customer_acceptance" / "PILOT_ISSUE_LEDGER_TEMPLATE.md",
        "install_record": root / "install_records" / "INSTALL_RECORD_TEMPLATE.md",
        "installer_manifest": root / "installer_manifest.json",
    }
    _write(assets["setup"], _setup_bat())
    _write(assets["uninstall"], _uninstall_bat())
    _write(assets["wizard"], _wizard_html(version))
    _write(assets["acceptance_checklist"], _acceptance_checklist())
    _write(assets["pilot_signoff"], _pilot_signoff())
    _write(assets["pilot_issue_ledger"], _pilot_issue_ledger())
    _write(assets["install_record"], _install_record())
    _write(
        assets["installer_manifest"],
        json.dumps(
            {
                "schema_version": "document_redaction_installer_manifest.v1",
                "version": version,
                "installer_type": "scripted_portable_installer_shell",
                "entrypoints": {
                    "setup": "setup.bat",
                    "uninstall": "uninstall.bat",
                    "wizard": "installer_wizard\\index.html",
                    "acceptance": "customer_acceptance\\ACCEPTANCE_CHECKLIST.md",
                    "pilot_issue_ledger": "customer_acceptance\\PILOT_ISSUE_LEDGER_TEMPLATE.md",
                    "install_record": "install_records\\INSTALL_RECORD_TEMPLATE.md",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    return assets


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _setup_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
echo 文档安全脱敏助手安装预检
call app\\install_local.bat
if errorlevel 1 exit /b 1
echo INSTALLER_SHELL_OK
echo Open installer wizard: %~dp0installer_wizard\\index.html
"""


def _uninstall_bat() -> str:
    return """@echo off
setlocal
cd /d "%~dp0"
echo 本便携包不写入系统注册表。
echo 如需卸载，请先备份 generated 和本地映射文件，再删除本目录。
echo UNINSTALL_GUIDE_OK
"""


def _wizard_html(version: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>文档安全脱敏助手安装向导</title>
  <style>
    :root {{ --ink:#17212b; --muted:#586575; --line:#d6dde5; --bg:#f3f6f8; --accent:#0f766e; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:"Microsoft YaHei","Segoe UI",sans-serif; }}
    main {{ max-width:960px; margin:0 auto; padding:32px; }}
    header {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom:1px solid var(--line); padding-bottom:18px; }}
    h1 {{ margin:0; font-size:26px; }}
    .version {{ color:var(--muted); }}
    ol {{ padding-left:22px; }}
    li {{ margin:16px 0; line-height:1.7; }}
    .panel {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:18px; margin-top:20px; }}
    code {{ background:#eef3f5; padding:2px 6px; border-radius:4px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>文档安全脱敏助手安装向导</h1>
    <div class="version">v{version}</div>
  </header>
  <section class="panel">
    <ol>
      <li><b>安装预检</b>：运行 <code>setup.bat</code>，确认输出 <code>INSTALLER_SHELL_OK</code>。</li>
      <li><b>样例自检</b>：运行 <code>app\\run_sample_self_test.bat</code>，确认输出 <code>SAMPLE_SELF_TEST_OK</code>。</li>
      <li><b>报告交付演示</b>：运行 <code>app\\build_report_delivery_demo.bat</code>，确认生成报告交付清单和本地还原预览。</li>
      <li><b>试点反馈</b>：运行 <code>app\\record_pilot_feedback.bat</code>，确认生成客户试点问题台账。</li>
      <li><b>生产沙箱配置</b>：运行 <code>app\\build_production_sandbox_config.bat</code>，确认配置不包含密钥和原始文件上传策略。</li>
      <li><b>试装记录</b>：填写 <code>install_records\\INSTALL_RECORD_TEMPLATE.md</code>。</li>
      <li><b>客户验收</b>：按 <code>customer_acceptance\\ACCEPTANCE_CHECKLIST.md</code> 完成签收。</li>
    </ol>
  </section>
</main>
</body>
</html>"""


def _acceptance_checklist() -> str:
    return """# 客户试点验收清单

- [ ] `setup.bat` 输出 `INSTALLER_SHELL_OK`。
- [ ] `app\\run_sample_self_test.bat` 输出 `SAMPLE_SELF_TEST_OK`。
- [ ] `app\\build_report_delivery_demo.bat` 生成报告交付清单。
- [ ] `app\\record_pilot_feedback.bat` 生成客户试点问题台账。
- [ ] `app\\build_production_sandbox_config.bat` 生成并校验生产沙箱配置。
- [ ] 报告交付演示可生成本地还原预览。
- [ ] 上传包不包含原始文件。
- [ ] 报告交付包不包含本地映射表。
- [ ] 本地映射表保存在客户本机。
"""


def _pilot_signoff() -> str:
    return """# 客户试点签收单

项目名称：

试点单位：

试点日期：

验收结论：

客户代表：

实施人员：
"""


def _pilot_issue_ledger() -> str:
    return """# 客户试点问题台账模板

记录规则：只记录项目别名、问题类型、影响和处理结论；不记录原始文件路径、原文片段、本地映射表内容和密钥。

| ID | 等级 | 状态 | 项目别名 | 问题类型 | 影响 | 下一步 | 责任人 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M15-PILOT-001 | P1 | open |  | OCR/沙箱/培训 |  |  |  |
"""


def _install_record() -> str:
    return """# 真实环境试装记录

## 环境信息

- 电脑型号：
- Windows 版本：
- Python 状态：
- OCR 状态：

## 执行记录

- `setup.bat` 输出：
- `run_sample_self_test.bat` 输出：
- `build_report_delivery_demo.bat` 输出：

## 问题记录

- 问题描述：
- 处理方式：

## 试装结论

- [ ] 通过
- [ ] 有条件通过
- [ ] 未通过
"""

# M24.7 开源发布预检说明

M24.7 新增开源前只读发布预检，用于在正式公开仓库或发布包前提示常见风险项。

## 本次新增

- 新增 `open_source_preflight.py`，扫描发布范围内的必要边界文档、`.gitignore` 防护项、疑似本地私有文件、临时 release 快照和密钥痕迹。
- 新增 CLI 命令 `open-source-preflight`，可直接打印 JSON，也可写入本地报告文件。
- 新增契约测试，锁定预检只读、不删除文件、不自动修复。

## 边界

- 预检只提供开源前风险提示，不替代人工清单复核、法务审查或正式安全审计。
- 预检不会删除、移动、重命名或脱敏任何文件；发现问题后应由发布负责人手工确认和处理。
- `stpe_upload_package/`、`local_mapping.private.*`、`.release_*`、`license.json`、注册申请和试用台账等均不得进入公开发布范围。

## 命令

```powershell
python -m redaction_assistant.cli open-source-preflight --root .
python -m redaction_assistant.cli open-source-preflight --root . --output .\open_source_preflight_report.json
```

返回 `passed` 表示未发现当前规则覆盖的高/中风险项；返回 `blocked` 表示需要人工清理或确认后再发布。

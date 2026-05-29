# M20 Release Notes - 安装包验收脚本固化与样例测试

发布日期: 2026-05-25

## 目标

M20 将 M19 的真实运行验证固化为包内可重复执行的验收自检，避免现场试装依赖人工记忆多条命令。

## 主要变化

- 新增 `acceptance.py`。
- CLI 新增 `run-acceptance-smoke`。
- 安装包新增 `app\run_acceptance_smoke.bat`。
- 验收输出包括 `generated\acceptance_smoke\acceptance_report.json` 和 `generated\acceptance_smoke\ACCEPTANCE_REPORT.md`。

## 验收范围

- 商业包存在时执行商业包校验。
- 检查 `run_cli.bat` 和 CLI 模块。
- 检查 OCR 状态。
- 使用包内样例数据生成脱敏上传包。
- 校验原始文件和本地映射表不进入上传包。

## 修复

- 从 `app` 目录执行 `--app-dir "."` 时，验收脚本会先解析绝对路径，再回溯安装包根目录，不会误跳过商业包校验。

## 验证

- 文档安全脱敏助手 M1-M20 自动化测试: `53/53 OK`
- 沙箱导入 API 测试: `4/4 OK`
- 最终 runtime-ready 压缩包: `products\document_redaction_assistant\.release_demo_m20_runtime_ready\document_redaction_assistant_install_0.20.0-m20_runtime_ready.zip`
- 压缩包大小: `407,256,116` 字节
- 最终 zip 解压包: M20 验收自检、离线 OCR 启用校验、真实 PDF OCR、桌面四文件入包样例测试均通过。

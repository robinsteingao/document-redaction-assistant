# M11 发布说明：规则更新与依赖清单

## 核心判断

M11 先把规则更新、OCR 依赖包和运行时文件清单做成可验收机制，不在当前环境中伪造真实依赖下载。这样客户后续拿到离线依赖包时，系统已有校验、清单和应用入口。

## 新增能力

- 新增 `rules_update.py`，支持规则更新包校验和应用。
- 新增 `apply-rules-update` 和 `validate-rules-update` 命令。
- 安装包新增 `app\apply_rules_update.bat`。
- 规则更新支持 Windows 常见 UTF-8 BOM JSON 输入，并写回无 BOM 规范 JSON。
- 安装包新增 `app\runtime\runtime_files_manifest.json`。
- 安装包新增 `app\runtime\python\README_RUNTIME.txt`。
- 安装包新增 `app\ocr_engines\requirements-ocr.txt`。
- 安装包新增 `app\ocr_engines\ocr_files_manifest.json`。

## 当前边界

- 当前仍不内置真实 Python 运行时。
- 当前仍不内置真实 OCR 模型。
- 规则更新会阻断破坏“本地映射表不得上传、金额不默认清空、技术指标保留”的更新包。

## 验收口径

- M11 规则更新与运行时依赖清单专项测试 `2/2 OK`。
- 产品全量自动化测试覆盖 M1-M11 与端到端闭环，当前 `27/27 OK`。
- 后端沙箱导入 API 当前 `2/2 OK`。
- M11 目录包执行 `app\install_local.bat` 输出 `INSTALL_READINESS_OK`。
- M11 目录包执行 `app\run_sample_self_test.bat` 输出 `SAMPLE_SELF_TEST_OK`。
- M11 目录包执行 `app\apply_rules_update.bat ..\sample_rule_update` 输出 `applied`。
- M11 zip 解压后重复执行安装预检和样例自检，均通过。

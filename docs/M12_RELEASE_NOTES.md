# M12 发布说明：离线运行时、OCR wheelhouse 与评估触发

## 核心判断

M12 把“客户已经拿到本地运行时和 OCR 依赖包后如何落盘、登记和触发后端评估”做成可测试能力。当前仍不伪造下载真实模型或运行时，但安装包已经具备接收和校验这些离线资产的入口。

## 新增能力

- 新增 `stage-python-runtime` 命令，可将本地 Python 可执行文件落入 `runtime\python\python.exe`。
- 新增 `build-ocr-wheelhouse` 命令，可扫描本地 OCR wheelhouse 并生成 `ocr_wheelhouse_manifest.json`。
- 安装包新增 `app\stage_python_runtime.bat`。
- 安装包新增 `app\build_ocr_wheelhouse.bat`。
- 后端沙箱导入支持注入式 `evaluation_trigger`，导入脱敏项目后可返回 `evaluation_result`。

## 当前边界

- 当前不下载 OCR 模型。
- 当前不提供正式 Python runtime 发行件，只支持把已有本地运行时落盘到包内。
- 沙箱评估触发只接收脱敏 payload 和 `project_alias_id`，不接触原始文件和本地映射表。

## 验收口径

- M12 离线运行时与 OCR wheelhouse 专项测试 `3/3 OK`。
- 后端沙箱导入 API 含评估触发测试 `3/3 OK`。
- 产品全量自动化测试覆盖 M1-M12 与端到端闭环，当前 `30/30 OK`。
- M12 目录包执行 `app\install_local.bat` 输出 `INSTALL_READINESS_OK`。
- M12 目录包执行 `app\run_sample_self_test.bat` 输出 `SAMPLE_SELF_TEST_OK`。
- M12 目录包执行 `app\stage_python_runtime.bat ..\fake_python.exe` 可落盘运行时。
- M12 目录包执行 `app\build_ocr_wheelhouse.bat ..\sample_wheelhouse` 可生成 OCR wheelhouse 清单。
- M12 zip 解压后重复执行安装预检和样例自检，均通过。

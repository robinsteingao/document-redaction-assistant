# M9 发布说明：离线运行时与本地授权边界

## 核心判断

M9 不把真实 OCR 模型或 Python 运行时强行打进包内，而是先把离线运行时、本地授权、规则更新和 OCR 引擎包的可测试边界做出来。这样后续替换为正式离线运行时或真实 OCR 引擎时，不需要推翻安装包结构。

## 新增能力

- 新增 `local_license.py`，支持本地试点授权生成和校验。
- 新增 `write-license` 和 `validate-license` 命令。
- 安装包新增 `app\license\local_license.json` 和 `app\activate_local_license.bat`。
- 新增 `offline_runtime.py`，生成 `runtime_manifest.json` 和 `ocr_engine_manifest.json`。
- 规则包新增 `rules_update_manifest.json`，约束规则更新的可改项和禁止项。
- `install_local.bat` 同时执行运行预检和本地授权校验。

## 当前边界

- 当前不内置 Python 运行时，`runtime_manifest.json` 明确标记 `bundled_python=false`。
- 当前不内置真实 OCR 引擎，`ocr_engine_manifest.json` 只提供接入槽位和边界。
- 本地授权文件用于试点能力开关，不包含客户原始文件内容，不上传服务端。

## 验收口径

- M9 离线运行时与本地授权专项测试 `2/2 OK`。
- 产品全量自动化测试覆盖 M1-M9 与端到端闭环，当前 `22/22 OK`。
- 后端沙箱导入 API 当前 `2/2 OK`。
- 生成的 M9 安装包目录执行 `app\install_local.bat`，输出 `INSTALL_READINESS_OK` 且授权状态为 `valid`。
- 生成的 M9 安装包目录执行 `app\run_sample_self_test.bat`，输出 `SAMPLE_SELF_TEST_OK`。
- M9 zip 解压后重复执行安装预检、授权校验和样例自检，均通过。

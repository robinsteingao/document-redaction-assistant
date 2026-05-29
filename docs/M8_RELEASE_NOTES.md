# M8 发布说明：安装就绪与规则包边界

## 核心判断

M8 解决“客户电脑拿到包后能不能跑、缺什么、从哪里启动”的问题。真实 OCR 引擎不在本阶段强行内置，先用预检报告、规则包清单和 OCR 插件清单把安装边界做清楚。

## 新增能力

- 新增 `runtime-preflight` 命令，输出运行环境预检报告。
- 安装包新增 `app\install_local.bat`，用于生成预检报告并提示桌面壳入口。
- 安装包新增 `app\check_runtime.bat`，用于单独检查运行环境。
- 安装包新增 `app\rules\rules_manifest.json`，固化评估保真脱敏规则边界。
- 安装包新增 `app\rules\ocr_plugin_manifest.json`，固化 OCR 插件接入边界。
- 样例自检前会先生成 `generated\runtime_report.json`。

## 当前边界

- 当前仍是可测试安装包，不是正式 MSI/EXE 安装器。
- 当前不内置真实 OCR 模型。
- OCR 支持以插件清单和适配器接口方式预留，后续再接入具体轻量引擎。

## 验收口径

- M8 安装就绪专项测试 `2/2 OK`。
- 产品全量自动化测试覆盖 M1-M8 与端到端闭环，当前 `20/20 OK`。
- 后端沙箱导入 API 当前 `2/2 OK`。
- 生成的 M8 安装包目录执行 `app\install_local.bat`，输出 `INSTALL_READINESS_OK`。
- 生成的 M8 安装包目录执行 `app\run_sample_self_test.bat`，输出 `SAMPLE_SELF_TEST_OK`。
- M8 zip 解压后重复执行安装预检和样例自检，均通过。

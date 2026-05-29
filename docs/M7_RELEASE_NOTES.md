# M7 发布说明：可测试安装包生成

## 核心判断

M7 的最小交付目标是“可测试安装包”，不是正式安装器。这样可以先验证客户侧解压、启动、样例脱敏和自检流程，避免过早投入 MSI/EXE 安装器。

## 新增能力

- 新增 `build-install-package` 命令，生成目录包和 zip 包。
- 安装包包含 `START_HERE.md`、`install_manifest.json`、产品源码、Windows 启动脚本、桌面壳、样例数据和发布说明。
- 安装包内置 `app\run_sample_self_test.bat`，可生成样例批处理脱敏输出并检查 OCR 状态。
- 安装包内置 `app\start_local_service.bat`，用于启动本地产品服务。

## 当前边界

- 当前包是可测试安装包，不是正式 MSI/EXE 安装器。
- 当前不内置真实 OCR 模型。
- 当前依赖客户电脑已有可用 Python 3.10+ 环境；正式离线运行时将在后续阶段处理。

## 验收口径

- M7 安装包契约测试 `1/1 OK`。
- 产品全量自动化测试覆盖 M1-M7 与端到端闭环，当前 `18/18 OK`。
- 后端沙箱导入 API 当前 `2/2 OK`。
- 生成的安装包目录内执行 `app\run_sample_self_test.bat`，输出 `SAMPLE_SELF_TEST_OK`。

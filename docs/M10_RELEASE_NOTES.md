# M10 发布说明：OCR 适配与运行时槽位

## 核心判断

M10 先把真实 OCR 适配路径和离线运行时启动槽位做成可测试接口，不在当前包内强行捆绑 OCR 模型和 Python 运行时。这样既消除了当前加密告警，也为 M11 的真实离线依赖打包留下稳定入口。

## 新增能力

- 加密派生改为本地 PBKDF2-HMAC-SHA256 兼容实现，消除当前环境中的 `pbkdf2_hmac()` 弃用告警。
- OCR 适配器支持 RapidOCR 真实懒加载调用路径。
- OCR 适配器支持 PaddleOCR 真实懒加载调用路径。
- 安装包新增 `app\runtime\run_with_embedded_python.bat`。
- 安装包新增 `app\ocr_engines\OCR_SETUP.md`。

## 当前边界

- 当前不内置真实 OCR 模型。
- 当前不内置 Python 运行时。
- `run_with_embedded_python.bat` 在未发现内置 Python 时回退到 `run_cli.bat`。

## 验收口径

- M10 OCR 与运行时专项测试 `3/3 OK`。
- 产品全量自动化测试覆盖 M1-M10 与端到端闭环，当前 `25/25 OK`。
- 后端沙箱导入 API 当前 `2/2 OK`。
- 生成的 M10 安装包目录执行 `app\install_local.bat`，输出 `INSTALL_READINESS_OK`。
- 生成的 M10 安装包目录执行 `app\run_sample_self_test.bat`，输出 `SAMPLE_SELF_TEST_OK`。
- `app\runtime\run_with_embedded_python.bat ocr-status` 在未内置 Python 时可回退执行。
- M10 zip 解压后重复执行安装预检和样例自检，均通过。

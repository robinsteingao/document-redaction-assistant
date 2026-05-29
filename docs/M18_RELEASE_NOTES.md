# M18 发布说明：真实环境可运行软件包

## 本阶段目标

M18 将交付件从“可装配商业包”推进为“当前真实 Windows 环境可运行软件包”。核心标准是：不依赖客户电脑已有 Python，包内运行时可执行，OCR 可通过本地 wheelhouse 离线安装并被 `ocr-status` 识别为可用。

## 新增能力

- `run_cli.bat` 优先使用包内 `app\runtime\python\python.exe`。
- 商业包内置 Python 运行时保留 pip/setuptools 必要组件。
- OCR 默认运行路线切换为 RapidOCR。
- 离线安装脚本安装 `rapidocr-onnxruntime` 及其本地 wheelhouse 依赖。
- 生成 runtime-ready 包，已完成 OCR 离线安装并写入启用标记。

## 验证结论

- 短路径安装目录 `D:\tmp\m18\document_redaction_assistant_install_0.18.0-m18` 下，`app\install_offline_ocr.bat` 执行成功。
- 执行 `app\ocr_engines\offline_ocr_env.bat` 后，`app\run_cli.bat ocr-status` 返回 `available`。
- `setup.bat` 和 `app\run_sample_self_test.bat` 均通过。

## 边界

- Windows 深路径会导致部分 OCR 依赖安装失败，客户侧建议解压至 `D:\DRA`、`D:\tmp\dra` 等短路径。
- M18 已验证 OCR 引擎可用状态，下一阶段还需用真实扫描件验证识别文本、置信度和人工复核提示。

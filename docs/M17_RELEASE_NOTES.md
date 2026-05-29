# M17 发布说明：离线 OCR 启用链路

## 本阶段目标

M17 解决 M16 的关键缺口：OCR 离线文件已经装配进商业包，但还缺少面向客户电脑的离线安装、环境配置和启用校验链路。

## 新增能力

- `build-offline-ocr-plan`：生成 OCR 离线安装计划。
- `validate-offline-ocr`：校验 OCR 是否已启用。
- `mark-offline-ocr-installed`：安装成功后写入本地启用标记。
- `app\install_offline_ocr.bat`：使用内置 Python 和本地 wheelhouse 执行 `--no-index --find-links` 离线安装。
- `app\validate_offline_ocr.bat`：客户现场校验 OCR 启用状态。

## 边界

- M17 建立离线 OCR 安装和启用链路，不声称 OCR 真实识别已验收。
- 下一阶段需要用真实扫描件样例验证 OCR 输出文本、置信度和复核提示。

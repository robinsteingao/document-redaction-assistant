# M16 发布说明：完整离线商业包装配层

## 本阶段目标

M16 将交付目标从可测试便携包升级为完整离线商业包：客户电脑不应依赖外网下载，不应要求客户理解 Python、OCR 或 Office 转换依赖。

## 新增能力

- `build-commercial-package`：在构建时装配本地 Python 运行时、OCR wheelhouse 和 Office/WPS 转换组件。
- `validate-commercial-package`：校验商业包是否具备内置 Python、OCR 离线依赖和 Office 转换器。
- `commercial_release_manifest.json`：明确商业包状态为 `complete_offline` 或 `staging_required`。
- `app\validate_commercial_package.bat`：客户现场一键校验商业包完整性。
- `app\start_offline_app.bat`：校验通过后使用内置运行时启动本地服务。

## 边界

- 本阶段不联网下载 OCR 模型、Python 运行时或 Office 组件。
- 真实二进制由构建机预先准备后通过目录参数装配。
- 未提供组件目录时，包会标记为 `staging_required`，不会伪装成完整离线包。
- OCR 离线文件装配完成不等于 OCR 已在内置 Python 环境中启用；下一阶段需要补离线安装脚本和扫描件识别验收。

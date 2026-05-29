# M15 发布说明：客户试点运行闭环

## 本阶段目标

M15 解决试点上线后的运行管理问题：客户现场问题如何记录、OCR 离线依赖包如何验真、生产沙箱联调配置如何避免误带原始材料和密钥。

## 新增能力

- `build-pilot-feedback-ledger`：生成客户试点问题台账 JSON 和 Markdown。
- `validate-ocr-wheelhouse`：校验 OCR wheelhouse 清单中的文件存在性、大小和 SHA256。
- `build-production-sandbox-config`：生成生产沙箱导入配置模板。
- `validate-production-sandbox-config`：校验沙箱配置是否只允许脱敏包，并阻断密钥类明文值。
- 安装包新增 `app\record_pilot_feedback.bat`、`app\validate_ocr_package.bat`、`app\build_production_sandbox_config.bat`。

## 边界

- M15 不联网下载 OCR 模型或依赖。
- M15 不保存真实沙箱密钥。
- M15 不上传原始文件、本地映射表和原文片段。

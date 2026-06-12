# 开源发布前检查指南

本指南用于文档脱敏助手公开仓库或发布包前的人工复核。

## 必须排除

- 真实样本、客户材料、原始文档和未脱敏内容。
- `.release_*`、`.release*`、历史安装包快照和本地盲测输出。
- `local_mapping.private.*`、映射表、恢复预览和人工复核中间产物。
- `registration_request.json`、`registration_mailto.txt`、`trial_usage_*.json`、`license.json`。
- 密钥、`.env`、API token、私钥、证书和 SMTP 密码。
- `stpe_upload_package/` 等本地生成包，除非已确认只含公开演示样例。

## 建议步骤

1. 先运行全量测试。
2. 运行 `open-source-preflight`，确认输出 `status=passed`。
3. 人工检查 `README.md`、`LICENSE`、`PRIVACY.md`、`COMMERCIAL.md`、`DISCLAIMER.md`。
4. 人工确认 release 包不含真实样本或客户敏感数据。
5. 正式公开前补齐 AGPL-3.0-or-later 完整官方文本或官方副本。

预检工具只是辅助门禁，不替代人工清单复核、法务审查或正式安全审计。

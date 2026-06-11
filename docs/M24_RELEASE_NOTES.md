# M24 发布说明：客户自定义脱敏与评价影响门禁

> 日期：2026-06-03
> 范围：文档安全脱敏助手独立支线，不改变 STPE-AI 主系统评分、TRL、readiness 或报告强结论口径。

## 核心变化

- 新增上传前 `redaction_impact_summary`，记录客户脱敏选择对 STPE-AI 评价审查的影响：TRL、效益、证据核验和转化就绪度。
- 支持客户通过 `review_decisions.json` 对候选字段选择 `keep / redact`，并选择 `pseudonym / mask / range` 策略。
- 技术指标和验证信息默认建议保留；如客户强制脱敏，门禁标记为 `blocked_requires_confirmation`，提示评价可能降级。
- 复核工作区展示“影响等级”和“评价影响提示”，便于内部测试人员确认哪些字段脱敏会影响评价。
- 桌面壳新增“评价影响提醒”说明和“自定义字段处理方式”输入框。

## 已修复的脱敏覆盖问题

- 新增联系人/负责人姓名识别，覆盖 `联系人：张三` 等场景。
- 专利号规则覆盖 `CN202410123456.7` 以及既有 `ZL...` 格式。
- 金额识别补充英文 `Amount / Budget / Cost / Revenue` 标签场景。
- 技术指标候选补充 `96.5%`、`10kV`、`30天` 等常见评价因子，默认 `keep`。

## 边界说明

- 本切片不改变 STPE-AI 评价规则，只在脱敏包中增加评价影响提示。
- 客户仍可强制脱敏高影响字段；只有客户显式确认“接受评价降级风险”时，系统才记录 `customer_confirmed=true`。仅提交 `review_decisions.json` 不代表已确认该风险。
- `.xls/.wps` 真实样本专项验证仍按 `M24_XLS_WPS_SAMPLE_PREP.md` 等待样本副本后执行。

## 验证

- `python -m pytest products/document_redaction_assistant/tests/test_m24_custom_redaction_gate.py -q`：`15 passed`
- `python -m pytest products/document_redaction_assistant/tests -q`：`86 passed`
- `python -m pytest prototype/tests/test_redaction_sandbox_import_api.py -q`：`4 passed`

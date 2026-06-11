# M24 文档安全脱敏助手 — 内部测试说明 / Checklist

> 适用版本：脱敏助手 M24（`0.24.0-m24`）
> 适用范围：本轮"客户可选脱敏项 + 评价影响门禁"支线增强。
> 本文档是内测执行手册，不改变 STPE-AI 主系统评价规则。

---

## 0. 一句话定位（务必先读）

本轮门禁回答的是：**"客户选择的脱敏，会不会削弱 STPE-AI 对该项目的评价（TRL / 效益 / 成果证据 / 转化就绪度）"**。

它**不**回答："脱敏后文档里还有没有残留隐私"。
门禁显示 `pass` **不等于**"可以安全上传"——它只代表"在**被识别到的**字段里，没有发现会阻断评价的强脱敏"。未被识别到的隐私不在门禁视野内。**请把这一句话原样转达给每一位测试人员。**

---

## 1. 本轮范围 / 不在范围

| 在范围（本轮要测） | 不在范围（本轮不验证） |
|---|---|
| 客户经 `review_decisions.json` 选择 `keep/redact` + `pseudonym/mask/range` | STPE-AI 主报告评分、TRL 口径、readiness 分值 |
| 脱敏包新增 `redaction_impact_summary` 及门禁等级 | 数据库 schema / 评分规则变化 |
| 默认策略（姓名电话邮箱脱敏、金额区间、专利软著占位、技术指标保留） | `.xls/.wps` 真实样本专项验证（**仍未完成**） |
| 脱敏覆盖修复（`联系人：张三`、`CN…`、英文金额标签、技术指标） | 原生文件选择器（当前仍是静态壳 + 手填路径） |
| 复核工作区展示影响等级 / 影响提示 | 评估判断层真值验证（门禁映射为启发式，未经真实项目校准） |

---

## 2. 环境与启动

1. Python 环境：项目既有虚拟环境，确认可 `python -m pytest` 正常运行。
2. 本地服务 / 桌面壳启动方式以 README 与桌面壳说明为准（桌面壳页面内引用 `app\start_local_service.bat` / `app\start_offline_app.bat`，服务默认 `http://127.0.0.1:8765`）。
3. 桌面壳：打开生成的 `desktop_shell_<version>\index.html`，确认“评价影响提醒”区块与“自定义字段处理方式”输入框可见。
4. 输出目录：相对路径会落到 `文档\文档安全脱敏助手输出\`，确认有写入权限。

---

## 3. 冒烟测试（全部必过，任一不过即阻断内测）

```powershell
# 门禁专项
python -m pytest products/document_redaction_assistant/tests/test_m24_custom_redaction_gate.py -q   # 期望 15 passed
# 产品全量
python -m pytest products/document_redaction_assistant/tests -q                                      # 期望 86 passed
# 沙箱导入 API
python -m pytest prototype/tests/test_redaction_sandbox_import_api.py -q                              # 期望 4 passed
```

- [ ] 三条命令全部通过，数字与上面一致
- [ ] 启动本地服务无报错，桌面壳页面正常加载
- [ ] 生成一次脱敏包，输出目录出现：`redaction_upload_package.json`、`local_mapping.private.json`、`redaction_review_report.md`、`review_workspace.html`、`sandbox_import_package.json`

---

## 4. 功能用例矩阵（脱敏覆盖）

用下面这段确定性文本作为标准样本（可直接存成 `.txt` 上传）：

```
联系人：张三
电话：13800138000
邮箱：tester@example.com
专利 CN202410123456.7
软著 2024SR1234567
合同金额：320.50万元
Amount: 480000
试运行30天，效率96.5%，电压10kV。
```

| # | 字段 | 期望默认行为 | 判定 |
|---|---|---|---|
| 4.1 | `张三` | 被脱敏（不出现在脱敏正文） | ☐ |
| 4.2 | `13800138000` / `tester@example.com` | 被脱敏（mask） | ☐ |
| 4.3 | `CN202410123456.7` | 稳定占位符替换，正文不含原号 | ☐ |
| 4.4 | `2024SR1234567` | 稳定占位符替换 | ☐ |
| 4.5 | `320.50万元` | 区间化（如"100万至500万"），非阻断 | ☐ |
| 4.6 | 英文 `Amount:` 金额 | 被识别为金额（见 §6 已知问题，注意区间数值偏差） | ☐ |
| 4.7 | `96.5%` / `10kV` / `30天` | **默认保留**，出现在脱敏正文中 | ☐ |
| 4.8 | 还原预演 | `review_workspace.html` 还原版能还原回原值 | ☐ |

---

## 5. 门禁专项用例

复核选择的回路：**首次生成 → 打开 `review_workspace.html` → 编辑/导出 `review_decisions.json` → 用记事本打开并修改 → 粘贴回桌面壳“自定义字段处理方式” → 重跑**。

| # | 操作 | 期望门禁结果 | 判定 |
|---|---|---|---|
| 5.1 | 全默认（不提交任何决策） | `overall_level = pass`；`trl_impact = none`；`benefit_impact = low`；`customer_confirmed = false` | ☐ |
| 5.2 | 仅金额，默认区间 | `overall_level ≠ blocked_requires_confirmation`；`benefit_impact = low` | ☐ |
| 5.3 | 客户强制脱敏某技术指标（`action=redact`，**显式** `strategy=mask`），但不勾选/不传入“确认接受评价降级风险” | `overall_level = blocked_requires_confirmation`；`trl_impact = high`；`redacted_assessment_fields` 含 `technical_metric`；`customer_decisions_present = true`；`customer_confirmed = false` | ☐ |
| 5.4 | 客户保留某隐私字段（如 email `action=keep`） | `overall_level = warning`；`kept_sensitive_fields` 含 `email` | ☐ |
| 5.5 | `redaction_review_report.md` 含"评价影响门禁"与"门禁提示"两行 | 与 `overall_level` 一致 | ☐ |
| 5.6 | `review_workspace.html` 表格含"影响等级"与"评价影响提示"列 | 数据非空 | ☐ |
| 5.7 | 粘贴错误或过期的 `candidate_id` | 脱敏包 `redaction_impact_summary.unmatched_decisions` 显示该 ID，测试人员可发现决策未生效 | ☐ |
| 5.8 | 客户强制脱敏技术指标但未写 `strategy` | 实际 mapping 与 impact 均记录 `strategy=mask`，`strongly_redacted_fields` 含 `technical_metric` | ☐ |
| 5.9 | `承担单位：甲、乙联合体，合同金额：320万元` | 单位识别为 `甲、乙联合体`，金额 `320万元` 被单独识别；中文逗号仍分隔字段，顿号保留在单位名内部 | ☐ |
| 5.10 | 客户强制脱敏某技术指标，并显式勾选/传入 `customer_confirmed_degradation_risk = true` | `overall_level = blocked_requires_confirmation`；`customer_decisions_present = true`；`customer_confirmed = true`；`customer_confirmation_source = explicit_customer_confirmed_degradation_risk` | ☐ |

> 建议内测仍尽量显式写 `strategy`，便于复核；但未写 `strategy` 的强制脱敏路径已补回归测试，impact 会以 mapping 实际策略为准。

---

## 6. 已知问题与重点观察项（来自本轮代码审查，**非新 bug，勿重复上报**）

下列问题已在代码审查中确认并复现。内测时请**按"重点观察"对待**，遇到相应现象记录但不必新建缺陷单；是否在内测前修复由负责人决定。

| 编号 | 现象 | 影响 | 测试人员应如何应对 |
|---|---|---|---|
| **KI-1（已修复，需复测）** | `customer_confirmed` 只认显式 `customer_confirmed_degradation_risk = true`；仅提交任何 `review_decisions`（包括全 `keep`、错 ID、强制脱敏但未确认风险）不会置 true | 审计语义收口：`customer_decisions_present` 只表示客户提交过决策，`customer_confirmed` 才表示显式确认接受评价降级风险 | 执行 §5.3、§5.7、§5.10，确认无显式风险确认时 `customer_confirmed=false`，有显式风险确认时才为 true |
| **KI-2（已修复，需复测）** | 客户决策里的 `candidate_id` 若与实际候选不匹配，会写入 `redaction_impact_summary.unmatched_decisions` | 旧风险是静默忽略；当前应显性暴露，便于测试人员发现"我的决策没生效" | 用错误 ID 构造样本，确认 `unmatched_decisions` 非空；改动源文本后仍建议重新导出决策文件 |
| **KI-3（已修复，需复测）** | 对默认保留字段强制 `redact` 且未写 `strategy` 时，impact 应读取 mapping 实际策略 `mask` | 旧风险是 action=redact / strategy=keep 自相矛盾；当前应保持一致 | 执行 §5.8，确认 `strongly_redacted_fields` 命中 |
| **KI-4（已修复，需复测）** | `单位：`/`项目名称：` 标签已把中文逗号、顿号、英文逗号作为停止符 | 旧风险是整段吞掉金额/人名；当前金额和联系人应单独识别 | 构造"单位：X，合同金额：…，联系人：…"同一行样本，确认金额、人名未被单位占位吞掉 |
| **KI-5** | 金额区间换算对**无单位**英文金额（如 `Amount: 480000`）按裸数判定区间，结果可能与直觉不符 | 效益区间估计偏差（非阻断） | 区间是辅助估计，不作判定依据；记录明显离谱的区间即可 |
| **KI-6** | 脱敏采用整串替换、无词边界 | 极端情况下原值作为子串出现在更长 token 中会被连带替换 | 留意人名/编号是否误伤了相邻无关文本 |

---

## 7. 通过 / 阻断判定标准

- **通过内测**：§3 冒烟全过 + §4 全部 ☐ 勾选 + §5 全部 ☐ 勾选 + §6 各项现象与本表描述一致（无新增、更严重的偏差）。
- **阻断（需回研发）**：出现任一 ——
  - 默认策略下隐私字段（姓名/电话/邮箱）**未被脱敏**且未进入门禁视野；
  - 客户 `redact` 决策（ID 正确）**未生效导致原值泄露**；
  - 门禁等级与实际脱敏行为方向相反（例如强脱敏技术指标却报 `pass`）；
  - 脱敏包在未显式 `customer_confirmed_degradation_risk=true` 时，被当作"客户已确认接受评价降级风险"流转。

---

## 8. 每条用例需记录

- 输入样本（文件名 / 文本片段）、使用的 `review_decisions.json`（如有）
- `redaction_impact_summary` 的 `overall_level` / `trl_impact` / `benefit_impact` / `customer_decisions_present` / `customer_confirmed`
- 脱敏正文片段 + 是否与 `structured_facts` 一致
- 命中的已知问题编号（KI-x）或新增异常

---

## 9. 对客户/对外的红线（测试结论不得逾越）

1. 门禁是**建议级**，不是结论级；不得以门禁 `pass` 向客户承诺"无隐私残留"或"评价不受影响"。
2. 本轮为脱敏助手支线增强，**不代表 STPE-AI 主系统评价规则、TRL 口径或 readiness 分值发生任何变化**。
3. 门禁映射（哪个字段影响 TRL/效益/证据）为**启发式、未经真实项目真值校准**；内测可用于演示与功能验证，真值采信需另走独立验证线。
4. `.xls/.wps` 真实样本专项验证尚未完成，相关结论暂不外推。

---

_本 checklist 随 M24 内测一同分发；§6 已知问题对应的研发处置以负责人决定为准。_

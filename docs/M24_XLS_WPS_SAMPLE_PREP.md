# M24-A `.xls/.wps` 真实样本专项验证准备清单

> 状态：样本准备中
> 范围：仅用于规划 M24-A，不修改 M23 既有产物，不触碰 STPE-AI 主线。

## 目标

补齐 M23 后仍未闭环的 `.xls/.wps` 真实样本验证边界，确认旧版表格与 WPS 文件能够完成：

1. 预检识别为 `convertible_files`；
2. 本地 LibreOffice 转换；
3. 脱敏上传包入包；
4. 本地映射表生成；
5. 沙箱导入包结构有效；
6. 不泄露原始文件和本地映射表。

## 样本要求

- 至少 2 个 `.xls` 文件：优先包含预算、效益、人员或项目台账字段。
- 至少 2 个 `.wps` 文件：优先包含项目说明、合同、验收或管理材料。
- 样本必须使用副本目录，不直接处理原始收资目录。
- 样本目录建议放置于短路径，例如：`C:\tmp\dra_m24_xls_wps_samples_YYYYMMDD`。

## 允许修改范围（后续执行时）

- `products/document_redaction_assistant/tests/test_m23_office_conversion_jobs.py`
- `products/document_redaction_assistant/docs/M24_REAL_SAMPLE_TEST_REPORT.md`
- `products/document_redaction_assistant/docs/M24_RELEASE_NOTES.md`
- `products/document_redaction_assistant/README.md` 的后续版本段落

## 禁止修改范围

- `PRODUCT_VISION.md`
- `AGENTS.md`
- `ROADMAP.md` 既有历史条目
- `prototype/src/backend/**`
- `prototype/src/frontend/**`
- 数据库 schema
- 评分规则、TRL 口径、就绪度口径和报告强结论措辞
- M20-M23 既有 runtime-ready 压缩包

## 建议验收命令（后续执行时）

```powershell
python -m pytest products/document_redaction_assistant/tests/test_m23_office_conversion_jobs.py -v
python -m pytest products/document_redaction_assistant/tests/
```

真实样本验证需补充手工记录：

- 输入样本目录
- `.xls/.wps` 文件数量
- `conversion_report.converted_count`
- `conversion_report.failed_count`
- 上传包 `source_file_count`
- 文本块数量
- 映射项数量
- 沙箱导入包路径
- 是否存在原始文件或本地映射表误入包

## 当前结论

M24-A 暂不编码，等待用户确认 `.xls/.wps` 真实样本副本目录后再启动。

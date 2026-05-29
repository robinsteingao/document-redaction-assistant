# M23 Release Notes: 旧版 Office 转换与任务控制

日期: 2026-05-25

## 本阶段目标

把 M22 发现的旧版 Office/WPS 缺口推进到可运行状态，同时补齐用户任务控制能力。

## 新增能力

- `.doc/.xls/.wps` 本地转换:
  - `.doc/.wps` 转 `.docx`
  - `.xls` 转 `.xlsx`
  - 转换失败文件不会静默入包
- 预检结果新增 `convertible_files / convertible_count`。
- 后台任务新增取消与重试:
  - `/cancel-job`
  - `/retry-job`
- 桌面壳新增“取消当前任务”“重试失败任务”。
- 任务结果新增 `conversion_report`，记录转换器、成功文件和失败文件。

## 修复

- 修复商业包 Office 运行时装配问题: 传入 `LibreOffice\program` 时保留完整 LibreOffice 根目录结构，避免包内 `soffice.exe` 缺少 `share` 等依赖。
- 修复 LibreOffice 转换策略: 默认不强制指定 `UserInstallation`，避免当前发行版报 `User installation could not be completed`。

## 真实样本验证

- 样本副本: `C:\tmp\dra_m21_nanwang_samples_20260525_153902`
- 可直接处理: `39`
- 可转换 DOC: `6`
- 转换成功: `6`
- 转换失败: `0`
- 入包文件数: `45`
- 文本块数: `744`
- PDF OCR 成功: `36`
- 映射项: `40`
- 任务耗时: `406.56s`

## 验证

- 文档安全脱敏助手自动化测试: `71/71 OK`
- 脱敏沙箱导入 API 测试: `4/4 OK`
- 商业包校验: `status=valid`
- 离线 OCR 安装: 成功
- runtime-ready 压缩包: `products\document_redaction_assistant\.release_demo_m23_runtime_ready\document_redaction_assistant_install_0.23.0-m23_runtime_ready.zip`
- 压缩包大小: `324,178,343` 字节

## 边界

- `.xls/.wps` 仍需真实样本专项验证。
- 取消任务不是强杀当前转换/OCR 进程，而是在当前文件处理回调点生效。
- 正式客户版仍需要桌面容器或原生 GUI 来解决文件选择体验。

# M23 真实样本测试报告

> 日期: 2026-05-25
> 产品: 文档安全脱敏助手 `v0.23.0-m23`
> 测试目标: 旧版 Office/WPS 自动转换、后台任务取消/重试入口、M22 南网样本副本全链路复测。

## 核心结论

M23 已解决 M22 的关键遗留问题: 旧版 `.doc` 不再只停留在“需转换”提示，而是在本地自动转换为 `.docx` 后进入脱敏处理链路。使用南网样本副本复测时，39 个原可处理文件加 6 个 `.doc` 转换文件全部入包，任务完成状态为 `completed`。

## 实现范围

- 新增 `office_converter.py`，通过包内 LibreOffice `soffice.exe` 执行 `.doc/.xls/.wps` 到 `.docx/.xlsx` 的本地转换。
- `collect_user_inputs()` 新增 `convertible_files / convertible_count`，旧版 Office/WPS 文件不再归入 `unsupported_files`。
- 本地服务新增:
  - `/cancel-job`
  - `/retry-job`
  - 后台任务 `conversion_report`
- 桌面壳新增:
  - 取消当前任务
  - 重试失败任务
  - 旧版 DOC/XLS/WPS 自动转换提示
- 商业包装配修复: 传入 `LibreOffice\program` 时，保留完整 LibreOffice 根目录结构，避免只复制 `program` 导致包内 `soffice.exe` 无法启动。

## 关键排错记录

1. 首次真实 DOC 转换在沙箱内超时。放开真实环境后发现 LibreOffice 指定 `UserInstallation` 会报 `User installation could not be completed`。
2. 直接使用 LibreOffice 默认用户配置可在约 11 秒内把 `sample_040.doc` 转换为 `sample_040.docx`。
3. 首次 M23 包内复测时，6 个 DOC 全部转换失败，返回码 `3765269347`。根因是商业包只复制了 `LibreOffice\program`，丢失上级 `share` 等运行时目录。
4. 修复装配逻辑后，包内转换器路径为 `app\office_runtime\program\soffice.exe`，6 个 DOC 全部转换成功。

## 真实样本复测

- 样本副本: `C:\tmp\dra_m21_nanwang_samples_20260525_153902`
- 原始样本目录: 只读，不直接处理。
- M23 包: `C:\tmp\dra_m23_build_fixed\document_redaction_assistant_install_0.23.0-m23`
- runtime-ready 包: `products\document_redaction_assistant\.release_demo_m23_runtime_ready\document_redaction_assistant_install_0.23.0-m23_runtime_ready.zip`
- 包大小: `324,178,343` 字节

### 预检结果

- 可直接处理: `39`
- 可转换: `6`
- 不支持: `0`
- 跳过: `1`
- OCR: RapidOCR `available`

### 任务结果

- job_id: `a473c1daadd6478bab5bfee94d99ef18`
- 状态: `completed`
- 耗时: `406.56s`
- DOC 转换成功: `6`
- DOC 转换失败: `0`
- 转换临时目录残留: `false`

### 输出产物

- `redaction_upload_package.json`: `393,569` 字节
- `local_mapping.private.json`: `12,822` 字节
- `review_candidates.json`: `9,615` 字节
- `review_workspace.html`: `15,042` 字节
- `sandbox_import_package.json`: `388,497` 字节

### 产物校验

- 入包文件数: `45`
- 文本块数: `744`
- 映射项数: `40`
- PDF OCR 成功数: `36`
- 转换 DOCX 入包数: `6`
- 沙箱文件数: `45`
- 沙箱文本块数: `744`
- 映射替换值复现原始值: `0`
- 分析保真:
  - `trl_factors_preserved=true`
  - `benefit_factors_preserved=true`
  - `stable_placeholders_used=true`
- 复核警告: `[]`

## 自动化验证

- M23 聚焦测试: `5/5 OK`
- 文档安全脱敏助手完整测试: `71/71 OK`
- STPE-AI 脱敏沙箱导入 API 测试: `4/4 OK`
- 商业包校验: `status=valid`
- 离线 OCR 安装: 成功

## 剩余边界

- `.wps` 和 `.xls` 已接入转换框架，但本轮真实样本只有 `.doc`，还需要专项样本验证。
- 取消任务依赖处理过程中的进度回调触发；正在执行单个大 PDF OCR 或 LibreOffice 转换时，取消会在当前文件处理完成后生效。
- 静态浏览器壳仍不能提供真正的系统级文件选择器；如要达到正式客户体验，下一阶段应转桌面容器或原生 GUI。

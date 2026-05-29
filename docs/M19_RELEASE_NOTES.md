# M19 Release Notes - 真实 PDF OCR 主链路回归

发布日期: 2026-05-24

## 目标

M19 解决真实应用测试暴露的 PDF OCR 断点：OCR 引擎已经可用，但 PDF 文件没有先渲染为图片，导致 `ocr-extract` 对 PDF 抛异常，`build-package` 也只标记 `ocr_required`，没有将 PDF 内容纳入脱敏上传包。

## 主要变化

- PDF OCR 先通过 `pypdfium2` 渲染为临时 PNG，再交给 RapidOCR/PaddleOCR。
- `ocr-extract` 对缺少 PDF 渲染组件的环境返回结构化 `unsupported`。
- `build-package` 对扫描 PDF 自动调用 OCR，成功后将识别文本写入 `redacted_text_blocks`。
- 上传包文件清单记录 `ocr_status`、`ocr_engine`、`ocr_confidence` 和 `ocr_pages_processed`。
- RapidOCR 离线安装计划、商业包 OCR 安装脚本和 OCR requirements 均纳入 `pypdfium2`。

## 真实文件验收

测试文件:

- `C:\Users\spook\Desktop\wipo_pub_946.pdf`
- `C:\Users\spook\Desktop\wipo-2024 绘制创新图景专利和可持续发展目标.pdf`
- `C:\Users\spook\Desktop\项目实施计划及报价表-科技成果转化模式及激励机制研究（质押融资与作价入股专题）.xlsx`
- `C:\Users\spook\Desktop\附件1：科技成果转化模式及激励机制研究（质押融资与作价入股专题）-技术服务委托函-6至9月16万版-v2.docx`

结果:

- 两个 PDF 均 `parser_status=ok`、`ocr_status=ok`、`ocr_engine=rapidocr`。
- 限制 PDF 前 2 页 OCR 时，两个 PDF 置信度均约 0.99。
- 四文件上传包结果为 `source_file_count=4`、`redacted_text_blocks=44`、`field_mapping_stats.total_fields=4`。
- 上传包不包含原始文件和本地映射表。
- 最终 runtime-ready 压缩包为 `products\document_redaction_assistant\.release_demo_m19_runtime_ready\document_redaction_assistant_install_0.19.0-m19_runtime_ready.zip`，大小 `407,243,624` 字节。

## 当前边界

- 大型 PDF 默认受 `DRA_OCR_MAX_PAGES` 控制，避免客户普通办公电脑长时间无响应。
- 本次样例没有可识别技术指标，`trl_factors_preserved=False`，评审报告会提示 TRL 判断可能降级。
- Windows 深路径仍可能影响离线依赖安装，客户侧建议解压到 `D:\DRA` 或类似短路径。

## 验证

- 文档安全脱敏助手 M1-M19 自动化测试: `49/49 OK`
- 沙箱导入 API 测试: `4/4 OK`
- 最终 zip 解压包: 商业包校验、OCR 启用校验、样例自检、真实 PDF OCR、四文件入包验收均通过。

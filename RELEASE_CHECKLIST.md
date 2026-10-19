# 发布检查清单

## M1 原型发布门槛

- [x] 自动化测试通过。
- [x] DOCX、XLSX、文本型 PDF 可解析。
- [x] 上传包不包含原始文件内容中的真实项目名、单位名、合同编号、电话。
- [x] 本地映射表不进入上传包。
- [x] 金额字段输出区间化结果，不直接变成不可计算的空值。
- [x] 技术指标和验证信息保留，用于 TRL 分析。
- [x] 可用本地映射表还原脱敏报告。
- [x] README 命令可执行。

## 当前不发布为客户安装包

M1 只作为工程原型，不向客户直接发布安装包。客户试点前必须补齐:

- [ ] 桌面向导界面。
- [x] 人工复核候选清单和字段策略决策。
- [ ] 映射表加密。
- [ ] 操作手册。
- [x] 样例数据包。

## M2 试点能力门槛

- [x] 可生成复核候选清单。
- [x] 可加载客户词库。
- [x] 可按复核决策保留、假名化、区间化或强脱敏字段。
- [x] 金额强脱敏时生成效益分析降级提示。
- [x] 可生成本地还原预演。
- [x] 可生成本地 HTML 复核页。

## M3 真实试点准备门槛

- [x] 可加密本地映射表，并删除明文映射表。
- [x] 错误口令无法解密映射表。
- [x] 疑似扫描 PDF 标记为 `ocr_required`，不静默上传伪文本。
- [x] XLSX 行列和单元格引用进入上传包结构。
- [x] 可生成 `sandbox_import_package.json`。
- [x] 多项目目录可批量生成独立脱敏包。
- [x] HTML 复核页可导出复核决策 JSON。

## M4 客户试点准备门槛

- [x] OCR 质量接口能阻断 `ocr_required` 文件。
- [x] 本地复核页保留可导出的决策 JSON。
- [x] 可生成客户试点包。
- [x] 试点包包含操作说明、安全边界、验收清单和样例数据。
- [x] STPE-AI 后端沙箱导入校验拒绝本地映射表上传。
- [x] STPE-AI 后端沙箱导入校验拒绝原始文件上传。

## 端到端验收

- [x] 批量样例项目可生成脱敏上传包。
- [x] 上传包通过 STPE-AI 沙箱导入 payload 校验。
- [x] 明文本地映射表在加密后删除。
- [x] 加密映射表不包含原始敏感值。
- [x] 解密后的本地映射表可还原脱敏内容。
- [x] 上传包不含原始项目名、单位名、合同编号、手机号和真实金额。
- [x] 脱敏包保留 `10kV`、`≤1%`、`30天` 等 TRL 判别信息。

## M5 试点闭环门槛

- [x] 沙箱导入包可写入脱敏项目记录。
- [x] 沙箱导入包可写入脱敏文件记录。
- [x] 写入记录不包含原始项目名。
- [x] OCR 状态接口可在无 OCR 环境下稳定返回。
- [x] 可生成静态桌面壳入口。
- [x] 静态桌面壳包含导入文件、字段复核、生成上传包、报告还原四步。

## M6 OCR 与产品组件门槛

- [x] OCR 适配器支持注入本地 OCR 引擎并返回识别文本、置信度和引擎名。
- [x] 无 OCR 引擎环境稳定返回不可用状态，不阻断非扫描件处理。
- [x] 本地产品服务提供 `/ocr-status`。
- [x] 本地产品服务提供 `/build-package`，可生成脱敏上传包、复核工作区和沙箱导入包。
- [x] 桌面壳可绑定本地服务 URL。
- [x] 桌面壳包含本地服务检测、OCR 检查和上传包生成接口调用。

## M7 可测试安装包门槛

- [x] 可生成安装包目录和 zip 包。
- [x] 安装包包含 `START_HERE.md` 和 `install_manifest.json`。
- [x] 安装包包含 `app\run_cli.bat`、`app\start_local_service.bat` 和 `app\run_sample_self_test.bat`。
- [x] 安装包包含产品源码、桌面壳、样例项目数据和发布说明。
- [x] 安装包不预置本地映射表明文。
- [x] 安装包目录内运行 `app\run_sample_self_test.bat` 可生成批处理脱敏输出并返回 OCR 状态。

## M8 安装就绪门槛

- [x] 可生成 `generated\runtime_report.json`。
- [x] 安装包包含 `app\install_local.bat`。
- [x] 安装包包含 `app\check_runtime.bat`。
- [x] 运行预检覆盖 Python 版本、源码包导入、写入权限、OCR 适配器和规则包清单。
- [x] 安装包包含 `app\rules\rules_manifest.json`。
- [x] 安装包包含 `app\rules\ocr_plugin_manifest.json`。
- [x] zip 解压后的安装包可运行安装预检和样例自检。

## M9 离线运行时与本地授权门槛（本地授权部分已于 0.27.0 移除）

- [x] 可生成 `app\license\local_license.json`（0.27.0 起不再生成，安装包已移除该文件）。
- [x] 可校验有效授权与过期授权（0.27.0 起不再校验）。
- [x] 安装包包含 `app\activate_local_license.bat`（0.27.0 起仅输出停用提示）。
- [x] 安装包包含 `app\runtime\runtime_manifest.json`。
- [x] 安装包包含 `app\ocr_engines\ocr_engine_manifest.json`。
- [x] 规则包包含 `app\rules\rules_update_manifest.json`。
- [x] `app\install_local.bat` 执行运行预检（0.27.0 起不再做本地授权校验）。
- [x] zip 解压后的安装包可运行安装预检和样例自检。

## M10 OCR 适配与运行时槽位门槛

- [x] 加密映射表往返测试不再触发 `pbkdf2_hmac()` 弃用告警。
- [x] OCR 适配器支持 RapidOCR 懒加载调用路径。
- [x] OCR 适配器支持 PaddleOCR 懒加载调用路径。
- [x] 安装包包含 `app\runtime\run_with_embedded_python.bat`。
- [x] 安装包包含 `app\ocr_engines\OCR_SETUP.md`。
- [x] 嵌入式运行时槽位在未内置 Python 时可回退到 `run_cli.bat`。
- [x] zip 解压后的安装包可运行安装预检和样例自检。

## M11 规则更新与依赖清单门槛

- [x] 可校验合法规则更新包。
- [x] 可阻断破坏评估保真边界的规则更新。
- [x] 可应用合法规则更新包。
- [x] 规则更新支持 UTF-8 BOM JSON 输入。
- [x] 安装包包含 `app\apply_rules_update.bat`。
- [x] 安装包包含 `app\runtime\runtime_files_manifest.json`。
- [x] 安装包包含 `app\runtime\python\README_RUNTIME.txt`。
- [x] 安装包包含 `app\ocr_engines\requirements-ocr.txt`。
- [x] 安装包包含 `app\ocr_engines\ocr_files_manifest.json`。

## M12 离线运行时与评估触发门槛

- [x] 可将本地 Python 可执行文件落入 `runtime\python\python.exe`。
- [x] 落盘 Python 后可更新 `runtime_manifest.json` 和 `runtime_files_manifest.json`。
- [x] 可扫描本地 OCR wheelhouse 并生成 `ocr_wheelhouse_manifest.json`。
- [x] 安装包包含 `app\stage_python_runtime.bat`。
- [x] 安装包包含 `app\build_ocr_wheelhouse.bat`。
- [x] 沙箱导入后可触发注入式评估任务。
- [x] 评估触发结果不需要原始文件或本地映射表。

## M13 报告交付与本地还原门槛

- [x] 可生成脱敏评估报告。
- [x] 可生成报告交付清单。
- [x] 可用本地映射表生成还原预览。
- [x] 报告交付包不包含本地映射表。
- [x] 报告交付包不包含原始文件。
- [x] 后端沙箱导入结果包含 `report_summary`。
- [x] 安装包包含 `app\build_report_delivery_demo.bat`。
- [x] zip 解压后的安装包可运行报告交付演示。

## M14 安装器外壳与客户验收包门槛

- [x] 安装包包含 `setup.bat`。
- [x] 安装包包含 `uninstall.bat`。
- [x] 安装包包含 `installer_wizard\index.html`。
- [x] 安装包包含 `customer_acceptance\ACCEPTANCE_CHECKLIST.md`。
- [x] 安装包包含 `customer_acceptance\PILOT_SIGNOFF.md`。
- [x] 安装包包含 `install_records\INSTALL_RECORD_TEMPLATE.md`。
- [x] `setup.bat` 可执行安装预检并输出 `INSTALLER_SHELL_OK`。
- [x] zip 解压后的安装包可运行安装器外壳、样例自检和报告交付演示。

## M15 客户试点运行闭环门槛

- [x] 可生成客户试点问题台账。
- [x] 问题台账不记录原始文件路径、原文片段和本地映射内容。
- [x] 可校验 OCR wheelhouse 文件存在性、大小和 SHA256。
- [x] OCR wheelhouse 文件被篡改时校验失败。
- [x] 可生成生产沙箱联调配置。
- [x] 生产沙箱配置默认只允许脱敏包，不允许原始文件和本地映射表。
- [x] 生产沙箱配置校验可阻断明文密钥。
- [x] 安装包包含 `app\record_pilot_feedback.bat`。
- [x] 安装包包含 `app\validate_ocr_package.bat`。
- [x] 安装包包含 `app\build_production_sandbox_config.bat`。
- [x] 安装包包含 `customer_acceptance\PILOT_ISSUE_LEDGER_TEMPLATE.md`。

## M16 完整离线商业包门槛

- [x] 可生成商业离线安装包。
- [x] 可装配本地 Python 运行时目录。
- [x] 可装配 OCR wheelhouse 离线依赖目录。
- [x] 可装配 Office/WPS 转换组件目录。
- [x] 可生成 `commercial_release_manifest.json`。
- [x] 组件齐备时标记 `complete_offline`。
- [x] 组件缺失时标记 `staging_required`，并在校验中列出缺项。
- [x] 商业包包含 `app\validate_commercial_package.bat`。
- [x] 商业包包含 `app\start_offline_app.bat`。
- [x] 商业包清单不把未装配组件伪装为已内置。

## M17 离线 OCR 启用链路门槛

- [x] 可生成 `offline_ocr_install_plan.json`。
- [x] 可生成 `offline_ocr_env.bat`。
- [x] OCR 安装计划使用 `--no-index --find-links` 离线安装方式。
- [x] 可校验 OCR 启用标记是否存在。
- [x] 未完成安装时校验返回 `not_enabled`。
- [x] 商业包包含 `app\install_offline_ocr.bat`。
- [x] 商业包包含 `app\validate_offline_ocr.bat`。
- [x] 商业包清单包含离线 OCR 安装和校验脚本入口。

## M18 真实环境可运行包门槛

- [x] `run_cli.bat` 优先使用包内嵌入式 Python。
- [x] 商业包内置 Python 可执行 `python -m pip --version`。
- [x] 商业包可在短路径安装目录完成 RapidOCR 离线安装。
- [x] OCR 启用后 `ocr-status` 返回 `available`。
- [x] 商业包安装预检输出 `INSTALLER_SHELL_OK`。
- [x] 商业包样例自检输出 `SAMPLE_SELF_TEST_OK`。
- [x] 已生成 runtime-ready 压缩包。
- [x] 明确要求客户解压到短路径，规避 Windows 长路径限制。

## M19 真实 PDF OCR 主链路门槛

- [x] PDF OCR 先渲染为临时 PNG，再调用 RapidOCR/PaddleOCR。
- [x] 缺少 PDF 渲染组件时返回结构化 `unsupported`，不输出 Python 堆栈。
- [x] RapidOCR 离线安装计划包含 `pypdfium2`。
- [x] 商业包 `install_offline_ocr.bat` 安装 `rapidocr-onnxruntime pypdfium2`。
- [x] `build-package` 可将扫描 PDF OCR 结果纳入 `redacted_text_blocks`。
- [x] 上传包文件清单记录 OCR 状态、引擎、置信度和页数。
- [x] 已用桌面两个 WIPO PDF、一个 XLSX、一个 DOCX 完成真实应用测试。
- [x] 真实四文件测试中原始文件和本地映射表不进入上传包。

## M20 安装包验收脚本门槛

- [x] 安装包包含 `app\run_acceptance_smoke.bat`。
- [x] CLI 包含 `run-acceptance-smoke` 命令。
- [x] 验收脚本生成 `acceptance_report.json`。
- [x] 验收脚本生成 `ACCEPTANCE_REPORT.md`。
- [x] 商业包存在时必须执行商业包校验。
- [x] 从 `app` 目录以 `--app-dir "."` 执行时不误跳过商业包校验。
- [x] 验收脚本校验 OCR 状态可返回明确结果。
- [x] 验收脚本生成样例脱敏上传包。
- [x] 验收脚本校验原始文件和本地映射表不进入上传包。

## M24 客户自定义脱敏与评价影响门禁

- [x] 客户可通过 `review_decisions.json` 选择 `keep / redact`。
- [x] 客户可选择 `pseudonym / mask / range` 策略。
- [x] 脱敏包包含 `redaction_impact_summary`。
- [x] 技术指标和验证信息默认建议保留。
- [x] 强制脱敏高影响字段时标记评价降级风险。
- [x] 联系人姓名、`CN` 格式专利号和英文金额标签可识别。
- [x] 复核工作区展示评价影响提示。
- [x] 桌面壳提供客户自定义脱敏决策 JSON 输入框。
- [ ] 发布验证前必须使用 A1 修复后的源码重新生成 `.release_*` 目录；禁止使用现存含旧 `bool(review_decisions)` 快照的 `.release_*` 做发布验收。

## M26 外发边界门槛

- [x] 包版本记为 `0.26.0`。
- [x] 文档不再把身份证号、银行卡号、地址写成当前能力。
- [x] 隐藏通道报告只含类型和数量，不含通道原文。
- [x] 应替换字段仍留在脱敏文本中时，结果包标记为不可直接外发。
- [x] `external_release/` 与可还原上传包分开，且不含本地映射表。
- [x] 隐藏表、批注或无法安全回写的 PDF 不进入外发目录。
- [x] 技术指标默认保留。
- [x] 支线测试 160 项通过。
- [x] 本版本不承诺材料已经安全，也不替代法务、涉密或安全审查。
- [ ] 不把本版本发布为正式客户安装包；安装包仍按既有商业包装配流程另行验收。

## M26 外发安全修订（未发布）

上节的 160 项通过为历史测试集结果，不是安全外发结论。以下各项需针对当前修订重新取得证据，不沿用旧结果：

- [x] 缺失、未知、未扫描或失败的检查状态一律阻断；源文件变化不得沿用旧检查。
- [x] 每次使用独立批次目录，目录内容与本次清单严格一致，不删除用户文件或历史批次。
- [x] OOXML 属性、关系及跨片段文本纳入验证；无法处理的媒体和嵌入部件阻断。
- [x] 全部 PDF 外发暂时阻断；PDF 解析、OCR 与文本上传包保留。
- [x] 生成件存在、非空、可重新打开；异常不得按“无残留”处理。
- [x] Word 未修改片段的格式保真验证通过。
- [x] 安全反例测试及产品全量回归通过，并完成独立只读复审（全量 206、独立定向 58 项）。
- [x] 未进行新版本发布、旧标签移动或远端 Release 修改。

本节仅为有界修复验证，详情见 `docs/handoff/export_safety_20261016/verify_result.md`；不是客户安装包、UI、隐私或整体外发安全验收。

## 0.27.0 开源并集整合门槛

- [x] 去商业化：注册、试用额度、年度授权与商业文件配额能力全部移除。
- [x] `write-license`、`validate-license`、`registration-request`、`trial-status` 保留命令名并输出停用提示，不静默假成功。
- [x] 不读取、不修改、不删除用户已有的授权文件、映射表和原文。
- [x] 本地服务并集签名校验、来源限制、路径与大小校验、任务 TTL 与容量限制，错误消息不回泄内部细节。
- [x] 映射表 v2 加密写入（`local_mapping.private.enc`），兼容 v1 旧封装读取。
- [x] 外发安全修复并集（明确通过才放行、独立批次、隐藏通道阻断、PDF 外发暂停、Office 外发依赖阻断）。
- [x] 并集测试全绿（48 个测试文件，225 项通过 + 2 项跨仓集成跳过）——以本轮实测结果为准，不继承历史通过结论。
- [x] 产物矩阵验收（源码/wheel/便携包/离线包 × CLI/本地服务/桌面 × 映射 v1 读、v2 写）：52 通过、1 阻断（离线包完整性，本机无内置运行时源）、0 失败；源码形态另做浏览器黄金路径。详见 `docs/handoff/open_source_transition_20261019/04_product_acceptance_20261019.md`。
- [ ] 推送前匿名化复核：`docs/handoff/**` 等内部交接文档中的内部单位与路径引用按既定决定处理（默认匿名化）。
- [ ] 发布与 tag 另行授权；v0.26.0 与既有远端标签不得移动。

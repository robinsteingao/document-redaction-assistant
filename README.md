# 文档安全脱敏助手

文档安全脱敏助手是一款本地优先的敏感文档脱敏处理软件，可作为个人用户的独立脱敏工具，也可作为 STPE-AI 的客户侧本地安全入口，还可作为企业内部敏感材料流转、评审、归档和外发前的脱敏处理组件。

它的核心目标不是“替用户判断材料是否一定安全”，而是把原始材料、本地映射表和可外发/可上传的脱敏包分开管理，让用户在本地完成材料解析、敏感字段识别、人工复核、保真脱敏、上传包生成和必要时的本地还原。

## 一句话定位

**在文档离开本地电脑、进入评审系统、外部协作或企业流转前，先做一轮可复核、可追溯、尽量不破坏业务分析价值的脱敏处理。**

## 适用场景

### 1. 个人本地脱敏工具

适合个人在本机处理准备外发、分享或提交的材料：

- 简历、合同、报价单、证明材料、项目申报书、验收材料等文档中的姓名、电话、邮箱、地址、身份证号、银行卡号、合同编号等敏感信息。
- 在发送给同事、专家、外部顾问、AI 工具或公开平台前，先生成脱敏版本。
- 保留本地加密映射表，必要时可以在本机凭口令还原或对照复核。

### 2. STPE-AI 的本地安全入口

适合科技项目后评估场景，在材料上传 STPE-AI 前先进行本地安全处理：

- 对项目申报书、验收报告、经费材料、成果证明、知识产权材料、效益材料等进行本地解析和脱敏。
- 生成面向 STPE-AI 的脱敏上传包，避免原始文件和本地映射表进入评估系统。
- 尽量保留 TRL、效益分析、技术指标、验证阶段、成果证据等评估所需信息，降低“脱敏后无法评估”的风险。
- 输出脱敏影响提示，辅助用户判断哪些字段可以脱敏，哪些字段脱敏后会影响评估质量。

### 3. 企业敏感文档脱敏处理

适合企业内部作为敏感材料处理组件，用于评审、审计、知识管理、供应商协作、咨询交付或跨部门材料流转前的预处理：

- 支持批量处理项目目录，每个项目生成独立脱敏包和复核工作区。
- 支持客户词库和人工复核决策，便于企业根据自身规则扩展敏感字段。
- 支持离线 OCR、离线运行时、商业安装包、规则更新包和本地服务接口等产品化能力。
- 可作为企业内部“材料出域前检查”的一环，但不替代法务审查、安全审计或涉密审查。

## 核心能力概览

| 能力 | 说明 |
| --- | --- |
| 本地解析 | 支持 DOCX、XLSX、文本型 PDF、TXT、Markdown，并逐步补齐扫描 PDF OCR 路径。 |
| 敏感字段识别 | 识别项目名、单位、合同编号、电话、邮箱、专利号、软著号、金额、身份证号、银行卡号、地址等常见字段。 |
| 保真脱敏 | 身份类信息可假名化，金额可区间化，技术指标默认保留，尽量兼顾安全与业务分析价值。 |
| 人工复核 | 输出候选字段、默认策略、影响等级和本地 HTML 复核工作区，支持 `keep / redact` 决策。 |
| 本地映射 | 桌面壳和带口令命令会生成 `local_mapping.private.enc`，仅留在本地并凭客户口令还原，不进入上传包。 |
| 上传包生成 | 生成脱敏上传包、STPE-AI 沙箱导入包和结构化证据材料，不包含原始文件和本地映射表。 |
| OCR 接入 | 支持 RapidOCR / PaddleOCR 等本地 OCR 引擎接入；无 OCR 环境时稳定降级。 |
| 批处理 | 支持多项目目录批量生成脱敏包、复核工作区和批处理清单。 |
| 安装与商用准备 | 支持本地服务、桌面壳、安装包、商业离线包、运行时预检、规则更新和验收脚本。 |
| 开源发布预检 | 提供 `open-source-preflight`，检查发布范围内是否缺少边界文档、是否混入本地映射、密钥、release 快照等。 |

## 典型工作流

1. **本地准备材料**：把需要处理的文档放入本机目录。
2. **生成脱敏包**：运行 CLI 或桌面壳，解析文档并识别敏感字段。
3. **人工复核**：查看候选字段、脱敏策略和评价影响提示，必要时调整 `review_decisions.json`。
4. **生成可上传/可外发材料**：输出脱敏文本、结构化 JSON、复核报告和 STPE-AI 上传包。
5. **保留本地映射**：原始文件和映射表只留在本地，作为还原和审计依据。
6. **进入下游系统或协作流程**：将脱敏包上传 STPE-AI，或将脱敏材料提供给专家、同事、外部顾问或企业内部系统。

## 主要输出物

| 输出物 | 用途 | 是否应上传/外发 |
| --- | --- | --- |
| `redaction_upload_package.json` | 通用脱敏上传包 | 可在复核后上传/外发 |
| `sandbox_import_package.json` | STPE-AI 沙箱导入包 | 可用于 STPE-AI 测试导入 |
| `stpe_upload_package/` | STPE-AI 标准脱敏上传包目录 | 可在复核后上传 |
| `review_candidates.json` | 待复核字段清单 | 本地复核用，谨慎外发 |
| `review_workspace.html` | 本地复核页面 | 本地使用 |
| `redaction_review_report.md` | 脱敏影响说明 | 可作为复核记录 |
| `local_mapping.private.enc` | 原文与脱敏值加密映射 | 仅本地保存，不应上传；口令丢失后无法还原 |
| 原始文档 | 客户原始材料 | 仅本地保存，不应进入脱敏上传包 |

## 与 STPE-AI 的关系

STPE-AI 的正式定位是“科技项目成果转化就绪度评估与推进建议系统”。文档安全脱敏助手是其前置安全处理工具，负责在客户本地把原始材料整理为可评估、可复核、风险更低的脱敏输入。

它不改变 STPE-AI 的评估规则、TRL/readiness 口径或报告结论边界；也不替代专家判断、法务审查、真实性核验或组织审批。

## 使用边界

- 本工具不能保证所有敏感信息都被自动识别。
- OCR、规则识别和候选字段识别可能存在遗漏或误判。
- “评价影响门禁”不是“无隐私残留”证明。
- 企业正式使用前，应结合内部制度、数据分级分类、法务要求和安全审计要求进行配置和复核。
- 涉密材料、真实客户材料或受监管数据不得在未确认合规边界前上传到外部系统或公开仓库。

## 快速开始

> 说明：GitHub 仓库发布的是源码版，默认不内置 OCR 模型、Python 运行时、企业离线安装包或 `.release*` 快照。因此仓库体积较小是正常现象。扫描 PDF/图片 OCR 需要按 `docs/INSTALL_AND_OCR.md` 另行安装本地 OCR 依赖。

首次处理文件前，建议先生成本地注册申请。个人版注册费用按年度缴纳，当前为 **80 元/年**；生成注册申请后可先试用 **50 个文件**。超过试用额度后，软件会阻止继续生成脱敏包，并提示联系作者获取年度授权 `license.json`。

```powershell
python -m redaction_assistant.cli registration-request `
  --email user@example.com `
  --out .\registration

python -m redaction_assistant.cli trial-status --registration-dir .\registration
```

源码目录直接试用时，优先使用 `run_cli.bat`：

```powershell
.\run_cli.bat build-package `
  --project-alias-id demo-project `
  --registration-dir .\registration `
  --out .\out `
  .\examples\sample_project.txt
```

如果已安装为本地开发包：

```powershell
python -m redaction_assistant.cli build-package `
  --project-alias-id demo-project `
  --registration-dir .\registration `
  --out .\out `
  .\project.docx .\benefit.xlsx .\contract.pdf
```

开源发布前可运行预检：

```powershell
python -m redaction_assistant.cli open-source-preflight --root .
```

更多安装、运行环境和 OCR 依赖说明见：[`docs/INSTALL_AND_OCR.md`](docs/INSTALL_AND_OCR.md)。

下方 M1-M24.8 记录保留了从原型到产品化能力的演进过程，便于了解每一阶段新增了哪些功能。

## M1 边界

当前 M1 原型只做最小闭环:

- 支持 DOCX、XLSX、文本型 PDF、TXT、Markdown 的本地解析。
- 使用本地规则识别项目名、单位、合同编号、电话、邮箱、专利号、软著号和金额。
- 身份字段使用稳定假名化。
- 金额字段使用区间化保真，避免效益分析完全失去可计算依据。
- 技术指标默认保留，例如电压等级、误差、试运行时间、验证阶段。
- 生成 `redaction_upload_package.json`，不包含原始文件和本地映射表。
- 生成本地映射表；客户端发布包默认保存为 `local_mapping.private.enc`，仅留在客户本地并凭口令用于报告还原。
- 生成 `redaction_review_report.md`，提示脱敏对 TRL 和效益分析的影响。

## M2 增强

M2 增加试点可用能力:

- 生成 `review_candidates.json`，列出待复核字段、默认策略和保真值。
- 支持客户词库 `customer_dictionary.json`。
- 支持复核决策文件，允许单字段 `keep / redact`，并选择 `pseudonym / range / mask` 策略。
- 生成 `restore_preview.json`，展示脱敏版和本地还原版片段。
- 生成 `review_workspace.html`，用于本地查看字段复核、评估影响和还原预演。

## M3 增强

M3 增加真实试点准备能力:

- 映射表加密封装，支持加密、解密和批处理时自动加密。
- 扫描 PDF 预检，疑似图片型 PDF 标记为 `ocr_required`，不静默上传伪文本。
- XLSX 表格结构保留，记录 sheet、row、cell ref 和脱敏单元格内容。
- 多项目批处理，每个项目目录生成独立上传包和复核工作区。
- STPE-AI 沙箱导入包 `sandbox_import_package.json`。
- 本地 HTML 复核页支持导出 `review_decisions.json`。

## M4 增强

M4 增加客户试点准备能力:

- OCR 质量接口，阻断 `ocr_required` 文件上传。
- 后端沙箱导入校验 API：`POST /api/redaction-sandbox/import`。
- 客户试点包生成，包含操作说明、安全边界、验收清单和样例数据。
- 本地复核页继续作为轻量交互入口，可导出决策 JSON。

## M5 增强

M5 增加试点闭环能力:

- STPE-AI 沙箱导入可写入脱敏项目和脱敏文件记录。
- OCR 适配器状态命令 `ocr-status`。
- 静态桌面壳生成命令 `build-desktop-shell`。

## M6 增强

M6 增加 OCR 和产品组件接入能力:

- OCR 适配器支持注入本地 OCR 引擎，扫描件识别结果统一返回 `status / engine / text / confidence`。
- 无 OCR 引擎环境稳定返回 `unavailable`，不影响 DOCX、XLSX、文本型 PDF 处理。
- 新增本地产品服务 `serve-local`，提供 `/ocr-status` 和 `/build-package`。
- 静态桌面壳可绑定本地服务 URL，通过浏览器页面调用本地服务生成脱敏结果包。
- 新增 `ocr-extract` 命令，用于验证可选 OCR 引擎接入链路。

## M7 增强

M7 增加可测试安装包生成能力:

- 新增 `build-install-package` 命令，生成可解压目录包和 zip 包。
- 安装包内置 `START_HERE.md`、`install_manifest.json`、本地 CLI、服务启动脚本、样例自检脚本和桌面壳。
- 安装包样例自检可生成批处理脱敏输出并检查 OCR 状态。
- 当前仍为可测试安装包，不是正式 MSI/EXE 安装器。

## M8 增强

M8 增加安装就绪能力:

- 新增 `runtime-preflight` 命令，检查 Python 版本、源码导入、目录写入、OCR 适配器和规则包清单。
- 安装包新增 `app\install_local.bat` 和 `app\check_runtime.bat`。
- 安装包新增 `app\rules\rules_manifest.json`，明确评估保真脱敏规则包。
- 安装包新增 `app\rules\ocr_plugin_manifest.json`，明确 OCR 插件接入边界。
- 安装包自检会先生成 `generated\runtime_report.json`，再执行样例脱敏。

## M9 增强

M9 增加离线运行时与本地授权边界:

- 新增本地授权文件 `app\license\local_license.json`。
- 新增 `validate-license` 和 `write-license` 命令。
- 安装包新增 `app\activate_local_license.bat`，用于本地授权校验。
- 安装包新增 `app\runtime\runtime_manifest.json`，明确当前不内置 Python 运行时，后续可切换为正式离线运行时。
- 安装包新增 `app\ocr_engines\ocr_engine_manifest.json`，明确 OCR 引擎包接入槽位。
- 规则包新增 `rules_update_manifest.json`，约束规则更新可改与不可改边界。

## M10 增强

M10 增加真实 OCR 适配路径和离线运行时启动槽位:

- 加密派生改为本地 PBKDF2-HMAC-SHA256 兼容实现，消除当前环境中的 `pbkdf2_hmac()` 弃用告警。
- OCR 适配器支持 RapidOCR 和 PaddleOCR 的真实懒加载调用路径。
- `ocr-extract` 在设置 `DRA_OCR_ENGINE=rapidocr` 或 `DRA_OCR_ENGINE=paddleocr` 后可调用对应本地引擎。
- 安装包新增 `app\runtime\run_with_embedded_python.bat`，为后续内置 Python 运行时预留启动入口；当前未内置时回退到 `run_cli.bat`。
- 安装包新增 `app\ocr_engines\OCR_SETUP.md`，说明 OCR 引擎本地接入方法。

## M11 增强

M11 增加规则更新应用、OCR 依赖清单和运行时文件清单:

- 新增 `apply-rules-update` 和 `validate-rules-update` 命令。
- 安装包新增 `app\apply_rules_update.bat`。
- 规则更新支持 Windows 常见 UTF-8 BOM JSON，并会写回无 BOM 规范文件。
- 安装包新增 `app\runtime\python\README_RUNTIME.txt` 和 `app\runtime\runtime_files_manifest.json`。
- 安装包新增 `app\ocr_engines\requirements-ocr.txt` 和 `app\ocr_engines\ocr_files_manifest.json`。

## M12 增强

M12 增加离线运行时落盘、OCR wheelhouse 清单和沙箱评估触发:

- 新增 `stage-python-runtime` 命令，可将本地 Python 可执行文件落入 `app\runtime\python\python.exe`。
- 新增 `build-ocr-wheelhouse` 命令，可扫描本地 wheelhouse 并生成 `ocr_wheelhouse_manifest.json`。
- 安装包新增 `app\stage_python_runtime.bat` 和 `app\build_ocr_wheelhouse.bat`。
- 后端沙箱导入支持注入评估触发器，导入脱敏项目后可返回 `evaluation_result`。
- 评估触发仍只使用脱敏包和 `project_alias_id`，不接触原始文件或本地映射表。

## M13 增强

M13 增加报告交付与本地还原演示:

- 新增 `build-report-delivery` 命令，可生成脱敏评估报告、交付清单和本地还原预览。
- 安装包新增 `app\build_report_delivery_demo.bat`。
- 后端沙箱导入结果新增 `report_summary`，用于说明脱敏报告下载边界。
- 报告交付包不包含本地映射表和原始文件。
- 支持读取 Windows 常见 UTF-8 BOM JSON 评估结果和本地映射文件。

## M14 增强

M14 增加安装器外壳、图形化安装向导和客户验收包:

- 安装包新增 `setup.bat` 和 `uninstall.bat`。
- 安装包新增 `installer_wizard\index.html`。
- 安装包新增 `customer_acceptance\ACCEPTANCE_CHECKLIST.md`。
- 安装包新增 `customer_acceptance\PILOT_SIGNOFF.md`。
- 安装包新增 `install_records\INSTALL_RECORD_TEMPLATE.md`。
- 安装包新增 `installer_manifest.json`，记录安装器外壳入口。

## M15 增强

M15 增加客户试点运行闭环:

- 新增客户试点问题台账生成命令 `build-pilot-feedback-ledger`。
- 新增 OCR wheelhouse 完整性校验命令 `validate-ocr-wheelhouse`，校验文件存在性、大小和 SHA256。
- 新增生产沙箱配置生成与校验命令 `build-production-sandbox-config`、`validate-production-sandbox-config`。
- 安装包新增 `app\record_pilot_feedback.bat`。
- 安装包新增 `app\validate_ocr_package.bat`。
- 安装包新增 `app\build_production_sandbox_config.bat`。
- 客户验收包新增 `customer_acceptance\PILOT_ISSUE_LEDGER_TEMPLATE.md`。

## M16 增强

M16 将目标切换为完整离线商业安装包:

- 新增 `build-commercial-package` 命令，可装配本地 Python 运行时、OCR wheelhouse 和 Office/WPS 转换组件目录。
- 新增 `validate-commercial-package` 命令，校验商业离线包是否具备内置 Python、OCR 离线依赖和 Office 转换器。
- 新增 `commercial_release_manifest.json`，明确 `complete_offline` 或 `staging_required`。
- 商业包新增 `app\validate_commercial_package.bat`。
- 商业包新增 `app\start_offline_app.bat`，用于校验通过后启动本地服务。
- 未提供真实组件目录时，商业包会明确标记为 `staging_required`，不伪装为完整离线包。

## M17 增强

M17 增加离线 OCR 启用链路:

- 新增 `build-offline-ocr-plan` 命令，生成 OCR 离线安装计划和环境变量脚本。
- 新增 `validate-offline-ocr` 命令，校验 OCR 是否已完成离线安装启用。
- 新增 `mark-offline-ocr-installed` 命令，用于安装脚本完成后写入本地启用标记。
- 商业包新增 `app\install_offline_ocr.bat`。
- 商业包新增 `app\validate_offline_ocr.bat`。
- 商业包新增 `app\ocr_engines\offline_ocr_install_plan.json` 和 `offline_ocr_env.bat`。

## M18 增强

M18 形成真实环境可运行软件包:

- `run_cli.bat` 改为优先使用包内 `app\runtime\python\python.exe`，避免样例自检借用客户电脑系统 Python。
- 商业包装配 Python 运行时时保留 pip/setuptools 必要组件，支持离线依赖安装。
- OCR 默认启用路线切换为 RapidOCR，使用 `rapidocr-onnxruntime` 离线 wheelhouse。
- 已验证短路径安装目录下离线安装 OCR 后，`ocr-status` 返回 `available`。
- Windows 下建议解压到短路径，例如 `D:\DRA` 或 `D:\tmp\dra`，避免深目录触发长路径限制。

## M19 增强

M19 补齐真实 PDF OCR 主链路:

- PDF OCR 改为先用 `pypdfium2` 渲染临时 PNG，再调用 RapidOCR/PaddleOCR。
- `ocr-extract` 对 PDF 缺少渲染组件时返回结构化 `unsupported`，不输出 Python 堆栈。
- `build-package` 对扫描 PDF 自动调用可用 OCR，成功后将 OCR 文本纳入 `redacted_text_blocks`。
- 上传包文件清单记录 `ocr_status`、`ocr_engine`、`ocr_confidence` 和 `ocr_pages_processed`。
- RapidOCR 离线安装计划和商业包安装脚本同步安装 `pypdfium2`。
- 已使用两个 WIPO PDF、一个 XLSX 报价表和一个 DOCX 技术服务委托函完成真实应用测试。

## M20 增强

M20 固化安装包验收脚本和样例测试:

- 新增 `run-acceptance-smoke` 命令。
- 安装包新增 `app\run_acceptance_smoke.bat`。
- 验收自检生成 `generated\acceptance_smoke\acceptance_report.json`。
- 验收自检同步生成 `generated\acceptance_smoke\ACCEPTANCE_REPORT.md`。
- 检查商业包校验、运行入口、OCR 状态、样例脱敏包生成和上传边界。
- 从 `app` 目录执行时可正确识别安装包根目录。

## M21 增强

M21 面向内部小范围盲测准备:

- 安装包推荐入口为 `app\start_desktop_app.bat`。
- 启动入口会自动启动本地服务、等待服务就绪并打开操作界面。
- 用户无需单独启动后台服务、检查端口或理解本地服务接口。
- 桌面壳新增项目代号、输出目录、文件路径输入区和“生成脱敏包”按钮。
- 本地服务未连接时，界面会提示应运行的启动脚本。
- 新增内部测试反馈表 Markdown 和 CSV。

## M24 增强

M24 增加客户自定义脱敏与评价影响门禁：

- 客户可通过 `review_decisions.json` 选择候选字段 `keep / redact`，并选择 `pseudonym / mask / range` 策略。
- 脱敏包新增 `redaction_impact_summary`，提示脱敏选择对 TRL、效益、成果证据核验和转化就绪度的影响。
- 技术指标、验证信息等评价因子默认建议保留；如客户强制脱敏，门禁提示评价可能降级。
- 复核工作区展示影响等级和评价影响提示，桌面壳提供“自定义字段处理方式”输入框。
- 规则补齐联系人姓名、`CN` 格式专利号和英文金额标签识别。

## M24.2 增强

M24.2 新增投用初期客户体验增强能力：

- 复核页支持按钮选择“保留原样、遮盖隐藏、替换为假名、保留区间”，自动生成 `review_decisions.json`，不要求客户手写 JSON。
- 增加批量总览与预检/进度业务化分组，优先展示“可直接处理、需先转换、暂不支持、路径不存在”等摘要，再保留技术支持用原始详情。
- 桌面壳提供“生成技术支持包”入口。技术支持包不包含原文、本地加密映射表、加密口令或密钥，仅用于复制给技术支持定位环境、预检和任务状态问题。
- 客户端生成结果包时要求设置本地映射表加密口令，输出 `local_mapping.private.enc`，不保留明文映射表。
- 输出目录提示更明确，客户可按界面显示的“输出目录”查找结果文件。
- M25 愿景记录为 PaddleOCR 3.7 / PP-OCRv6、OCR 置信度复核、表格/版面结构化解析；该能力不属于 M24.2 交付范围。

## M24.7 增强

M24.7 新增开源前只读发布预检：

- 检查 `README.md`、`LICENSE`、`PRIVACY.md`、`COMMERCIAL.md`、`DISCLAIMER.md` 和开源发布指南是否存在。
- 检查 `.gitignore` 是否覆盖 `.release*`、`local_mapping.private*`、`trial_usage_*.json`、注册申请、`license.json` 和 `stpe_upload_package/` 等不应公开的本地输出。
- 扫描发布范围内疑似私有映射、release 快照、密钥文件和常见 secret 赋值痕迹。
- 预检只生成 JSON 结果，不删除、不移动、不重命名任何文件；正式开源仍需人工清单复核、法务审查和安全审计。

## M24.8 增强

M24.8 补齐轻注册与试用额度门禁：

- 个人社区版需先生成本地注册申请，注册申请不包含原始文档、本地映射表或脱敏正文。
- 个人版注册费用按年度缴纳，当前为 **80 元/年**。
- 注册后可先试用 **50 个文件**；超过额度后，`build-package` / `batch-build` / 本地服务生成包会阻止继续处理。
- 导入有效 `license.json` 后可继续使用授权范围内能力。
- 公开源码版不提供自助生成正式授权文件的入口，`write-license` 默认禁用，避免用户绕过注册授权流程。

## 命令行用法

源码目录直接试用时，优先使用 `run_cli.bat`，它会自动设置本地包路径:

```powershell
.\run_cli.bat build-package `
  --project-alias-id 2026-STPE-001 `
  --out .\out `
  .\examples\sample_project.txt
```

如果已经通过 `pip install -e .` 安装为本地开发包，也可以使用下面的 Python 模块命令。

```powershell
python -m redaction_assistant.cli build-package `
  --project-alias-id 2026-STPE-001 `
  --out .\out `
  .\project.docx .\benefit.xlsx .\contract.pdf
```

带客户词库和复核决策:

```powershell
python -m redaction_assistant.cli build-package `
  --project-alias-id 2026-STPE-001 `
  --customer-dictionary .\customer_dictionary.json `
  --review-decisions .\review_decisions.json `
  --out .\out `
  .\project.docx .\benefit.xlsx .\contract.pdf
```

开源前只读发布预检:

```powershell
python -m redaction_assistant.cli open-source-preflight --root .
python -m redaction_assistant.cli open-source-preflight --root . --output .\open_source_preflight_report.json
```

只生成复核候选工作区:

```powershell
python -m redaction_assistant.cli review-workspace `
  --project-alias-id 2026-STPE-001 `
  --customer-dictionary .\customer_dictionary.json `
  --out .\review `
  .\project.docx .\benefit.xlsx
```

多项目批处理:

```powershell
python -m redaction_assistant.cli batch-build `
  --input-root .\projects `
  --out .\out `
  --mapping-passphrase "local-secret"
```

映射表加密和解密:

```powershell
python -m redaction_assistant.cli encrypt-mapping `
  --input .\out\local_mapping.private.json `
  --output .\out\local_mapping.private.enc `
  --passphrase "local-secret"

python -m redaction_assistant.cli decrypt-mapping `
  --input .\out\local_mapping.private.enc `
  --output .\out\local_mapping.private.json `
  --passphrase "local-secret"
```

生成客户试点材料包:

```powershell
python -m redaction_assistant.cli build-trial-package `
  --out .\trial `
  --version 0.4.0-m4
```

生成静态桌面壳:

```powershell
python -m redaction_assistant.cli build-desktop-shell `
  --out .\desktop `
  --version 0.6.0-m6 `
  --service-url http://127.0.0.1:8765
```

检查 OCR 适配器状态:

```powershell
python -m redaction_assistant.cli ocr-status
```

通过 OCR 适配器抽取扫描件文本:

```powershell
python -m redaction_assistant.cli ocr-extract `
  --file .\scan.pdf
```

启动本地产品服务:

```powershell
python -m redaction_assistant.cli serve-local `
  --host 127.0.0.1 `
  --port 8765
```

生成可测试安装包:

```powershell
.\run_cli.bat build-install-package `
  --out .\release `
  --version 0.9.0-m9
```

生成后进入安装包目录，运行:

```powershell
.\app\install_local.bat
.\app\run_sample_self_test.bat
```

单独校验本地授权:

```powershell
.\app\activate_local_license.bat
```

通过离线运行时槽位启动命令:

```powershell
.\app\runtime\run_with_embedded_python.bat ocr-status
```

应用规则更新包:

```powershell
.\app\apply_rules_update.bat ..\sample_rule_update
```

落盘离线 Python 运行时:

```powershell
.\app\stage_python_runtime.bat ..\python.exe
```

登记 OCR 离线依赖包:

```powershell
.\app\build_ocr_wheelhouse.bat ..\wheelhouse
```

校验 OCR 离线依赖包:

```powershell
.\app\validate_ocr_package.bat
```

生成报告交付与本地还原演示:

```powershell
.\app\build_report_delivery_demo.bat
```

生成客户试点问题台账:

```powershell
.\app\record_pilot_feedback.bat
```

生成生产沙箱联调配置:

```powershell
.\app\build_production_sandbox_config.bat
```

运行安装器外壳:

```powershell
.\setup.bat
```

生成完整离线商业包:

```powershell
python -m redaction_assistant.cli build-commercial-package `
  --out .\commercial_release `
  --version 0.16.0-m16 `
  --python-runtime-dir .\runtime_sources\python `
  --ocr-wheelhouse-dir .\runtime_sources\ocr_wheelhouse `
  --office-runtime-dir .\runtime_sources\libreoffice
```

校验完整离线商业包:

```powershell
.\app\validate_commercial_package.bat
```

启动完整离线本地服务:

```powershell
.\app\start_offline_app.bat
```

安装离线 OCR 依赖:

```powershell
.\app\install_offline_ocr.bat
```

校验离线 OCR 是否启用:

```powershell
.\app\validate_offline_ocr.bat
```

运行安装包验收自检:

```powershell
.\app\run_acceptance_smoke.bat
```

启动产品操作界面:

```powershell
.\app\start_desktop_app.bat
```

M22 用户流程:

- 普通用户优先阅读包根目录《使用必读》.txt/.doc；其中已合并本地部署、操作方法、常见报错、复核选择文件和批量脱敏说明。
- 在界面中先填写项目代号和待处理文件或文件夹路径。
- 点击“预检文件”，确认可处理文件、待转换旧版 Office/WPS 文件和跳过文件。
- M23 起旧版 DOC/XLS/WPS 会先尝试本地转换，转换失败文件不会静默进入上传包。
- PDF 较多时先选择“快速预览”，确认链路和字段识别效果后再做完整处理。
- M24 起如粘贴自定义字段处理方式，系统只表示“客户提交过选择”；只有显式勾选“确认接受评价降级风险”时，才会在评价影响摘要中记录 `customer_confirmed=true`。
- 点击“开始生成脱敏结果包”，等待处理进度完成。
- 如任务长时间运行，可点击“取消当前任务”；失败任务可点击“重试失败任务”沿用原参数重跑。
- 以任务结果中的 `outputs.output_dir` 为准打开输出目录。相对输出目录会自动保存到用户文档输出根目录，避免安装目录无写入权限。
- 批量脱敏可直接填写文件夹路径或多行文件路径；多个项目建议分项目分别运行，避免映射表混用。

还原报告:

```powershell
python -m redaction_assistant.cli restore `
  --mapping .\out\local_mapping.private.json `
  --input .\redacted_report.md `
  --output .\restored_report.md
```

## 盲测人员快速上手

**不了解项目源码结构的测试人员，请直接阅读 `BLIND_TEST_QUICK_START.md`**。该文件是唯一入口，按顺序执行即可完成盲测。

## 后续版本

- M24: `.xls/.wps` 真实样本专项验证、真正的文件/文件夹选择入口、完整 OCR 的暂停/续跑/失败重试。
- M24 已完成客户自定义脱敏与评价影响门禁；`.xls/.wps` 真实样本专项验证仍等待样本副本后执行。

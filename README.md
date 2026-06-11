# 文档安全脱敏助手

文档安全脱敏助手是 STPE-AI 的客户侧本地安全入口，用于在客户本地完成项目材料解析、敏感字段识别、评估保真脱敏、脱敏上传包生成和报告本地还原。

## M1 边界

当前 M1 原型只做最小闭环:

- 支持 DOCX、XLSX、文本型 PDF、TXT、Markdown 的本地解析。
- 使用本地规则识别项目名、单位、合同编号、电话、邮箱、专利号、软著号和金额。
- 身份字段使用稳定假名化。
- 金额字段使用区间化保真，避免效益分析完全失去可计算依据。
- 技术指标默认保留，例如电压等级、误差、试运行时间、验证阶段。
- 生成 `redaction_upload_package.json`，不包含原始文件和本地映射表。
- 生成 `local_mapping.private.json`，仅留在客户本地，用于报告还原。
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

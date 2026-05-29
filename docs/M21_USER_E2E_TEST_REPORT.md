# M21 真实使用者视角端到端测试报告

> 测试日期：2026-05-25
> 测试对象：`document_redaction_assistant_install_0.21.0-m21_runtime_ready.zip`
> 测试口径：按普通用户拿到离线压缩包后的使用方式测试，不从源码启动，不手工启动后台服务，不手工检查端口作为操作前提。

## 1. 测试结论

M21 已解决“安装后点击入口不能进入工作状态”的核心启动问题：在 8765 端口清空后，执行 `app\start_desktop_app.bat` 能自动拉起本地服务，`/ocr-status` 返回 RapidOCR 可用，随后可通过本地服务生成脱敏上传包、映射表、复核工作区和沙箱导入包。

但本轮不能判定为“用户测试前完全通过”。原因是字段脱敏覆盖仍不完整：人员姓名未脱敏，专利号未脱敏，英文 PDF 中的金额和专利号未被识别为应脱敏字段；桌面壳虽然有最小交互表单，但仍依赖用户粘贴完整路径，距离“傻瓜式文件选择/拖拽”还有差距。

## 2. 测试环境与安装包

- 发布包路径：`products\document_redaction_assistant\.release_demo_m21_runtime_ready\document_redaction_assistant_install_0.21.0-m21_runtime_ready.zip`
- 发布包大小：`407,241,488` 字节
- 独立测试目录：`C:\tmp\dra_m21_user_e2e_20260525_151714`
- 解压后应用目录：`C:\tmp\dra_m21_user_e2e_20260525_151714\document_redaction_assistant_install_0.21.0-m21`
- 启动入口：`app\start_desktop_app.bat`
- 本地服务地址：`http://127.0.0.1:8765`

## 3. 测试样例

本轮准备了 4 类样例文件，模拟普通项目评审材料：

- `project_info_utf8.txt`：包含项目名称、承担单位、联系人、手机号、合同金额、技术指标、专利号。
- `service_letter_utf8.docx`：包含项目名称、承担单位、合同金额、技术指标。
- `quote_utf8.xlsx`：包含项目、单位、金额、联系人。
- `contract_scan_utf8.pdf`：模拟 PDF 文本流，包含英文项目描述、金额、电话、专利号。

关键敏感字段：

- 项目名称：`高效储能变流器示范项目`
- 单位：`北京华能智造科技有限公司`
- 联系人：`张三`
- 手机号：`13800138000`
- 金额：`320.50 万元`
- 专利号：`CN202410123456.7`
- 技术指标：`96.5%`、`6000 次`

## 4. 测试过程与方式

### 4.1 解压安装包

操作方式：从发布压缩包解压到短路径 `C:\tmp`，模拟客户电脑本地安装目录。

结果：解压成功，根目录包含 `app`、`docs`、`generated`、`installer_wizard`、`sample_data`、`START_HERE.md`、`setup.bat` 等文件。

### 4.2 冷启动入口测试

测试前先检查 8765 端口。首次发现端口已被旧 M18 测试服务占用：

```text
ProcessId: 27532
ExecutablePath: D:\tmp\m18\document_redaction_assistant_install_0.18.0-m18\app\runtime\python\python.exe
CommandLine: ... serve-local --host 127.0.0.1 --port 8765
```

停止旧服务后重新执行：

```bat
app\start_desktop_app.bat
```

结果：

```json
{
  "schema_version": "document_redaction_desktop_launch.v1",
  "status": "started",
  "service_url": "http://127.0.0.1:8765",
  "service_process_id": 17368
}
```

随后端口实际监听进程为 M21 包内 Python：

```text
PORT_AFTER=27172
ExecutablePath: C:\tmp\dra_m21_user_e2e_20260525_151714\document_redaction_assistant_install_0.21.0-m21\app\runtime\python\python.exe
CommandLine: ... -m redaction_assistant.cli serve-local --host 127.0.0.1 --port 8765
```

判断：冷启动自动拉起后台服务通过。需要注意的是，启动 JSON 中的 `service_process_id=17368` 与实际监听 Python 进程 `27172` 不一致，原因可能是启动器返回了 `cmd` 包装进程 PID，而非最终 Python 服务进程 PID。这不影响用户使用，但影响排障准确性。

### 4.3 OCR 状态测试

请求：

```http
GET http://127.0.0.1:8765/ocr-status
```

结果：

```json
{
  "success": true,
  "result": {
    "status": "available",
    "engine": "rapidocr",
    "rapidocr_available": true,
    "paddleocr_available": false,
    "required_for_text_pdf": false,
    "message": "OCR 引擎可用。"
  }
}
```

判断：离线 OCR 组件状态检查通过。

### 4.4 脱敏包生成测试

桌面壳前端调用的实际接口为：

```http
POST http://127.0.0.1:8765/build-package
```

本轮浏览器自动化环境禁止打开 `file://` 本地页面，并且阻止直接访问 `127.0.0.1:8765` 页面，因此未能完成机器自动点击桌面壳按钮。为验证同一业务链路，测试使用与前端 `runBuildPackage()` 相同的 `/build-package` 请求体执行。

请求要点：

```json
{
  "project_alias_id": "USER-E2E-M21-UTF8",
  "out": "...\generated\user_e2e_utf8_output",
  "files": [
    "...\user_samples_utf8\project_info_utf8.txt",
    "...\user_samples_utf8\service_letter_utf8.docx",
    "...\user_samples_utf8\quote_utf8.xlsx",
    "...\user_samples_utf8\contract_scan_utf8.pdf"
  ]
}
```

结果：

```json
{
  "success": true,
  "result": {
    "package": "...\redaction_upload_package.json",
    "mapping": "...\local_mapping.private.json",
    "review_report": "...\redaction_review_report.md",
    "review_candidates": "...\review_candidates.json",
    "restore_preview": "...\restore_preview.json",
    "review_html": "...\review_workspace.html",
    "sandbox_import": "...\sandbox_import_package.json"
  }
}
```

输出文件：

| 文件 | 大小 |
|---|---:|
| `redaction_upload_package.json` | 4,971 |
| `local_mapping.private.json` | 1,400 |
| `redaction_review_report.md` | 386 |
| `review_candidates.json` | 987 |
| `restore_preview.json` | 1,482 |
| `review_workspace.html` | 5,473 |
| `sandbox_import_package.json` | 4,632 |

### 4.5 自动化验收脚本

执行：

```bat
app\run_acceptance_smoke.bat
app\validate_offline_ocr.bat
```

结果：

- `run_acceptance_smoke.bat`：`status=passed`，`ACCEPTANCE_EXIT=0`
- `validate_offline_ocr.bat`：`status=enabled`，`OCR_VALIDATE_EXIT=0`

判断：包内自检与 OCR 启用校验通过。

## 5. 脱敏结果核查

上传包核心字段：

```json
{
  "schema_version": "stpe_redaction_upload.v1",
  "project_alias_id": "USER-E2E-M21-UTF8",
  "redaction_policy": {
    "mode": "local_mapping_not_uploaded",
    "original_files_uploaded": false,
    "mapping_uploaded": false
  },
  "analysis_preservation_flags": {
    "trl_factors_preserved": true,
    "benefit_factors_preserved": true,
    "stable_placeholders_used": true
  },
  "field_mapping_stats": {
    "total_fields": 4,
    "by_kind": {
      "amount": 1,
      "organization": 1,
      "phone": 1,
      "project_name": 1
    }
  }
}
```

已正确处理：

- 项目名称替换为 `项目A`
- 单位替换为 `单位A`
- 手机号替换为 `电话A`
- 中文金额替换为 `金额区间A（100万-500万元）`
- 原始文件不上传：`original_files_uploaded=false`
- 本地映射表不上传：`mapping_uploaded=false`
- 本地映射表可用于还原报告

未正确处理或需要明确产品策略：

- `张三` 未脱敏，上传包中仍可见。
- `CN202410123456.7` 未脱敏，上传包和沙箱导入包中仍可见。
- 技术指标 `96.5%`、`6000` 被保留。该项不一定是错误，因为技术成熟度分析需要保留技术指标；但界面应向用户说明“技术指标通常建议保留，否则会影响评审判断”。
- PDF 英文文本中的 `Amount: 320.50`、`Patent: CN202410123456.7` 未脱敏，说明当前字段识别主要偏中文规则，对英文/混合文本覆盖不足。

## 6. 使用者视角反思

从真实使用者角度看，M21 最大进步是“能点一个入口进入工作状态”，这已经解决上一轮盲测中最致命的问题；用户不需要理解本地服务、端口和后台窗口。

但当前仍更像“内部测试版”，还不是低培训成本的客户版。主要障碍有三个：

1. 文件输入仍要求粘贴完整路径。普通客户不会稳定提供完整路径，下一步必须提供“选择文件/选择文件夹/拖拽导入”。
2. 字段选择还没有产品化。用户看不到“项目名称、单位、姓名、电话、金额、专利、技术指标”等字段开关，也不能理解哪些字段建议保留、哪些字段必须脱敏。
3. 脱敏覆盖存在实际风险。姓名和专利号泄露会削弱“安全脱敏助手”的可信度；英文 PDF 金额/专利未识别会影响跨来源材料处理。

## 7. 当前验收判断

| 检查项 | 结果 | 判断 |
|---|---|---|
| 发布包解压 | 通过 | 可在独立目录使用 |
| 一键启动入口 | 通过 | 冷启动可自动拉起本地服务 |
| OCR 状态 | 通过 | RapidOCR 可用 |
| 脱敏包生成 | 通过 | TXT/DOCX/XLSX/PDF 可生成上传包 |
| 原始文件不上链 | 通过 | 上传包只含文本块、清单和结构化字段 |
| 本地映射不上传 | 通过 | 映射表独立保存在本地 |
| 反向还原预览 | 通过 | `restore_preview.json` 可还原 |
| 字段脱敏完整性 | 未通过 | 姓名、专利号、英文 PDF 金额/专利存在泄露 |
| 界面易用性 | 部分通过 | 有最小表单，但缺少文件选择与字段开关 |
| 浏览器自动点击验收 | 未完成 | 测试工具阻止 `file://` 与 `127.0.0.1` 页面访问 |

## 8. 后续建议

M22 不应继续扩大包装能力，而应优先修正真实用户入口和字段风险：

1. 桌面壳增加文件选择、文件夹选择和拖拽导入，避免粘贴完整路径。
2. 增加字段复核页，至少支持项目名称、单位、姓名、电话、金额、专利号、技术指标的开关和建议策略。
3. 扩展字段识别规则：姓名、专利号、英文金额、英文 phone/patent/amount 场景。
4. 修正启动器返回 PID，使日志中的服务进程与真实监听进程一致。
5. 将“技术指标建议保留、金额可转区间、合同金额会影响效益分析”写入界面引导，而不是只放在说明文档。

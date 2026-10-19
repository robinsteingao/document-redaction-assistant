# 安装、运行环境与 OCR 依赖说明

本文说明 GitHub 源码版如何安装，以及为什么仓库本身不内置 OCR 模型、Python 运行时和离线组件包。

## 1. GitHub 源码版包含什么

当前 GitHub 仓库发布的是**源码版**，主要包含：

- 脱敏助手源码 `src/`
- 测试用例 `tests/`
- 示例文件 `examples/`
- README、许可声明、隐私、免责声明和开源发布检查文档
- CLI、桌面壳、安装包生成、OCR 接入、离线包装配等代码能力

源码版不直接包含：

- 内置 Python 运行时
- OCR 模型文件
- PaddleOCR / RapidOCR / ONNXRuntime wheelhouse 离线依赖包
- 已生成的 `.release*` 安装包快照
- 真实客户样本、原始材料、本地映射表或旧版授权文件

这些内容体积较大，且可能包含平台相关二进制文件或本地测试快照，不适合直接放入公开源码仓库。

## 2. 基础安装

建议使用 Python 3.10+。

```powershell
git clone https://github.com/robinsteingao/document-redaction-assistant.git
cd document-redaction-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

基础源码版依赖较轻：`pypdf`、`defusedxml`、`cryptography` 为必装核心依赖，其余主要使用 Python 标准库。非扫描件的 TXT、Markdown、文本型 PDF、DOCX、XLSX 等基础处理可直接使用。

### 便携包（解压即用形态）的核心依赖

便携包同样需要本机 Python 3.10–3.13。构建时若提供核心依赖 wheelhouse（`DRA_CORE_WHEELHOUSE` 或 `vendor/core_wheels`），包内会携带 `app\wheels`、`app\requirements.txt` 与 `app\install_core_deps.bat`：

```powershell
# 首次使用：优先离线安装 app\wheels，离线失败才回退联网 pip
.\app\install_core_deps.bat
```

`app\run_cli.bat` 在核心依赖缺失时会明确报错并指向该脚本，不会静默失败。wheel 形态（`pip install document_redaction_assistant-0.27.0-py3-none-any.whl`）同样需要 Python，并按 PyPI 安装核心依赖；无法联网时请改用便携包或自行提供 wheelhouse。

### Office 外发副本的额外校验依赖（工作分支安全修订）

基础解析和生成脱敏文本包不等于原格式外发副本。修订后的 DOCX/XLSX 外发回写、命名空间保留和重新打开校验依赖 `lxml`、`python-docx` 与 `openpyxl`：

```powershell
python -m pip install -r requirements-external-release.txt
# 或已安装源码包时：
python -m pip install -e ".[external-release]"
```

缺少这些依赖时，Office 外发文件会被阻断，而不是跳过校验后导出；文本上传包流程保留。企业离线环境须在受控 wheelhouse 中准备这些依赖及其传递依赖，不允许运行时自动联网下载。

运行完整产品测试时使用：

```powershell
python -m pip install -e ".[test]"
python -B -m pytest tests -q -p no:cacheprovider
```

**本轮暂时阻断所有 PDF 外发副本**。安装 OCR、渲染或上述 Office 校验依赖不会重新启用 PDF 外发；PDF 解析、OCR 和脱敏文本包仍可按原流程运行。

```powershell
python -m redaction_assistant.cli ocr-status
python -m redaction_assistant.cli build-package `
  --project-alias-id demo-project `
  --out .\out `
  .\examples\sample_project.txt
```

也可以使用仓库内的批处理入口：

```powershell
.\run_cli.bat build-package `
  --project-alias-id demo-project `
  --out .\out `
  .\examples\sample_project.txt
```

## 3. 启用 RapidOCR（推荐）

如需处理扫描 PDF 或图片 OCR，推荐优先使用 RapidOCR 路线：

```powershell
python -m pip install -r requirements-ocr-rapidocr.txt
$env:DRA_OCR_ENGINE="rapidocr"
python -m redaction_assistant.cli ocr-status
python -m redaction_assistant.cli ocr-extract --file .\scan.pdf
```

说明：

- `rapidocr-onnxruntime` 用于本地 OCR 识别。
- `pypdfium2` 用于将扫描 PDF 页面渲染为图片再识别。
- `Pillow` 用于图片处理。
- OCR 全程在本地执行，低置信结果仍需人工复核。

## 4. 启用 PaddleOCR（可选）

PaddleOCR 体积更大，依赖也更重，建议只在确有需要时安装：

```powershell
python -m pip install -r requirements-ocr-paddle.txt
$env:DRA_OCR_ENGINE="paddleocr"
python -m redaction_assistant.cli ocr-status
python -m redaction_assistant.cli ocr-extract --file .\scan.pdf
```

如果 PaddlePaddle 安装失败，请参考 PaddleOCR 官方说明选择与你的操作系统、Python 版本和 CPU/GPU 环境匹配的安装命令。

## 5. 离线/企业环境如何处理 OCR 依赖

企业内网或无公网环境不建议在公开仓库中直接提交 wheelhouse。推荐流程：

1. 在可联网的同类环境中下载依赖 wheel。
2. 将 wheel 放入企业内部制品库或离线介质。
3. 使用本项目的 `build-ocr-wheelhouse`、`build-offline-ocr-plan`、`mark-offline-ocr-installed` 等命令生成本地安装计划和校验清单。
4. 在客户内网机器上通过 `--no-index --find-links` 离线安装。

示例：

```powershell
python -m redaction_assistant.cli build-ocr-wheelhouse `
  --wheelhouse-dir .\wheelhouse `
  --out .\ocr_bundle

python -m redaction_assistant.cli build-offline-ocr-plan `
  --app-dir .\app `
  --engine rapidocr
```

## 6. 为什么 GitHub 仓库不到几 MB

这是预期结果。公开仓库只放源码、文档、测试和示例，不放：

- 大体积 OCR 模型和运行库
- 内置 Python 运行时
- 企业离线组件安装包
- 本地 release 快照
- 真实样本和客户材料

这样的好处是：仓库更干净、可审查、可复现，也避免把本地构建产物或敏感材料误公开。

如果需要“开箱即用”的企业离线包，应在受控环境中单独构建 release 包，而不是把所有二进制依赖直接提交到 GitHub。

## 7. 安全边界

- OCR 结果不等于最终脱敏结果，必须人工复核。
- 评价影响门禁不是“无隐私残留”证明。
- 原始文件和 `local_mapping.private.*` 应保留在本地，不应上传到公开仓库。
- 企业正式使用前应结合自身数据分级分类、法务要求和安全审计要求进行配置。

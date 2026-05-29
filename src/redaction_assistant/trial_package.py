from __future__ import annotations

import json
import shutil
from pathlib import Path


def build_trial_package(output_root: Path | str, *, version: str) -> Path:
    root = Path(output_root) / f"document_redaction_assistant_trial_{version}"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    sample_alpha = root / "sample_data" / "project_alpha"
    sample_beta = root / "sample_data" / "project_beta"
    sample_alpha.mkdir(parents=True, exist_ok=True)
    sample_beta.mkdir(parents=True, exist_ok=True)

    _write(root / "START_HERE.md", _start_here(version))
    _write(root / "USER_GUIDE.md", _user_guide())
    _write(root / "SECURITY_BOUNDARY.md", _security_boundary())
    _write(root / "PILOT_ACCEPTANCE_CHECKLIST.md", _acceptance_checklist())
    _write(sample_alpha / "input.txt", "项目名称：配网智能监测项目。\n合同金额：350万元。\n技术指标：10kV线路故障定位误差≤1%，现场试运行30天。\n")
    _write(sample_beta / "input.txt", "项目名称：变电站辅助系统项目。\n合同金额：80万元。\n技术指标：现场验证完成。\n")

    manifest = {
        "schema_version": "document_redaction_trial_manifest.v1",
        "version": version,
        "customer_installation_package": False,
        "entrypoint": "START_HERE.md",
        "required_review": [
            "本地映射表不得上传",
            "扫描件需 OCR 后再上传",
            "金额强脱敏会降低效益分析可信度",
        ],
    }
    _write(root / "trial_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return root


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _start_here(version: str) -> str:
    return f"""# 文档安全脱敏助手试点包

版本: {version}

本试点包用于验证客户侧本地脱敏、字段复核、上传包生成和报告还原流程。当前不是完整安装包。

推荐顺序:

1. 阅读 `SECURITY_BOUNDARY.md`。
2. 使用 `sample_data` 运行批处理。
3. 打开生成的 `review_workspace.html` 复核字段。
4. 上传 `sandbox_import_package.json` 到 STPE-AI 沙箱接口。
"""


def _user_guide() -> str:
    return """# 用户操作说明

核心流程:

`选择文件 -> 字段复核 -> 生成脱敏包 -> 上传沙箱 -> 本地还原`

默认策略使用评估保真脱敏。项目名、单位、合同编号等身份字段会假名化；金额保留区间；技术指标和验证信息保留。
"""


def _security_boundary() -> str:
    return """# 安全边界说明

- 原始文件不上传。
- 本地映射表不上传。
- 映射表应加密保存。
- 扫描 PDF 在未 OCR 前不得进入正式上传包。
- 外部 AI 不得接触原始项目材料。
"""


def _acceptance_checklist() -> str:
    return """# 试点验收清单

- [ ] 上传包不含原始项目名、单位名、合同编号、手机号。
- [ ] 本地映射表可还原报告。
- [ ] 金额字段未被完全抹除。
- [ ] 技术指标和验证阶段保留。
- [ ] 扫描 PDF 能被标记为需要 OCR。
"""

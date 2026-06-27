from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.user_summary import build_batch_job_summary, build_input_plan_summary


def test_input_plan_summary_groups_customer_actions():
    plan = {
        "processable_count": 2,
        "convertible_count": 1,
        "unsupported_count": 1,
        "skipped_count": 3,
        "missing_count": 1,
        "recommended_ocr_modes": ["quick", "full"],
        "processable_files": ["a.docx", "b.txt"],
        "convertible_files": [{"path": "old.xls", "reason": "office_conversion_required"}],
        "unsupported_files": [{"path": "archive.zip", "reason": "unsupported_extension"}],
        "skipped_files": [{"path": "Thumbs.db"}, {"path": "copy_manifest.json"}, {"path": "~$tmp.docx"}],
        "missing_paths": ["D:/missing"],
    }

    summary = build_input_plan_summary(plan)

    assert summary["status"] == "ready_with_warnings"
    assert summary["counts"]["可直接处理"] == 2
    assert summary["counts"]["需先转换"] == 1
    assert summary["counts"]["暂不支持"] == 1
    assert summary["counts"]["跳过文件"] == 3
    assert summary["counts"]["路径不存在"] == 1
    assert "旧版 Office/WPS 文件会先尝试本地转换" in "\n".join(summary["next_actions"])
    assert "archive.zip" in summary["groups"]["暂不支持"][0]["path"]


def test_batch_job_summary_never_requires_raw_json_to_understand_status():
    job = {
        "status": "completed",
        "progress": {"current": 2, "total": 2, "file_name": "input.txt"},
        "outputs": {"output_dir": "D:/out", "package": "D:/out/redaction_upload_package.json"},
        "conversion_report": {"converted_count": 1, "failed_count": 0},
        "error": None,
    }

    summary = build_batch_job_summary(job)

    assert summary["状态"] == "已完成"
    assert summary["进度"] == "2/2"
    assert summary["当前文件"] == "input.txt"
    assert summary["输出目录"] == "D:/out"
    assert summary["转换结果"] == "成功转换 1 个，失败 0 个"
    assert summary["错误提示"] == "无"

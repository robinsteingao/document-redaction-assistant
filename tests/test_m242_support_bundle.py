from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.local_service import handle_request
from redaction_assistant.support_bundle import build_support_bundle


def test_support_bundle_excludes_original_text_and_mapping_items():
    plan = {"processable_count": 1, "by_extension": {".txt": 1}, "processable_files": ["D:/secret/input.txt"]}
    job = {
        "status": "failed",
        "error": "ValueError: example",
        "outputs": {"mapping": "D:/out/local_mapping.private.json", "package": "D:/out/redaction_upload_package.json"},
        "payload": {"review_decisions": {"abc": {"action": "keep"}}},
        "redacted_text_blocks": [{"text": "原文不应出现"}],
        "mapping": {"items": [{"original": "张三"}]},
    }

    bundle = build_support_bundle(plan, job, version="M24.2-test")
    text = str(bundle)

    assert bundle["version"] == "M24.2-test"
    assert "原文不应出现" not in text
    assert "张三" not in text
    assert "local_mapping.private.json" not in text
    assert bundle["job_summary"]["状态"] == "失败"


def test_support_bundle_excludes_local_output_paths():
    job = {
        "status": "completed",
        "outputs": {
            "output_dir": "D:/customer/private/output",
            "mapping": "D:/customer/private/output/local_mapping.private.json",
        },
        "requested_output_dir": "D:/customer/private/requested",
        "conversion_report": {"workspace": "D:/customer/private/conversion", "converted_count": 1},
    }

    bundle = build_support_bundle({"processable_count": 1}, job)
    text = str(bundle)

    assert "D:/customer/private" not in text
    assert "local_mapping.private.json" not in text


def test_support_bundle_sanitizes_error_paths_and_secret_like_tokens():
    job = {
        "status": "failed",
        "error": "PermissionError: D:/customer/private/output/local_mapping.private.json token=sk-secret-123456",
    }

    bundle = build_support_bundle({"processable_count": 0}, job)
    text = str(bundle)

    assert "D:/customer/private" not in text
    assert "local_mapping.private.json" not in text
    assert "sk-secret-123456" not in text
    assert bundle["job_summary"]["错误提示"].startswith("PermissionError")


def test_local_service_returns_support_bundle_without_files_required():
    response = handle_request({"action": "support_bundle", "plan": {"processable_count": 0}, "job": {"status": "queued"}})

    assert response["success"] is True
    assert response["result"]["schema_version"] == "document_redaction_support_bundle.v1"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

"""P2-3 / P2-4: Tests for exception desensitization and _JOBS TTL cleanup."""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant import local_service
from redaction_assistant.local_service import (
    MAX_JOBS,
    _JOBS,
    _JOBS_LOCK,
    _cleanup_expired_jobs,
    handle_request,
)


def test_handle_request_value_error_returns_message():
    """ValueError should still return its message (user-facing validation)."""
    result = handle_request({"action": "plan_inputs", "input_paths": []})
    assert result["success"] is False
    assert "input_paths are required" in result["error"]


def test_handle_request_internal_error_returns_generic_message():
    """Non-ValueError exceptions should return a generic message, not the raw exception."""
    original = local_service.collect_user_inputs
    def boom(*args, **kwargs):
        raise RuntimeError("secret internal path: C:\\Users\\admin\\secret\\file.txt")
    local_service.collect_user_inputs = boom
    try:
        result = handle_request({
            "action": "plan_inputs",
            "input_paths": [__file__],
        })
    finally:
        local_service.collect_user_inputs = original
    assert result["success"] is False
    assert "secret" not in result["error"]
    assert "RuntimeError" not in result["error"]
    assert "处理失败" in result["error"] or "日志" in result["error"]


def test_cleanup_expired_jobs_removes_old_terminal_jobs():
    """Jobs older than TTL in terminal state should be removed."""
    _JOBS.clear()
    old_time = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    with _JOBS_LOCK:
        _JOBS["old-job"] = {
            "job_id": "old-job",
            "status": "completed",
            "completed_at": old_time,
        }
        _JOBS["fresh-job"] = {
            "job_id": "fresh-job",
            "status": "completed",
            "completed_at": datetime.now().isoformat(timespec="seconds"),
        }
        _JOBS["running-job"] = {
            "job_id": "running-job",
            "status": "running",
            "completed_at": old_time,
        }
    with _JOBS_LOCK:
        _cleanup_expired_jobs()
    assert "old-job" not in _JOBS
    assert "fresh-job" in _JOBS
    assert "running-job" in _JOBS
    _JOBS.clear()


def test_start_build_job_rejects_when_at_capacity(monkeypatch):
    """When _JOBS is at MAX_JOBS, new jobs should be rejected."""
    _JOBS.clear()
    with _JOBS_LOCK:
        for i in range(MAX_JOBS):
            _JOBS[f"job-{i}"] = {
                "job_id": f"job-{i}",
                "status": "completed",
                "completed_at": datetime.now().isoformat(timespec="seconds"),
            }
    # All jobs are fresh (just created), so cleanup won't remove them
    result = handle_request({
        "action": "start_build_package",
        "input_paths": [__file__],
        "out": ".",
        "project_alias_id": "test",
    })
    assert result["success"] is False
    assert "繁忙" in result["error"]
    _JOBS.clear()


def test_start_build_job_rechecks_capacity_before_enqueue(monkeypatch):
    """If capacity fills after validation but before enqueue, the job is still rejected."""
    _JOBS.clear()

    def fill_jobs(_paths):
        with _JOBS_LOCK:
            for i in range(MAX_JOBS):
                _JOBS[f"late-job-{i}"] = {
                    "job_id": f"late-job-{i}",
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(timespec="seconds"),
                }
        return {
            "processable_files": [__file__],
            "processable_count": 1,
            "convertible_count": 0,
            "convertible_files": [],
        }

    monkeypatch.setattr(local_service, "collect_user_inputs", fill_jobs)

    result = handle_request({
        "action": "start_build_package",
        "input_paths": [__file__],
        "out": ".",
        "project_alias_id": "test",
    })

    assert result["success"] is False
    assert "繁忙" in result["error"]
    assert len(_JOBS) == MAX_JOBS
    _JOBS.clear()

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.cli import main
from redaction_assistant.local_service import handle_request, validate_request_headers


def test_unsigned_service_requests_are_rejected_by_header_contract():
    assert validate_request_headers({}, "{}") is False
    assert validate_request_headers({"X-DRA-Timestamp": "1", "X-DRA-Signature": "deadbeef"}, "{}") is False


def test_legacy_trial_and_license_artifacts_are_inert(tmp_path: Path):
    legacy = tmp_path / "registration"
    legacy.mkdir()
    (legacy / "license.json").write_text('{"schema_version": "document_redaction_local_license.v1"}', encoding="utf-8")
    (legacy / "trial_usage_community.json").write_text('{"used_files": 50}', encoding="utf-8")
    (legacy / "registration_request.json").write_text('{"email": "old@example.com"}', encoding="utf-8")
    before = sorted(p.name for p in legacy.iterdir())

    assert main(["trial-status", "--registration-dir", str(legacy)]) == 0
    assert main(["registration-request", "--email", "x@example.com", "--out", str(legacy)]) == 0

    after = sorted(p.name for p in legacy.iterdir())
    assert before == after


def test_no_gate_files_are_created_by_build_package(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("项目名称：示范电网项目。合同金额：350万元。", encoding="utf-8")
    response = handle_request({
        "action": "build_package",
        "project_alias_id": "SEC-TRIAL",
        "out": str(tmp_path / "out"),
        "files": [str(source)],
    })
    assert response["success"] is True

    created = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")}
    assert not any("trial_usage_" in name for name in created)
    assert not any(name.endswith("license.json") for name in created)
    assert not any(name.endswith("registration_request.json") for name in created)

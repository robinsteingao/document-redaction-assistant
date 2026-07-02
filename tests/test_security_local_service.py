from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.auth import generate_signature
from redaction_assistant import local_service
from redaction_assistant.install_package import build_install_package
from redaction_assistant.local_service import ALLOWED_ORIGINS, handle_request, validate_request_headers, validate_input_paths


def test_hmac_request_auth_rejects_missing_and_accepts_signed_payload():
    payload = json.dumps({"action": "ocr_status"}, ensure_ascii=False)
    secret = b"local-secret"
    timestamp = str(int(time.time()))

    assert validate_request_headers({}, payload, secret=secret) is False
    signature = generate_signature(secret, timestamp, payload)
    assert validate_request_headers({"X-DRA-Timestamp": timestamp, "X-DRA-Signature": signature}, payload, secret=secret) is True


def test_hmac_request_auth_accepts_canonicalized_header_case():
    payload = json.dumps({"action": "ocr_status"}, ensure_ascii=False)
    secret = b"local-secret"
    timestamp = str(int(time.time()))
    signature = generate_signature(secret, timestamp, payload)

    assert validate_request_headers({"X-Dra-Timestamp": timestamp, "X-Dra-Signature": signature}, payload, secret=secret) is True


def test_hmac_request_auth_rejects_stale_timestamp():
    payload = "{}"
    secret = b"local-secret"
    timestamp = str(int(time.time()) - 9999)
    signature = generate_signature(secret, timestamp, payload)

    assert validate_request_headers({"X-DRA-Timestamp": timestamp, "X-DRA-Signature": signature}, payload, secret=secret) is False


def test_validate_input_paths_blocks_system_locations():
    assert validate_input_paths([r"C:\\Windows\\System32\\drivers\\etc\\hosts"])["ok"] is False
    assert validate_input_paths([r"C:\\Windows"])["ok"] is False
    assert validate_input_paths([r"C:\\Program Files"])["ok"] is False
    assert validate_input_paths([r"C:\\ProgramData"])["ok"] is False
    assert validate_input_paths([str(Path.home() / ".ssh")])["ok"] is False


def test_validate_input_paths_allows_existing_user_file(tmp_path: Path):
    sample = tmp_path / "input.txt"
    sample.write_text("hello", encoding="utf-8")

    result = validate_input_paths([str(sample)])

    assert result["ok"] is True
    assert result["paths"] == [str(sample.resolve())]


def test_cors_allows_packaged_file_origin_without_wildcard():
    assert "null" in ALLOWED_ORIGINS
    assert "*" not in ALLOWED_ORIGINS


def test_build_package_input_paths_rejects_dangerous_path_before_collection(monkeypatch):
    def fail_collect_user_inputs(paths):  # pragma: no cover - should not be called
        raise AssertionError(f"dangerous paths reached collect_user_inputs: {paths}")

    monkeypatch.setattr(local_service, "collect_user_inputs", fail_collect_user_inputs)

    result = handle_request({
        "action": "build_package",
        "input_paths": [r"C:\Windows\System32\drivers\etc\hosts"],
        "out": "out",
        "project_alias_id": "demo",
    })

    assert result["success"] is False
    assert "path is not allowed" in result["error"]


def test_build_package_rejects_dangerous_output_path_before_build(monkeypatch, tmp_path: Path):
    sample = tmp_path / "input.txt"
    sample.write_text("hello", encoding="utf-8")

    def fail_build_outputs(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("dangerous output path reached build outputs")

    monkeypatch.setattr(local_service, "_build_outputs", fail_build_outputs)

    result = handle_request({
        "action": "build_package",
        "files": [str(sample)],
        "out": r"C:\Windows\Temp\dra-output",
        "project_alias_id": "demo",
    })

    assert result["success"] is False
    assert "output path is not allowed" in result["error"]


def test_install_package_uses_package_local_service_secret(tmp_path: Path):
    result = build_install_package(tmp_path, version="security-test")
    package_dir = result["package_dir"]

    shell = (package_dir / "app" / "desktop_shell" / "index.html").read_text(encoding="utf-8")
    start_desktop = (package_dir / "app" / "start_desktop_app.bat").read_text(encoding="utf-8")
    start_service = (package_dir / "app" / "start_local_service.bat").read_text(encoding="utf-8")

    assert "DRA_LOCAL_SERVICE_SECRET" in start_desktop
    assert "DRA_LOCAL_SERVICE_SECRET" in start_service
    assert "document-redaction-assistant-local-service" not in shell
    assert "const localServiceSecret = \"" in shell

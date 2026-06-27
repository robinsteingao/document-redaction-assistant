from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.crypto import decrypt_mapping_file
from redaction_assistant.desktop_shell import build_desktop_shell
from redaction_assistant.local_service import handle_request
from redaction_assistant.registration import build_registration_request, write_registration_request


def test_local_service_encrypts_mapping_when_client_passphrase_is_provided(tmp_path: Path):
    registration_dir = tmp_path / "registration"
    write_registration_request(
        registration_dir,
        build_registration_request(edition="community", email="client@example.com"),
    )
    source = tmp_path / "input.txt"
    source.write_text("联系人：张三\n合同金额：300万元\n试运行30天，电压10kV。", encoding="utf-8")
    out = tmp_path / "out"

    response = handle_request({
        "action": "build_package",
        "files": [str(source)],
        "out": str(out),
        "project_alias_id": "CLIENT-ENC",
        "registration_dir": str(registration_dir),
        "mapping_passphrase": "client-passphrase",
    })

    assert response["success"] is True
    result = response["result"]
    encrypted = Path(result["encrypted_mapping"])
    plain = out / "local_mapping.private.json"
    text = encrypted.read_text(encoding="utf-8")

    assert encrypted.name == "local_mapping.private.enc"
    assert encrypted.exists()
    assert not plain.exists()
    assert "张三" not in text
    restored = decrypt_mapping_file(encrypted, passphrase="client-passphrase")
    assert restored["items"]


def test_async_job_status_does_not_echo_mapping_passphrase(tmp_path: Path):
    registration_dir = tmp_path / "registration"
    write_registration_request(
        registration_dir,
        build_registration_request(edition="community", email="client@example.com"),
    )
    source = tmp_path / "input.txt"
    source.write_text("联系人：张三\n合同金额：300万元", encoding="utf-8")

    response = handle_request({
        "action": "start_build_package",
        "input_paths": [str(source)],
        "out": str(tmp_path / "out"),
        "project_alias_id": "CLIENT-ENC-ASYNC",
        "registration_dir": str(registration_dir),
        "mapping_passphrase": "do-not-echo-passphrase",
    })
    assert response["success"] is True

    status = handle_request({"action": "job_status", "job_id": response["result"]["job_id"]})
    text = str(status)

    assert status["success"] is True
    assert "do-not-echo-passphrase" not in text
    assert "mapping_passphrase" not in text


def test_desktop_shell_collects_client_mapping_passphrase(tmp_path: Path):
    shell = build_desktop_shell(tmp_path, version="0.24.2-client-enc", service_url="http://127.0.0.1:8765")
    html = (shell / "index.html").read_text(encoding="utf-8")

    assert "mappingPassphrase" in html
    assert "本地映射表加密口令" in html
    assert "mapping_passphrase" in html
    assert "local_mapping.private.enc" in html
    assert "local_mapping.private.json" not in html

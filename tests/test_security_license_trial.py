from __future__ import annotations

import json
import sys
import base64
from datetime import date
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.local_license import LicenseSigningKeyMissingError, create_local_license, validate_local_license
from redaction_assistant.registration import TrialLimitExceededError, consume_trial_or_raise, write_registration_request, build_registration_request


def test_signed_license_v2_rejects_tampering():
    private_key = Ed25519PrivateKey.generate()
    private_key_b64 = base64.b64encode(private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).decode("ascii")
    public_key_b64 = base64.b64encode(private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode("ascii")
    license_data = create_local_license("客户A", expires_on="2099-12-31", features=["build_package"], issuer_private_key_b64=private_key_b64)

    assert license_data["schema_version"] == "document_redaction_local_license.v2"
    assert "signature" in license_data
    assert validate_local_license(license_data, today=date(2026, 1, 1), public_key_b64=public_key_b64)["status"] == "valid"

    tampered = dict(license_data)
    tampered["features"] = ["build_package", "batch_build"]
    result = validate_local_license(tampered, today=date(2026, 1, 1), public_key_b64=public_key_b64)
    assert result["status"] == "invalid"
    assert "签名" in result["message"]


def test_license_signing_requires_external_issuer_private_key(monkeypatch):
    monkeypatch.delenv("DRA_LICENSE_ISSUER_PRIVATE_KEY_B64", raising=False)

    with pytest.raises(LicenseSigningKeyMissingError):
        create_local_license("客户A", expires_on="2099-12-31")


def test_legacy_v1_license_has_migration_status():
    legacy = {
        "schema_version": "document_redaction_local_license.v1",
        "customer_name": "旧客户",
        "expires_on": "2099-12-31",
        "features": ["build_package"],
    }

    result = validate_local_license(legacy, today=date(2026, 1, 1))

    assert result["status"] == "legacy_migration_required"
    assert result["features"] == ["build_package"]


def test_trial_usage_hmac_detects_tampering(tmp_path: Path):
    write_registration_request(tmp_path, build_registration_request(email="user@example.com"))
    consume_trial_or_raise(1, registration_dir=tmp_path)
    usage_path = tmp_path / "trial_usage_community.json"
    data = json.loads(usage_path.read_text(encoding="utf-8"))
    assert "signature" in data

    data["used_files"] = 0
    usage_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        consume_trial_or_raise(1, registration_dir=tmp_path)
    except TrialLimitExceededError as exc:
        assert "试用记录校验失败" in str(exc)
    else:
        raise AssertionError("tampered usage should be rejected")

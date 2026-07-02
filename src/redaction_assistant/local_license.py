from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


DEFAULT_FEATURES = [
    "runtime_preflight",
    "build_package",
    "batch_build",
    "restore",
    "local_service",
    "desktop_shell",
    "ocr_adapter",
]

PUBLIC_KEY_B64 = os.getenv("DRA_LICENSE_ISSUER_PUBLIC_KEY_B64") or "QwRr/kCSs+lJlOraFdzCDYqqB7ZY/TlU644O+4vcpd4="


class LicenseSigningKeyMissingError(RuntimeError):
    pass


def create_local_license(
    customer_name: str,
    *,
    expires_on: str = "2099-12-31",
    features: list[str] | None = None,
    issuer_private_key_b64: str | None = None,
) -> dict[str, Any]:
    enabled = features or DEFAULT_FEATURES
    license_id = hashlib.sha256(f"{customer_name}|{expires_on}|{'/'.join(sorted(enabled))}".encode("utf-8")).hexdigest()[:16]
    data = {
        "schema_version": "document_redaction_local_license.v2",
        "license_id": f"DRA-{license_id}",
        "customer_name": customer_name,
        "expires_on": expires_on,
        "features": enabled,
        "offline_only": True,
        "boundary": [
            "授权文件仅用于本地试点能力开关",
            "不包含客户原始文件内容",
            "不上传到 STPE-AI 服务端",
        ],
    }
    data["signature"] = sign_license(data, _load_issuer_private_key(issuer_private_key_b64))
    return data


def sign_license(license_data: dict[str, Any], private_key: Ed25519PrivateKey) -> str:
    payload = _license_payload(license_data)
    return base64.b64encode(private_key.sign(payload)).decode("ascii")


def verify_license_signature(license_data: dict[str, Any], *, public_key_b64: str = PUBLIC_KEY_B64) -> bool:
    signature = license_data.get("signature")
    if not signature:
        return False
    public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    try:
        public_key.verify(base64.b64decode(str(signature)), _license_payload(license_data))
        return True
    except (InvalidSignature, ValueError):
        return False


def validate_local_license(license_data: dict[str, Any], *, today: date | None = None, public_key_b64: str = PUBLIC_KEY_B64) -> dict[str, Any]:
    schema = license_data.get("schema_version")
    features = list(license_data.get("features") or [])
    if schema == "document_redaction_local_license.v1":
        return {"status": "legacy_migration_required", "features": features, "message": "旧版授权文件缺少签名，请联系作者换发 v2 签名授权。"}
    if schema != "document_redaction_local_license.v2":
        return {"status": "invalid", "features": [], "message": "授权文件 schema_version 不匹配。"}
    if not verify_license_signature(license_data, public_key_b64=public_key_b64):
        return {"status": "invalid", "features": [], "message": "授权文件签名验证失败。"}
    expires_raw = license_data.get("expires_on")
    try:
        expires = date.fromisoformat(str(expires_raw))
    except ValueError:
        return {"status": "invalid", "features": [], "message": "授权到期日期格式无效。"}
    current = today or date.today()
    if expires < current:
        return {"status": "expired", "features": features, "message": f"授权已于 {expires.isoformat()} 到期。"}
    return {"status": "valid", "features": features, "message": f"授权有效期至 {expires.isoformat()}。"}


def write_local_license(path: Path | str, *, customer_name: str = "本地试点客户", expires_on: str = "2099-12-31", issuer_private_key_b64: str | None = None) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(create_local_license(customer_name, expires_on=expires_on, issuer_private_key_b64=issuer_private_key_b64), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output


def write_license_placeholder(path: Path | str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "document_redaction_local_license.v2",
        "license_required": True,
        "message": "请将发行方签发的 license.json 放到本文件位置后再校验授权。",
        "boundary": [
            "客户/开源包不包含授权签发私钥",
            "正式授权文件应由发行方离线签发",
            "未签名占位文件不能作为有效授权",
        ],
    }
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _load_issuer_private_key(issuer_private_key_b64: str | None = None) -> Ed25519PrivateKey:
    raw = issuer_private_key_b64 or os.getenv("DRA_LICENSE_ISSUER_PRIVATE_KEY_B64")
    if not raw:
        raise LicenseSigningKeyMissingError("缺少发行方授权签发私钥；客户/开源包不得内置私钥。")
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))


def _license_payload(license_data: dict[str, Any]) -> bytes:
    payload = {
        "license_id": license_data.get("license_id"),
        "customer_name": license_data.get("customer_name"),
        "expires_on": license_data.get("expires_on"),
        "features": sorted(str(item) for item in license_data.get("features") or []),
        "offline_only": bool(license_data.get("offline_only")),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

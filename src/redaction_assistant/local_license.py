from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_FEATURES = [
    "runtime_preflight",
    "build_package",
    "batch_build",
    "restore",
    "local_service",
    "desktop_shell",
    "ocr_adapter",
]


def create_local_license(
    customer_name: str,
    *,
    expires_on: str = "2099-12-31",
    features: list[str] | None = None,
) -> dict[str, Any]:
    enabled = features or DEFAULT_FEATURES
    license_id = hashlib.sha256(f"{customer_name}|{expires_on}|{'/'.join(enabled)}".encode("utf-8")).hexdigest()[:16]
    return {
        "schema_version": "document_redaction_local_license.v1",
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


def validate_local_license(license_data: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    if license_data.get("schema_version") != "document_redaction_local_license.v1":
        return {"status": "invalid", "features": [], "message": "授权文件 schema_version 不匹配。"}
    expires_raw = license_data.get("expires_on")
    try:
        expires = date.fromisoformat(str(expires_raw))
    except ValueError:
        return {"status": "invalid", "features": [], "message": "授权到期日期格式无效。"}
    current = today or date.today()
    features = list(license_data.get("features") or [])
    if expires < current:
        return {"status": "expired", "features": features, "message": f"授权已于 {expires.isoformat()} 到期。"}
    return {"status": "valid", "features": features, "message": f"授权有效期至 {expires.isoformat()}。"}


def write_local_license(path: Path | str, *, customer_name: str = "本地试点客户", expires_on: str = "2099-12-31") -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(create_local_license(customer_name, expires_on=expires_on), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output

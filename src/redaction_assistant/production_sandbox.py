from __future__ import annotations

import json
from pathlib import Path


SECRET_KEYS = {"authorization", "token", "api_key", "apikey", "secret", "password"}
SECRET_MARKERS = ("bearer ", "sk-", "token", "secret", "password")


def build_production_sandbox_config(
    output_dir: Path | str,
    *,
    endpoint: str,
    environment: str = "pilot",
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "document_redaction_production_sandbox_config.v1",
        "environment": environment,
        "endpoint": endpoint,
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "SET_BY_CUSTOMER_AT_RUNTIME",
        },
        "payload_policy": {
            "redacted_payload_only": True,
            "allow_original_files": False,
            "allow_local_mapping": False,
            "allowed_payloads": ["sandbox_import_package.json", "redaction_upload_package.json"],
        },
        "project_identity": {
            "use_project_alias_id": True,
            "forbid_real_project_name": True,
        },
        "dry_run_first": True,
    }
    path = root / "production_sandbox_config.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def validate_production_sandbox_config(config_path: Path | str) -> dict:
    path = Path(config_path)
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    issues = []
    policy = config.get("payload_policy", {})
    if policy.get("redacted_payload_only") is not True:
        issues.append({"field": "payload_policy.redacted_payload_only", "reason": "must_be_true"})
    if policy.get("allow_original_files") is not False:
        issues.append({"field": "payload_policy.allow_original_files", "reason": "must_be_false"})
    if policy.get("allow_local_mapping") is not False:
        issues.append({"field": "payload_policy.allow_local_mapping", "reason": "must_be_false"})
    issues.extend(_secret_issues(config))
    return {
        "status": "valid" if not issues else "invalid",
        "config": str(path),
        "issues": issues,
    }


def _secret_issues(value, prefix: str = "") -> list[dict]:
    issues = []
    if isinstance(value, dict):
        for key, child in value.items():
            field = f"{prefix}.{key}" if prefix else str(key)
            lower_key = str(key).lower()
            if lower_key in SECRET_KEYS and isinstance(child, str) and child != "SET_BY_CUSTOMER_AT_RUNTIME":
                issues.append({"field": field, "reason": "secret_like_value"})
            issues.extend(_secret_issues(child, field))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(_secret_issues(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in SECRET_MARKERS) and value != "SET_BY_CUSTOMER_AT_RUNTIME":
            issues.append({"field": prefix, "reason": "secret_like_value"})
    return issues

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .local_license import validate_local_license


ANNUAL_FEE_CNY = 80
DEFAULT_EDITION = "community"
CONTACT_EMAIL = "65710714@qq.com"
TRIAL_LIMITS = {
    "community": 50,
    "stpe_partner": 10,
}


class RegistrationRequiredError(RuntimeError):
    pass


class TrialLimitExceededError(RuntimeError):
    pass


def default_registration_dir() -> Path:
    configured = os.getenv("DRA_REGISTRATION_DIR")
    if configured:
        return Path(configured)
    return Path.home() / ".document_redaction_assistant"


def build_registration_request(
    *,
    edition: str = DEFAULT_EDITION,
    email: str,
    organization: str = "",
    name: str = "",
    phone: str = "",
    use_case: str = "",
) -> dict[str, Any]:
    _ensure_edition(edition)
    return {
        "schema_version": "document_redaction_registration_request.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "edition": edition,
        "email": email.strip(),
        "organization": organization.strip(),
        "name": name.strip(),
        "phone": phone.strip(),
        "use_case": use_case.strip(),
        "trial_file_limit": TRIAL_LIMITS[edition],
        "annual_fee_cny": ANNUAL_FEE_CNY,
        "recipient": CONTACT_EMAIL,
        "boundary": [
            "注册申请不包含原始文档、本地映射表或脱敏正文。",
            "个人版注册费用按年度缴纳，当前为每年80元。",
            "未导入有效授权文件前，仅允许使用试用文件额度。",
        ],
    }


def write_registration_request(output_dir: Path | str, request: dict[str, Any]) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    request_path = root / "registration_request.json"
    mailto_path = root / "registration_mailto.txt"
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    mailto_path.write_text(_mailto_text(request), encoding="utf-8")
    return {"registration_request": request_path, "registration_mailto": mailto_path}


def registration_status(registration_dir: Path | str | None = None, *, edition: str = DEFAULT_EDITION) -> dict[str, Any]:
    _ensure_edition(edition)
    root = Path(registration_dir) if registration_dir else default_registration_dir()
    request_path = root / "registration_request.json"
    license_path = root / "license.json"
    usage_path = _usage_path(root, edition)
    usage = _read_usage(usage_path, root=root, edition=edition)
    license_result = None
    if license_path.exists():
        license_result = validate_local_license(_read_json(license_path, default={}))
    registered = request_path.exists()
    licensed = bool(license_result and license_result.get("status") == "valid")
    return {
        "schema_version": "document_redaction_registration_status.v1",
        "edition": edition,
        "registration_dir": str(root),
        "registered": registered,
        "licensed": licensed,
        "annual_fee_cny": ANNUAL_FEE_CNY,
        "trial_file_limit": TRIAL_LIMITS[edition],
        "used_files": int(usage.get("used_files") or 0),
        "remaining_trial_files": max(0, TRIAL_LIMITS[edition] - int(usage.get("used_files") or 0)),
        "registration_request": str(request_path),
        "license_file": str(license_path),
        "license_status": license_result,
        "message": _status_message(registered=registered, licensed=licensed, edition=edition, used=int(usage.get("used_files") or 0)),
    }


def consume_trial_or_raise(file_count: int, *, edition: str = DEFAULT_EDITION, registration_dir: Path | str | None = None) -> dict[str, Any]:
    _ensure_edition(edition)
    count = max(0, int(file_count))
    root = Path(registration_dir) if registration_dir else default_registration_dir()
    root.mkdir(parents=True, exist_ok=True)
    status = registration_status(root, edition=edition)
    if status["licensed"]:
        return {**status, "consumed_files": 0, "gate": "licensed"}
    if not status["registered"]:
        raise RegistrationRequiredError(
            "请先完成本地注册申请后再使用脱敏处理。运行："
            "python -m redaction_assistant.cli registration-request --email 你的邮箱 --out 注册目录。"
            f"个人版注册费用按年度缴纳，当前为每年{ANNUAL_FEE_CNY}元；注册后可先试用{TRIAL_LIMITS[edition]}个文件。"
        )
    used = int(status["used_files"])
    limit = TRIAL_LIMITS[edition]
    if used + count > limit:
        raise TrialLimitExceededError(
            f"试用额度已用完或不足：{edition} 版已使用 {used}/{limit} 个文件，本次还需 {count} 个文件。"
            f"请联系 {CONTACT_EMAIL} 办理年度注册授权（{ANNUAL_FEE_CNY}元/年），并将有效 license.json 放入 {root} 后继续使用。"
        )
    usage_path = _usage_path(root, edition)
    usage = _read_usage(usage_path, root=root, edition=edition)
    events = list(usage.get("events") or [])
    events.append({"created_at": datetime.now().isoformat(timespec="seconds"), "file_count": count})
    usage.update({"schema_version": "document_redaction_trial_usage.v2", "edition": edition, "used_files": used + count, "events": events})
    _write_usage(usage_path, usage, root=root, edition=edition)
    return registration_status(root, edition=edition) | {"consumed_files": count, "gate": "trial"}


def _usage_path(root: Path, edition: str) -> Path:
    return root / f"trial_usage_{edition}.json"


def _read_usage(path: Path, *, root: Path, edition: str) -> dict[str, Any]:
    if not path.exists():
        return {"used_files": 0, "events": []}
    data = _read_json(path, default=None)
    if not isinstance(data, dict):
        raise TrialLimitExceededError("试用记录校验失败：文件无法读取。")
    if "signature" not in data:
        # Legacy unsigned usage is accepted once, then rewritten as signed v2 on next consume.
        return data
    signature = str(data.get("signature") or "")
    payload = dict(data)
    payload.pop("signature", None)
    expected = _usage_signature(payload, root=root, edition=edition)
    if not hmac.compare_digest(signature, expected):
        raise TrialLimitExceededError("试用记录校验失败：文件可能已被篡改，请联系作者处理。")
    return data


def _write_usage(path: Path, usage: dict[str, Any], *, root: Path, edition: str) -> None:
    payload = dict(usage)
    payload.pop("signature", None)
    payload["signature"] = _usage_signature(payload, root=root, edition=edition)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _usage_signature(payload: dict[str, Any], *, root: Path, edition: str) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    key_material = f"{uuid.getnode()}|{root.resolve()}|{edition}".encode("utf-8")
    key = hashlib.sha256(key_material).digest()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _ensure_edition(edition: str) -> None:
    if edition not in TRIAL_LIMITS:
        raise ValueError(f"unsupported edition: {edition}")


def _status_message(*, registered: bool, licensed: bool, edition: str, used: int) -> str:
    if licensed:
        return "已导入有效授权文件，可继续使用授权功能。"
    if not registered:
        return f"尚未生成本地注册申请。个人版注册费用为{ANNUAL_FEE_CNY}元/年，注册后可先试用{TRIAL_LIMITS[edition]}个文件。"
    return f"已注册待授权，当前试用已使用 {used}/{TRIAL_LIMITS[edition]} 个文件。年度注册费用为{ANNUAL_FEE_CNY}元/年。"


def _mailto_text(request: dict[str, Any]) -> str:
    return "\n".join([
        f"收件人：{request.get('recipient', CONTACT_EMAIL)}",
        "主题：文档安全脱敏助手注册申请",
        "",
        "请将 registration_request.json 作为附件发送，或复制以下信息：",
        json.dumps(request, ensure_ascii=False, indent=2),
        "",
        f"费用说明：个人版注册费用按年度缴纳，当前为每年{ANNUAL_FEE_CNY}元。",
    ])

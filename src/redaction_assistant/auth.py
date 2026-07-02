from __future__ import annotations

import hashlib
import hmac
import time

DEFAULT_MAX_SKEW_SECONDS = 300


def generate_signature(secret: bytes, timestamp: str, payload: str) -> str:
    message = f"{timestamp}.{payload}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_request_signature(
    timestamp: str,
    signature: str,
    payload: str,
    *,
    secret: bytes,
    now: int | None = None,
    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
) -> bool:
    if not timestamp or not signature or not secret:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    current = int(time.time()) if now is None else int(now)
    if abs(current - ts) > max_skew_seconds:
        return False
    expected = generate_signature(secret, timestamp, payload)
    return hmac.compare_digest(expected, signature)

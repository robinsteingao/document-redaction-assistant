from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


LEGACY_SCHEMA = "local_mapping_envelope.v1"
SCHEMA = "local_mapping_envelope.v2"
PBKDF2_ROUNDS = 390_000
LEGACY_PBKDF2_ROUNDS = 120_000


def encrypt_mapping_file(source: Path | str, target: Path | str, *, passphrase: str) -> Path:
    source_path = Path(source)
    target_path = Path(target)
    payload = source_path.read_bytes()
    salt = os.urandom(16)
    key = _fernet_key(passphrase, salt, PBKDF2_ROUNDS)
    token = Fernet(key).encrypt(payload)
    envelope = {
        "schema_version": SCHEMA,
        "algorithm": "fernet",
        "kdf": "pbkdf2_hmac_sha256",
        "rounds": PBKDF2_ROUNDS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "ciphertext": token.decode("ascii"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    target_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    source_path.unlink()
    return target_path


def decrypt_mapping_file(source: Path | str, *, passphrase: str) -> dict[str, Any]:
    envelope = json.loads(Path(source).read_text(encoding="utf-8"))
    schema = envelope.get("schema_version")
    if schema == SCHEMA:
        return _decrypt_v2(envelope, passphrase=passphrase)
    if schema == LEGACY_SCHEMA:
        return _decrypt_v1(envelope, passphrase=passphrase)
    raise ValueError("unsupported encrypted mapping schema")


def _decrypt_v2(envelope: dict[str, Any], *, passphrase: str) -> dict[str, Any]:
    if envelope.get("algorithm") != "fernet":
        raise ValueError("unsupported encrypted mapping algorithm")
    salt = base64.b64decode(envelope["salt"])
    rounds = int(envelope.get("rounds") or PBKDF2_ROUNDS)
    key = _fernet_key(passphrase, salt, rounds)
    try:
        plaintext = Fernet(key).decrypt(str(envelope["ciphertext"]).encode("ascii"))
    except InvalidToken as exc:
        raise ValueError("invalid passphrase or corrupted mapping file") from exc
    return json.loads(plaintext.decode("utf-8"))


def _decrypt_v1(envelope: dict[str, Any], *, passphrase: str) -> dict[str, Any]:
    salt = base64.b64decode(envelope["salt"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    expected_tag = base64.b64decode(envelope["tag"])
    rounds = int(envelope.get("rounds") or LEGACY_PBKDF2_ROUNDS)
    key = _legacy_derive_key(passphrase, salt, rounds, dklen=32)
    actual_tag = hmac.new(key, ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, actual_tag):
        raise ValueError("invalid passphrase or corrupted mapping file")
    plaintext = _legacy_xor_stream(ciphertext, key)
    return json.loads(plaintext.decode("utf-8"))


def _fernet_key(passphrase: str, salt: bytes, rounds: int) -> bytes:
    if not passphrase:
        raise ValueError("passphrase is required")
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, rounds, dklen=32)
    return base64.urlsafe_b64encode(key)


def _legacy_derive_key(passphrase: str, salt: bytes, rounds: int, *, dklen: int) -> bytes:
    if not passphrase:
        raise ValueError("passphrase is required")
    digest_size = hashlib.sha256().digest_size
    blocks = []
    block_count = -(-dklen // digest_size)
    password = passphrase.encode("utf-8")
    for block_index in range(1, block_count + 1):
        block = hmac.new(password, salt + block_index.to_bytes(4, "big"), hashlib.sha256).digest()
        accumulator = bytearray(block)
        previous = block
        for _ in range(1, rounds):
            previous = hmac.new(password, previous, hashlib.sha256).digest()
            for idx, value in enumerate(previous):
                accumulator[idx] ^= value
        blocks.append(bytes(accumulator))
    return b"".join(blocks)[:dklen]


def _legacy_xor_stream(data: bytes, key: bytes) -> bytes:
    out = bytearray()
    counter = 0
    offset = 0
    while offset < len(data):
        block = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha256).digest()
        for b in block:
            if offset >= len(data):
                break
            out.append(data[offset] ^ b)
            offset += 1
        counter += 1
    return bytes(out)

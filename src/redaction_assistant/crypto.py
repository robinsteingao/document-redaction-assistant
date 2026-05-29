from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any


SCHEMA = "local_mapping_envelope.v1"
PBKDF2_ROUNDS = 120_000


def encrypt_mapping_file(source: Path | str, target: Path | str, *, passphrase: str) -> Path:
    source_path = Path(source)
    target_path = Path(target)
    payload = source_path.read_bytes()
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    ciphertext = _xor_stream(payload, key)
    tag = hmac.new(key, ciphertext, hashlib.sha256).digest()
    envelope = {
        "schema_version": SCHEMA,
        "kdf": "pbkdf2_hmac_sha256",
        "rounds": PBKDF2_ROUNDS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    target_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    source_path.unlink()
    return target_path


def decrypt_mapping_file(source: Path | str, *, passphrase: str) -> dict[str, Any]:
    envelope = json.loads(Path(source).read_text(encoding="utf-8"))
    if envelope.get("schema_version") != SCHEMA:
        raise ValueError("unsupported encrypted mapping schema")
    salt = base64.b64decode(envelope["salt"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    expected_tag = base64.b64decode(envelope["tag"])
    key = _derive_key(passphrase, salt)
    actual_tag = hmac.new(key, ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, actual_tag):
        raise ValueError("invalid passphrase or corrupted mapping file")
    plaintext = _xor_stream(ciphertext, key)
    return json.loads(plaintext.decode("utf-8"))


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if not passphrase:
        raise ValueError("passphrase is required")
    return _pbkdf2_hmac_sha256(passphrase.encode("utf-8"), salt, PBKDF2_ROUNDS, dklen=32)


def _pbkdf2_hmac_sha256(password: bytes, salt: bytes, rounds: int, *, dklen: int) -> bytes:
    digest_size = hashlib.sha256().digest_size
    blocks = []
    block_count = -(-dklen // digest_size)
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


def _xor_stream(data: bytes, key: bytes) -> bytes:
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

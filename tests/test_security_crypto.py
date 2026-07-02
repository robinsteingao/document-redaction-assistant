from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.crypto import decrypt_mapping_file, encrypt_mapping_file


def _legacy_pbkdf2(password: bytes, salt: bytes, rounds: int, *, dklen: int) -> bytes:
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


def _legacy_xor(data: bytes, key: bytes) -> bytes:
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


def test_encrypt_mapping_uses_fernet_v2_and_removes_plaintext(tmp_path: Path):
    mapping = {"items": [{"original": "张三", "placeholder": "人员A"}]}
    plain = tmp_path / "local_mapping.private.json"
    encrypted = tmp_path / "local_mapping.private.enc"
    plain.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    encrypt_mapping_file(plain, encrypted, passphrase="secret-pass")
    envelope = json.loads(encrypted.read_text(encoding="utf-8"))

    assert not plain.exists()
    assert envelope["schema_version"] == "local_mapping_envelope.v2"
    assert envelope["algorithm"] == "fernet"
    assert envelope["kdf"] == "pbkdf2_hmac_sha256"
    assert "ciphertext" in envelope
    assert "张三" not in encrypted.read_text(encoding="utf-8")
    assert decrypt_mapping_file(encrypted, passphrase="secret-pass") == mapping


def test_decrypt_legacy_v1_envelope_still_supported(tmp_path: Path):
    mapping = {"items": [{"original": "李四", "placeholder": "人员B"}]}
    payload = json.dumps(mapping, ensure_ascii=False).encode("utf-8")
    salt = b"0123456789abcdef"
    key = _legacy_pbkdf2("old-pass".encode("utf-8"), salt, 120_000, dklen=32)
    ciphertext = _legacy_xor(payload, key)
    tag = hmac.new(key, ciphertext, hashlib.sha256).digest()
    envelope = {
        "schema_version": "local_mapping_envelope.v1",
        "kdf": "pbkdf2_hmac_sha256",
        "rounds": 120_000,
        "salt": base64.b64encode(salt).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    encrypted = tmp_path / "legacy.enc"
    encrypted.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")

    assert decrypt_mapping_file(encrypted, passphrase="old-pass") == mapping

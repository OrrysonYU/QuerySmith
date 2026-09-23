"""One-time API key creation and Argon2id verification."""

import hashlib
import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_HASHER = PasswordHasher()


@dataclass(frozen=True)
class ApiKeyRecord:
    lookup_hash: str
    password_hash: str


def create_api_key() -> tuple[str, ApiKeyRecord]:
    raw = f"qs_{secrets.token_urlsafe(32)}"
    lookup = hashlib.sha256(raw.encode()).hexdigest()
    return raw, ApiKeyRecord(lookup_hash=lookup, password_hash=_HASHER.hash(raw))


def verify_api_key(raw: str, record: ApiKeyRecord) -> bool:
    if not secrets.compare_digest(hashlib.sha256(raw.encode()).hexdigest(), record.lookup_hash):
        return False
    try:
        return _HASHER.verify(record.password_hash, raw)
    except VerifyMismatchError:
        return False

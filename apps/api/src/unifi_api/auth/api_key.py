"""API key generation, format validation, and argon2id hashing.

Format: unifi_<env>_<22-char-base32>
Env is "live" or "test". The 22-char body is base32-encoded random bytes.
The "prefix" exposed in audit logs is the first 15 chars (env + first 4 random).
"""

from __future__ import annotations

import re
import secrets
from base64 import b32encode
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


_KEY_PATTERN = re.compile(r"^unifi_(live|test)_[A-Z2-7]{22}$")
_HASHER = PasswordHasher()


@dataclass(frozen=True)
class ApiKeyMaterial:
    plaintext: str
    prefix: str


def generate_key(env: str = "live") -> ApiKeyMaterial:
    if env not in ("live", "test"):
        raise ValueError(f"env must be 'live' or 'test', got {env!r}")
    body = b32encode(secrets.token_bytes(14)).decode("ascii").rstrip("=")[:22]
    plaintext = f"unifi_{env}_{body}"
    prefix = plaintext[:15]
    return ApiKeyMaterial(plaintext=plaintext, prefix=prefix)


def hash_key(plaintext: str) -> str:
    if not _KEY_PATTERN.fullmatch(plaintext):
        raise ValueError("invalid key format")
    return _HASHER.hash(plaintext)


def verify_key(plaintext: str, digest: str) -> bool:
    if not _KEY_PATTERN.fullmatch(plaintext):
        raise ValueError("invalid key format")
    try:
        return _HASHER.verify(digest, plaintext)
    except VerifyMismatchError:
        return False

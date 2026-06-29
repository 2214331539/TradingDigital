"""Symmetric encryption helpers for secrets stored at rest.

The key is derived from ``settings.session_secret`` so no extra configuration is
required. Encrypted values carry an ``enc:v1:`` prefix; values without the prefix
are treated as legacy plaintext and returned as-is, so existing rows keep working
until they are re-written.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from tradedigital.core.config import get_settings

_PREFIX = "enc:v1:"


@lru_cache
def _fernet() -> Fernet:
    secret = get_settings().session_secret.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    if not value:
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return _PREFIX + token


def decrypt_secret(value: str) -> str:
    if not value or not value.startswith(_PREFIX):
        # Empty or legacy plaintext value — nothing to decrypt.
        return value
    token = value[len(_PREFIX):]
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Wrong key / corrupted token: fall back to returning the stored value
        # rather than crashing the login flow.
        return value

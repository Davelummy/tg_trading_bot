from __future__ import annotations

import base64
from typing import Optional

from cryptography.fernet import Fernet


def build_fernet(key: str | None) -> Fernet | None:
    if not key:
        return None
    raw = key.encode("utf-8")
    if len(raw) == 32:
        raw = base64.urlsafe_b64encode(raw)
    return Fernet(raw)


def encrypt(fernet: Fernet | None, payload: str) -> str:
    if not fernet:
        return payload
    return fernet.encrypt(payload.encode("utf-8")).decode("utf-8")


def decrypt(fernet: Fernet | None, payload: str) -> str:
    if not fernet:
        return payload
    return fernet.decrypt(payload.encode("utf-8")).decode("utf-8")

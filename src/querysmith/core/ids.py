"""Opaque identifier helpers."""

import secrets


def new_id(prefix: str) -> str:
    if not prefix.isidentifier():
        raise ValueError("prefix must be a valid identifier")
    return f"{prefix}_{secrets.token_urlsafe(16)}"

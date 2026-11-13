"""Unguessable bearer tokens for public (login-less) carts and orders."""

import secrets

TOKEN_BYTES = 32
TOKEN_MAX_LENGTH = 64


def new_access_token() -> str:
    """43 URL-safe characters carrying 256 bits of randomness."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def tokens_match(expected: str | None, supplied: str | None) -> bool:
    """Constant-time comparison; empty values never match."""
    if not expected or not supplied:
        return False
    return secrets.compare_digest(str(expected).encode(), str(supplied).encode())

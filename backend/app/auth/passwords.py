"""Secure password hashing and verification using bcrypt."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage.

    Returns a string suitable for ``User.password_hash``.
    The hash includes a random salt and work factor.
    """
    if not password:
        raise ValueError("Password must not be empty")
    raw = password.encode("utf-8")
    hashed: bytes = bcrypt.hashpw(raw, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Returns ``True`` when the password matches.
    Malformed hashes return ``False`` safely (no exception).
    """
    try:
        raw = password.encode("utf-8")
        stored = password_hash.encode("utf-8")
        return bcrypt.checkpw(raw, stored)
    except (ValueError, TypeError, AttributeError):
        return False

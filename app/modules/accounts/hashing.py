"""Password and single-use-token hashing, on the standard library only.

PBKDF2-HMAC-SHA256 with a per-password random salt. Format stored in the DB:
    pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
Constant-time verification via hmac.compare_digest.
"""

import hashlib
import hmac
import secrets

from app.config import get_settings

_ALGO = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    iterations = get_settings().account_pbkdf2_iterations
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{_ALGO}${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def new_token() -> tuple[str, str]:
    """Return (plaintext, hash). Only the hash is stored; the plaintext goes
    into the emailed link and is never persisted."""
    plain = secrets.token_urlsafe(32)
    return plain, hash_token(plain)


def hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()

from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_salt(nbytes: int = 16) -> str:
    return secrets.token_hex(nbytes)


def hash_password(password: str, salt: str, iterations: int = 100_000) -> str:
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, iterations)
    return derived.hex()


def verify_password(password: str, salt: str, password_hash: str, iterations: int = 100_000) -> bool:
    candidate_hash = hash_password(password, salt, iterations)
    return hmac.compare_digest(candidate_hash, password_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_user_id() -> str:
    return f"usr_{secrets.token_hex(8)}"

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.auth_utils import verify_password as verify_legacy_password

# Argon2 hasher (OWASP recommended for 2024+)
argon2_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# Bcrypt fallback for existing hashes
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-only-change-me-2f3b0cc7d8d34b4ca28f5e59d8416d10a8f42790d1f74c20",
)
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash. Supports Argon2, bcrypt, and legacy formats."""
    # Try Argon2 first (modern standard)
    if hashed_password.startswith("$argon2"):
        try:
            argon2_hasher.verify(hashed_password, plain_password)
            return True
        except (VerifyMismatchError, InvalidHashError):
            return False

    # Try bcrypt
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, UnknownHashError):
        # Fall back to legacy (SHA-256, PBKDF2)
        return verify_legacy_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using Argon2 (OWASP recommended)."""
    return argon2_hasher.hash(password)


def create_access_token(
    subject: str,
    *,
    role: str,
    region_name: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }
    if region_name:
        payload["region_name"] = region_name
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token.") from exc

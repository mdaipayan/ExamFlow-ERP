from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from .settings import settings

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters.")
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: str, institution_id: str | None, roles: list[str]) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured.")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "institution_id": institution_id,
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured.")
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

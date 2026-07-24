"""
Password hashing and JWT token utilities.

bcrypt for password hashing (via passlib) and HS256 JWT for stateless auth tokens.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# bcrypt context — 12 rounds is a sensible default (balance of speed + security)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    if not plain_password:
        raise ValueError("Password must not be empty")
    # bcrypt has a 72-byte input limit; truncate defensively
    return pwd_context.hash(plain_password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password[:72], hashed_password)
    except Exception:
        return False


def create_access_token(
    user_id: str,
    username: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Token payload contains `sub` (user_id), `username`, and `exp` (expiry).
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.JWT_EXPIRE_HOURS)

    expire_at = datetime.now(tz=timezone.utc) + expires_delta
    payload: Dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "exp": expire_at,
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on invalid/expired tokens."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]

"""
LADRIS — Auth Service: JWT creation, verification, password hashing
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
import bcrypt

from app.config import get_settings
from app.schemas.auth import TokenPayload

settings = get_settings()


# ─── Password Utilities ───────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False


# ─── JWT Utilities ────────────────────────────────────────────────────────────

def create_access_token(
    user_id: UUID,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(tz=timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": email,
        "user_id": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    email: str,
    role: str,
) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": email,
        "user_id": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return TokenPayload(**payload)

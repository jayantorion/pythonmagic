"""
FastAPI authentication dependencies.

`get_current_user` extracts the Bearer JWT, decodes it, and returns the
corresponding User row from the database. `get_current_active_user` is a
stricter variant that also requires `is_active=True`.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User


# tokenUrl is the login endpoint; used for OpenAPI docs only
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def _credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the JWT to a User row. 401 on any failure."""
    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise _credentials_exception("Invalid authentication token: missing subject")
    except JWTError:
        raise _credentials_exception("Invalid or expired authentication token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise _credentials_exception("User account no longer exists")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the user to be active. 403 if deactivated."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return current_user


__all__ = [
    "get_current_user",
    "get_current_active_user",
    "oauth2_scheme",
]

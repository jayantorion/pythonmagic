"""
Auth-related Pydantic schemas (register/login/response).
"""
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,64}$")


def _validate_username(v: str) -> str:
    if not _USERNAME_RE.match(v):
        raise ValueError(
            "Username must be 3-64 chars, alphanumeric or underscore only"
        )
    return v


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        return _validate_username(v)


class LoginRequest(BaseModel):
    """JSON login (used by the frontend; we also accept OAuth2 form data)."""
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    expires_in_hours: int


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

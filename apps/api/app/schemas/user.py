"""Authentication request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    roles: list[UserRole]

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=255)


class LoginResponse(BaseModel):
    user: UserResponse
    expires_at: datetime
    csrf_token: str = Field(description="Echo in X-CSRF-Token on cookie-authenticated unsafe requests")


class LogoutResponse(BaseModel):
    message: str
"""Local user, role and session models for offline authentication."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid as uuid_pkg

from sqlmodel import SQLModel, Field


class UserRole(str, Enum):
    """Workstation roles.

    Analyst (investigate/draft) and Approver (approve/send) are independent
    roles; either may be held explicitly together. Both inherit read-only
    Viewer access. Administrator implies every other role.
    """

    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    APPROVER = "APPROVER"
    ADMINISTRATOR = "ADMINISTRATOR"

    def __str__(self) -> str:
        return self.value

    def implies(self, other: "UserRole") -> bool:
        """Return True when holding this role is sufficient for ``other``."""
        hierarchy = {
            UserRole.ADMINISTRATOR: {
                UserRole.ADMINISTRATOR,
                UserRole.ANALYST,
                UserRole.APPROVER,
                UserRole.VIEWER,
            },
            UserRole.ANALYST: {UserRole.ANALYST, UserRole.VIEWER},
            UserRole.APPROVER: {UserRole.APPROVER, UserRole.VIEWER},
            UserRole.VIEWER: {UserRole.VIEWER},
        }
        return other in hierarchy.get(self, set())


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False
    )
    username: str = Field(max_length=50, nullable=False, unique=True, index=True)
    email: Optional[str] = Field(
        default=None, max_length=255, unique=True, index=True
    )
    full_name: Optional[str] = Field(default=None, max_length=255)
    password_hash: str = Field(max_length=255, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    disabled_at: Optional[datetime] = Field(default=None, nullable=True)
    password_changed_at: Optional[datetime] = Field(default=None, nullable=True)
    last_login_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Optional[datetime] = Field(default=None, nullable=True)
    revoked_at: Optional[datetime] = Field(default=None, nullable=True)


class UserRoleAssignment(SQLModel, table=True):
    __tablename__ = "user_role_assignments"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid_pkg.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    role: UserRole = Field(nullable=False)
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    assigned_by: Optional[uuid_pkg.UUID] = Field(
        default=None, foreign_key="users.id", nullable=True
    )
    revoked_at: Optional[datetime] = Field(default=None, nullable=True)
    revoked_by: Optional[uuid_pkg.UUID] = Field(
        default=None, foreign_key="users.id", nullable=True
    )


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"

    id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4, primary_key=True, nullable=False
    )
    user_id: uuid_pkg.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    token_hash: str = Field(max_length=64, nullable=False, unique=True, index=True)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: datetime = Field(nullable=False)
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at: Optional[datetime] = Field(default=None, nullable=True)
    revoked_reason: Optional[str] = Field(default=None, max_length=200)
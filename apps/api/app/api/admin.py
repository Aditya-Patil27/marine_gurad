"""Administrator-only local accounts and single-deployment settings."""
import json
from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlmodel import Session, select

from app.api.auth import csrf_protect, require_admin
from app.database import get_db
from app.models.user import User, UserRole, UserRoleAssignment
from app.schemas.user import UserResponse
from app.services import auth as auth_service

router = APIRouter()


class DeploymentSettings(BaseModel):
    organization: str = Field(min_length=1, max_length=200)
    aoi_name: str = Field(min_length=1, max_length=200)
    aoi_bbox: List[List[float]]
    display_timezone: str = Field(min_length=1, max_length=100)
    alert_threshold: Decimal = Field(ge=0, le=1, max_digits=4, decimal_places=3)
    report_recipients: List[str] = Field(default_factory=list, max_length=50)
    retention_days: int = Field(ge=1, le=3650)

    @field_validator("aoi_bbox")
    @classmethod
    def validate_bbox(cls, value: List[List[float]]) -> List[List[float]]:
        if len(value) != 2 or any(len(point) != 2 for point in value):
            raise ValueError("aoi_bbox must be [[west, south], [east, north]]")
        (west, south), (east, north) = value
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("aoi_bbox must be ordered WGS84 longitude/latitude bounds")
        return value

    @field_validator("display_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("display_timezone must be an IANA timezone") from exc
        return value

    @field_validator("report_recipients")
    @classmethod
    def validate_recipients(cls, values: List[str]) -> List[str]:
        cleaned = []
        for value in values:
            address = value.strip().lower()
            if not address or "@" not in address or len(address) > 254:
                raise ValueError("report_recipients must contain valid email-like addresses")
            cleaned.append(address)
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("report_recipients must not contain duplicates")
        return cleaned


class DeploymentSettingsResponse(DeploymentSettings):
    updated_at: datetime
    updated_by: UUID | None
    source_status_endpoint: str = "/api/v1/sources/health"


class CreateLocalUser(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=256)
    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    roles: List[UserRole] = Field(min_length=1, max_length=4)


class SetUserActive(BaseModel):
    is_active: bool


def _user_response(db: Session, user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id), username=user.username, email=user.email,
        full_name=user.full_name, is_active=user.is_active,
        created_at=user.created_at, last_login_at=user.last_login_at,
        roles=auth_service.get_user_roles(db, user.id),
    )


@router.get("/settings", response_model=DeploymentSettingsResponse)
def get_deployment_settings(
    _admin: UserResponse = Depends(require_admin), db: Session = Depends(get_db),
):
    row = db.execute(text("SELECT * FROM deployment_settings WHERE id = 1")).mappings().one()
    return dict(row)


@router.put("/settings", response_model=DeploymentSettingsResponse)
def update_deployment_settings(
    payload: DeploymentSettings,
    admin: UserResponse = Depends(require_admin),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    row = db.execute(text("""
        UPDATE deployment_settings SET
            organization=:organization, aoi_name=:aoi_name,
            aoi_bbox=CAST(:aoi_bbox AS jsonb), display_timezone=:display_timezone,
            alert_threshold=:alert_threshold,
            report_recipients=CAST(:report_recipients AS jsonb),
            retention_days=:retention_days, updated_at=NOW(), updated_by=:updated_by
        WHERE id=1 RETURNING *
    """), {
        **payload.model_dump(mode="json"),
        "aoi_bbox": json.dumps(payload.aoi_bbox),
        "report_recipients": json.dumps(payload.report_recipients),
        "updated_by": UUID(admin.id),
    }).mappings().one()
    db.commit()
    return dict(row)


@router.get("/users", response_model=List[UserResponse])
def list_local_users(
    _admin: UserResponse = Depends(require_admin), db: Session = Depends(get_db),
):
    return [_user_response(db, user) for user in db.exec(select(User).order_by(User.username)).all()]


@router.post("/users", response_model=UserResponse, status_code=201)
def create_local_user(
    payload: CreateLocalUser,
    _admin: UserResponse = Depends(require_admin),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    roles = list(dict.fromkeys(payload.roles))
    try:
        user = auth_service.create_user(
            db, payload.username, payload.password, payload.email,
            payload.full_name, roles[0], assigned_by=UUID(_admin.id),
        )
    except auth_service.UserAlreadyExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    for role in roles[1:]:
        db.add(UserRoleAssignment(user_id=user.id, role=role, assigned_by=UUID(_admin.id)))
    db.commit()
    return _user_response(db, user)


@router.patch("/users/{user_id}/active", response_model=UserResponse)
def set_local_user_active(
    user_id: UUID, payload: SetUserActive,
    admin: UserResponse = Depends(require_admin),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    if str(user_id) == admin.id and not payload.is_active:
        raise HTTPException(409, "Administrators cannot disable their own active session")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return _user_response(db, auth_service.set_user_active(db, user, payload.is_active))

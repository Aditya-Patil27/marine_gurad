"""Local cookie-session authentication endpoints and role dependencies.

Login issues an opaque session token in an HttpOnly cookie plus a readable
CSRF cookie. Unsafe cookie-authenticated requests must echo the CSRF cookie in
the ``X-CSRF-Token`` header (double-submit). No provider or network dependency.
"""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, LoginResponse, LogoutResponse, UserResponse
from app.services import auth as auth_service

logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_COOKIE = settings.AUTH_SESSION_COOKIE_NAME
CSRF_COOKIE = settings.AUTH_CSRF_COOKIE_NAME
CSRF_HEADER = "X-CSRF-Token"


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_response(db: Session, user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        roles=auth_service.get_user_roles(db, user.id),
    )


def _set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    max_age = settings.AUTH_SESSION_TTL_MINUTES * 60
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Resolve the authenticated user from the session cookie.

    Never trusts a user id or name supplied in the request body or headers.
    """
    token = request.cookies.get(SESSION_COOKIE)
    try:
        user, _session = auth_service.validate_session(db, token)
    except auth_service.SessionInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return _user_response(db, user)


def csrf_protect(request: Request) -> None:
    """Double-submit CSRF check for unsafe HTTP methods."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    cookie_value = request.cookies.get(CSRF_COOKIE)
    header_value = request.headers.get(CSRF_HEADER)
    if not cookie_value or not header_value or not secrets.compare_digest(cookie_value, header_value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid CSRF token",
        )


def require_roles(*required: UserRole):
    """Dependency factory: allow a user holding any required role.

    Administrator implies every other role through ``UserRole.implies``.
    """

    def dependency(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if any(auth_service.user_has_role(current_user.roles, role) for role in required):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return dependency


require_viewer = require_roles(UserRole.VIEWER)
require_analyst = require_roles(UserRole.ANALYST)
require_approver = require_roles(UserRole.APPROVER)
require_admin = require_roles(UserRole.ADMINISTRATOR)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    key = auth_service.throttle_key(payload.username, _client_ip(request))
    retry_after = auth_service.login_retry_after(key)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        user = auth_service.authenticate_user(db, payload.username, payload.password)
    except auth_service.AuthError:
        auth_service.record_login_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    auth_service.clear_login_failures(key)
    token, session = auth_service.create_session(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    csrf_token = secrets.token_urlsafe(32)
    _set_session_cookies(response, token, csrf_token)
    logger.info("Local login succeeded for user_id=%s", user.id)
    return LoginResponse(
        user=_user_response(db, user),
        expires_at=session.expires_at,
        csrf_token=csrf_token,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
) -> LogoutResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or not auth_service.revoke_session(db, token, reason="logout"):
        _clear_session_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    _clear_session_cookies(response)
    return LogoutResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
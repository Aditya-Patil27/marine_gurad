"""Local authentication service: password hashing, sessions and login throttling.

No network or provider dependency. Sessions use opaque random tokens; only a
SHA-256 digest of each token is stored. Passwords use Argon2id via argon2-cffi.
"""
import hashlib
import secrets
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import update
from sqlmodel import Session, select

from app.config import settings
from app.models.user import User, UserRole, UserRoleAssignment, UserSession


class AuthError(Exception):
    """Base authentication error."""


class InvalidCredentialsError(AuthError):
    """Unknown username or wrong password."""


class UserAlreadyExistsError(AuthError):
    """A user with the same normalized identity already exists."""


class InactiveUserError(AuthError):
    """Account disabled, revoked or expired."""


class SessionInvalidError(AuthError):
    """Session missing, revoked or expired."""


class LoginThrottledError(AuthError):
    """Too many failed attempts for this identity/client pair."""

    def __init__(self, retry_after: int):
        super().__init__("Too many failed login attempts")
        self.retry_after = retry_after


_hasher = PasswordHasher()
# Fixed dummy hash keeps unknown-user verification roughly as expensive as a real one.
_DUMMY_HASH = _hasher.hash("samudrasense-dummy-password")


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def issue_token() -> str:
    """Return a URL-safe opaque session token."""
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    """Return the stored digest for a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LoginThrottle:
    """Bounded, process-local failed-login tracker.

    Scope: one API process. Multiple workers do not share counters; this is a
    development/workstation defence, not a distributed rate limiter.
    """

    def __init__(self, max_attempts: int, window_seconds: int, max_entries: int = 1024):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self._entries: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._entries.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        return bucket

    def _evict_if_needed(self) -> None:
        if len(self._entries) <= self.max_entries:
            return
        # Drop the least recently touched entries; bounded memory is the goal.
        overflow = len(self._entries) - self.max_entries
        for key in list(self._entries)[:overflow]:
            self._entries.pop(key, None)

    def retry_after(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            bucket = self._prune(key, now)
            if len(bucket) < self.max_attempts:
                return 0
            return max(1, int(self.window_seconds - (now - bucket[0])) + 1)

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._prune(key, now)
            bucket.append(now)
            self._evict_if_needed()

    def reset(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_login_throttle = LoginThrottle(
    max_attempts=settings.AUTH_LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.AUTH_LOGIN_WINDOW_SECONDS,
    max_entries=settings.AUTH_LOGIN_MAX_TRACKED_KEYS,
)


def throttle_key(username: str, client_ip: Optional[str]) -> str:
    return f"{normalize_username(username)}|{client_ip or 'unknown'}"


def login_retry_after(key: str) -> int:
    return _login_throttle.retry_after(key)


def record_login_failure(key: str) -> None:
    _login_throttle.record_failure(key)


def clear_login_failures(key: str) -> None:
    _login_throttle.reset(key)


def reset_login_throttle() -> None:
    _login_throttle.clear()


def _assign_role(db: Session, user_id: uuid.UUID, role: UserRole, assigned_by: Optional[uuid.UUID] = None) -> None:
    db.add(UserRoleAssignment(user_id=user_id, role=role, assigned_by=assigned_by))
    db.commit()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.exec(select(User).where(User.username == normalize_username(username))).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.exec(select(User).where(User.id == user_id)).first()


def create_user(
    db: Session,
    username: str,
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    role: UserRole = UserRole.VIEWER,
) -> User:
    normalized = normalize_username(username)
    if get_user_by_username(db, normalized):
        raise UserAlreadyExistsError("Username already exists")
    if email:
        existing_email = db.exec(select(User).where(User.email == email)).first()
        if existing_email:
            raise UserAlreadyExistsError("Email already exists")

    user = User(
        username=normalized,
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _assign_role(db, user.id, role)
    return user


def create_admin_user(
    db: Session,
    username: str,
    password: str,
    full_name: Optional[str] = None,
) -> User:
    """Create the first administrator. Refuses to overwrite an existing user."""
    return create_user(
        db,
        username=username,
        password=password,
        full_name=full_name,
        role=UserRole.ADMINISTRATOR,
    )


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Validate credentials. Unknown user and wrong password both raise InvalidCredentialsError."""
    user = get_user_by_username(db, username)
    if not user:
        verify_password(_DUMMY_HASH, password)
        raise InvalidCredentialsError("Invalid username or password")

    if not verify_password(user.password_hash, password):
        raise InvalidCredentialsError("Invalid username or password")

    if not user.is_active or user.revoked_at is not None:
        raise InactiveUserError("Account is not active")
    if user.expires_at is not None and user.expires_at <= utcnow():
        raise InactiveUserError("Account is not active")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    user.updated_at = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(
    db: Session,
    user: User,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> tuple[str, UserSession]:
    """Issue a session for ``user`` and return the raw token once.

    Policy: one active session per user; earlier sessions are revoked.
    """
    now = utcnow()
    db.execute(
        update_active_sessions(user.id),
    )
    db.commit()

    token = issue_token()
    session = UserSession(
        user_id=user.id,
        token_hash=token_digest(token),
        user_agent=(user_agent or "")[:500] or None,
        ip_address=(ip_address or "")[:64] or None,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.AUTH_SESSION_TTL_MINUTES),
        last_activity_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session


def update_active_sessions(user_id: uuid.UUID):
    """Build a statement revoking every active session for ``user_id``."""
    return (
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow(), revoked_reason="superseded")
    )


def validate_session(db: Session, token: Optional[str]) -> tuple[User, UserSession]:
    if not token:
        raise SessionInvalidError("No session token")

    session = db.exec(
        select(UserSession).where(UserSession.token_hash == token_digest(token))
    ).first()
    if not session:
        raise SessionInvalidError("Invalid session")
    if session.revoked_at is not None:
        raise SessionInvalidError("Session revoked")
    if session.expires_at <= utcnow():
        raise SessionInvalidError("Session expired")

    user = get_user_by_id(db, session.user_id)
    if not user or not user.is_active or user.revoked_at is not None:
        raise SessionInvalidError("Account is not active")
    if user.expires_at is not None and user.expires_at <= utcnow():
        raise SessionInvalidError("Account is not active")

    # Touch activity at most once a minute to avoid a write per request.
    if session.last_activity_at <= utcnow() - timedelta(minutes=1):
        session.last_activity_at = utcnow()
        db.add(session)
        db.commit()

    return user, session


def revoke_session(db: Session, token: Optional[str], reason: str = "logout") -> bool:
    if not token:
        return False
    session = db.exec(
        select(UserSession).where(UserSession.token_hash == token_digest(token))
    ).first()
    if not session or session.revoked_at is not None:
        return False
    session.revoked_at = utcnow()
    session.revoked_reason = reason
    db.add(session)
    db.commit()
    return True


def revoke_all_sessions(db: Session, user_id: uuid.UUID, reason: str = "revoked") -> None:
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow(), revoked_reason=reason)
    )
    db.commit()


def get_user_roles(db: Session, user_id: uuid.UUID) -> list[UserRole]:
    rows = db.exec(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.revoked_at.is_(None),
        )
    ).all()
    return [row.role for row in rows]


def user_has_role(roles: list[UserRole], required: UserRole) -> bool:
    """Role check where Administrator implies all roles."""
    return any(role == required or role.implies(required) for role in roles)


def set_user_active(db: Session, user: User, active: bool) -> User:
    user.is_active = active
    user.disabled_at = None if active else utcnow()
    user.updated_at = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    if not active:
        revoke_all_sessions(db, user.id, reason="disabled")
    return user
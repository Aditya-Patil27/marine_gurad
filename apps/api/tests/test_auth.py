"""Focused tests for local authentication and role dependencies.

Unit tests run without a database. Integration tests require a migrated
disposable database via ``TEST_DATABASE_URL`` and are skipped otherwise.
"""
import hashlib
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlmodel import Session, select

from app.api import auth as auth_api
from app.config import settings
from app.models.user import User, UserRole, UserRoleAssignment, UserSession
from app.services import auth as auth_service

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
requires_db = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="requires a migrated disposable database in TEST_DATABASE_URL",
)


# ---------------------------------------------------------------------------
# Unit tests (no database)
# ---------------------------------------------------------------------------

def test_password_hash_is_argon2_and_never_plaintext():
    hashed = auth_service.hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2")
    assert "correct horse battery staple" not in hashed
    assert auth_service.verify_password(hashed, "correct horse battery staple")
    assert not auth_service.verify_password(hashed, "wrong password")


def test_token_digest_is_deterministic_and_not_the_token():
    token = auth_service.issue_token()
    digest = auth_service.token_digest(token)
    assert digest == hashlib.sha256(token.encode()).hexdigest()
    assert digest != token
    assert len(digest) == 64


def test_username_normalization():
    assert auth_service.normalize_username("  Analyst1 ") == "analyst1"


def test_role_hierarchy_is_separated_for_analyst_and_approver():
    # Administrator implies every role.
    assert UserRole.ADMINISTRATOR.implies(UserRole.VIEWER)
    assert UserRole.ADMINISTRATOR.implies(UserRole.ANALYST)
    assert UserRole.ADMINISTRATOR.implies(UserRole.APPROVER)
    # Analyst and Approver both inherit Viewer but not each other.
    assert UserRole.ANALYST.implies(UserRole.VIEWER)
    assert UserRole.APPROVER.implies(UserRole.VIEWER)
    assert not UserRole.ANALYST.implies(UserRole.APPROVER)
    assert not UserRole.APPROVER.implies(UserRole.ANALYST)
    assert UserRole.VIEWER.implies(UserRole.VIEWER)
    assert not UserRole.VIEWER.implies(UserRole.ANALYST)
    assert not UserRole.VIEWER.implies(UserRole.APPROVER)

    assert not auth_service.user_has_role([UserRole.ANALYST], UserRole.APPROVER)
    assert not auth_service.user_has_role([UserRole.APPROVER], UserRole.ANALYST)
    assert auth_service.user_has_role(
        [UserRole.ANALYST, UserRole.APPROVER], UserRole.ANALYST
    )
    assert auth_service.user_has_role(
        [UserRole.ANALYST, UserRole.APPROVER], UserRole.APPROVER
    )
    assert auth_service.user_has_role([UserRole.ADMINISTRATOR], UserRole.ANALYST)
    assert auth_service.user_has_role([UserRole.ADMINISTRATOR], UserRole.APPROVER)
    assert not auth_service.user_has_role([UserRole.VIEWER], UserRole.ADMINISTRATOR)


def test_login_throttle_is_bounded_and_recovers():
    throttle = auth_service.LoginThrottle(max_attempts=2, window_seconds=60, max_entries=2)
    assert throttle.retry_after("a") == 0
    throttle.record_failure("a")
    throttle.record_failure("a")
    assert throttle.retry_after("a") > 0
    throttle.record_failure("b")
    throttle.record_failure("c")
    assert len(throttle._entries) <= 2
    throttle.reset("a")
    assert throttle.retry_after("a") == 0


# ---------------------------------------------------------------------------
# Integration tests (disposable migrated database)
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    from sqlalchemy import create_engine

    engine = create_engine(TEST_DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        engine.dispose()


@pytest.fixture
def client(db):
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    auth_service.reset_login_throttle()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        auth_service.reset_login_throttle()


@pytest.fixture
def role_app(db):
    """Minimal app that exercises the exported role dependencies."""
    from app.database import get_db

    test_app = FastAPI()
    test_app.include_router(auth_api.router, prefix="/api/v1/auth")

    @test_app.get("/viewer")
    def viewer(user=Depends(auth_api.require_viewer)):
        return {"role": "viewer"}

    @test_app.get("/analyst")
    def analyst(user=Depends(auth_api.require_analyst)):
        return {"role": "analyst"}

    @test_app.get("/approver")
    def approver(user=Depends(auth_api.require_approver)):
        return {"role": "approver"}

    @test_app.get("/admin")
    def admin(user=Depends(auth_api.require_admin)):
        return {"role": "admin"}

    test_app.dependency_overrides[get_db] = lambda: db
    return test_app


def _make_user(db, username="analyst1", password="correcthorse123", role=UserRole.ANALYST):
    return auth_service.create_user(db, username=username, password=password, role=role)


def test_bootstrap_refuses_duplicate(db):
    auth_service.create_admin_user(db, "admin", "adminpassword123")
    with pytest.raises(auth_service.UserAlreadyExistsError):
        auth_service.create_admin_user(db, "admin", "anotherpassword123")
    assert len(db.exec(select(User).where(User.username == "admin")).all()) == 1


def test_login_me_logout_and_cookies(db, client):
    _make_user(db)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst1", "password": "correcthorse123"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["username"] == "analyst1"
    assert body["user"]["roles"] == ["ANALYST"]
    assert body["csrf_token"]

    session_cookie = next(
        header for header in response.headers.get_list("set-cookie")
        if header.startswith(f"{settings.AUTH_SESSION_COOKIE_NAME}=")
    )
    csrf_cookie = next(
        header for header in response.headers.get_list("set-cookie")
        if header.startswith(f"{settings.AUTH_CSRF_COOKIE_NAME}=")
    )
    assert "HttpOnly" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=lax" in session_cookie.lower() or "samesite=lax" in session_cookie.lower()

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["username"] == "analyst1"

    # Raw session token must not be recoverable from the database.
    raw_token = client.cookies.get(settings.AUTH_SESSION_COOKIE_NAME)
    stored = db.execute(select(UserSession)).scalars().first()
    assert stored.token_hash != raw_token
    assert stored.token_hash == auth_service.token_digest(raw_token)

    no_csrf = client.post("/api/v1/auth/logout")
    assert no_csrf.status_code == 403

    logged_out = client.post(
        "/api/v1/auth/logout",
        headers={auth_api.CSRF_HEADER: body["csrf_token"]},
    )
    assert logged_out.status_code == 200, logged_out.text
    assert client.get("/api/v1/auth/me").status_code == 401


def test_invalid_login_shares_safe_401(db, client):
    _make_user(db)
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst1", "password": "nope"},
    )
    unknown_user = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "nope"},
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_disabled_and_revoked_accounts_cannot_authenticate(db, client):
    user = _make_user(db)
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "analyst1", "password": "correcthorse123"},
    ).status_code == 200

    auth_service.set_user_active(db, user, False)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "analyst1", "password": "correcthorse123"},
    ).status_code == 401


def test_expired_session_is_rejected(db, client):
    _make_user(db)
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "analyst1", "password": "correcthorse123"},
    ).status_code == 200
    raw_token = client.cookies.get(settings.AUTH_SESSION_COOKIE_NAME)
    session = db.execute(
        select(UserSession).where(
            UserSession.token_hash == auth_service.token_digest(raw_token)
        )
    ).scalars().first()
    db.execute(
        update(UserSession)
        .where(UserSession.id == session.id)
        .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def _login(role_app, username, password="correcthorse123"):
    client = TestClient(role_app)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return client


def test_role_dependencies_allow_and_deny(db, role_app):
    _make_user(db, username="analyst1", role=UserRole.ANALYST)
    _make_user(db, username="approver1", role=UserRole.APPROVER)
    dual = _make_user(db, username="dual1", role=UserRole.ANALYST)
    db.add(UserRoleAssignment(user_id=dual.id, role=UserRole.APPROVER))
    db.commit()
    _make_user(db, username="viewer1", role=UserRole.VIEWER)
    auth_service.create_admin_user(db, "admin1", "adminpassword123")

    # Analyst can investigate/draft but must not approve.
    analyst_client = _login(role_app, "analyst1")
    assert analyst_client.get("/viewer").status_code == 200
    assert analyst_client.get("/analyst").status_code == 200
    assert analyst_client.get("/approver").status_code == 403
    assert analyst_client.get("/admin").status_code == 403

    # Approver can approve/send but must not act as an Analyst.
    approver_client = _login(role_app, "approver1")
    assert approver_client.get("/viewer").status_code == 200
    assert approver_client.get("/analyst").status_code == 403
    assert approver_client.get("/approver").status_code == 200
    assert approver_client.get("/admin").status_code == 403

    # Holding both roles explicitly grants both capabilities.
    dual_login = TestClient(role_app)
    dual_response = dual_login.post(
        "/api/v1/auth/login",
        json={"username": "dual1", "password": "correcthorse123"},
    )
    assert dual_response.status_code == 200, dual_response.text
    assert sorted(dual_response.json()["user"]["roles"]) == ["ANALYST", "APPROVER"]
    assert dual_login.get("/viewer").status_code == 200
    assert dual_login.get("/analyst").status_code == 200
    assert dual_login.get("/approver").status_code == 200
    assert dual_login.get("/admin").status_code == 403

    # Administrator still implies every other role.
    admin_client = _login(role_app, "admin1", "adminpassword123")
    assert admin_client.get("/viewer").status_code == 200
    assert admin_client.get("/analyst").status_code == 200
    assert admin_client.get("/approver").status_code == 200
    assert admin_client.get("/admin").status_code == 200

    # Viewer remains read-only.
    viewer_client = _login(role_app, "viewer1")
    assert viewer_client.get("/viewer").status_code == 200
    assert viewer_client.get("/analyst").status_code == 403
    assert viewer_client.get("/approver").status_code == 403
    assert viewer_client.get("/admin").status_code == 403

    # Anonymous requests are still rejected.
    anonymous = TestClient(role_app)
    assert anonymous.get("/viewer").status_code == 401
    assert anonymous.get("/analyst").status_code == 401
    assert anonymous.get("/approver").status_code == 401


def test_login_throttle_returns_429(db, client, monkeypatch):
    _make_user(db)
    monkeypatch.setattr(auth_service, "_login_throttle", auth_service.LoginThrottle(2, 300))
    payload = {"username": "analyst1", "password": "wrong"}
    assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    throttled = client.post("/api/v1/auth/login", json=payload)
    assert throttled.status_code == 429
    assert int(throttled.headers["Retry-After"]) >= 1
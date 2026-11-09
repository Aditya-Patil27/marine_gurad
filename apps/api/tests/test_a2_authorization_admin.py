"""Focused A2 route-matrix and disposable admin/settings checks."""
import os

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlmodel import Session, select

from app.api import auth as auth_api
from app.database import get_db
from app.main import app
from app.models.user import UserRole, UserRoleAssignment
from app.services import auth as auth_service


PUBLIC_PATHS = {"/", "/health", "/api/v1/auth/login", "/docs", "/redoc", "/openapi.json"}


def test_every_mounted_application_route_has_an_identity_dependency():
    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in PUBLIC_PATHS:
            continue
        dependency_calls = {item.call for item in route.dependant.dependencies}
        assert dependency_calls & {
            auth_api.get_current_user,
            auth_api.require_viewer,
            auth_api.require_analyst,
            auth_api.require_approver,
            auth_api.require_admin,
        }, f"route lacks identity dependency: {sorted(route.methods)} {route.path}"


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable database")
def test_admin_settings_and_user_lifecycle():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    with Session(engine) as db:
        admin = auth_service.create_admin_user(db, "a2admin", "adminpassword123")

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        try:
            assert TestClient(app).get("/api/v1/admin/settings").status_code == 401
            client = TestClient(app)
            login = client.post("/api/v1/auth/login", json={
                "username": "a2admin", "password": "adminpassword123",
            })
            assert login.status_code == 200
            csrf = login.json()["csrf_token"]
            headers = {auth_api.CSRF_HEADER: csrf}

            assert client.post("/api/v1/admin/users", json={
                "username": "denied", "password": "viewerpassword123",
                "roles": [UserRole.VIEWER.value],
            }).status_code == 403

            current = client.get("/api/v1/admin/settings")
            assert current.status_code == 200
            assert "api_key" not in current.text.lower()
            assert "password" not in current.text.lower()

            payload = {
                "organization": "A2 isolated test",
                "aoi_name": "Gulf of Mannar test box",
                "aoi_bbox": [[77.5, 8.0], [79.5, 10.0]],
                "display_timezone": "Asia/Kolkata",
                "alert_threshold": "0.650",
                "report_recipients": ["review@example.test"],
                "retention_days": 90,
            }
            updated = client.put("/api/v1/admin/settings", json=payload, headers=headers)
            assert updated.status_code == 200, updated.text
            assert updated.json()["organization"] == "A2 isolated test"
            assert updated.json()["updated_by"] == str(admin.id)

            created = client.post("/api/v1/admin/users", json={
                "username": "a2viewer", "password": "viewerpassword123",
                "roles": [UserRole.VIEWER.value],
            }, headers=headers)
            assert created.status_code == 201, created.text
            user_id = created.json()["id"]
            assignment = db.exec(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.revoked_at.is_(None),
                )
            ).one()
            assert assignment.assigned_by == admin.id

            viewer_client = TestClient(app)
            viewer_login = viewer_client.post("/api/v1/auth/login", json={
                "username": "a2viewer", "password": "viewerpassword123",
            })
            assert viewer_login.status_code == 200
            assert viewer_client.get("/api/v1/admin/settings").status_code == 403

            disabled = client.patch(
                f"/api/v1/admin/users/{user_id}/active",
                json={"is_active": False}, headers=headers,
            )
            assert disabled.status_code == 200
            assert disabled.json()["is_active"] is False
            assert client.post("/api/v1/auth/login", json={
                "username": "a2viewer", "password": "viewerpassword123",
            }).status_code == 401
        finally:
            app.dependency_overrides.clear()
            db.rollback()
            db.execute(text("UPDATE deployment_settings SET updated_by = NULL WHERE id = 1"))
            db.execute(text("DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE username IN ('a2admin', 'a2viewer', 'denied'))"))
            db.execute(text("DELETE FROM user_role_assignments WHERE user_id IN (SELECT id FROM users WHERE username IN ('a2admin', 'a2viewer', 'denied'))"))
            db.execute(text("DELETE FROM users WHERE username IN ('a2admin', 'a2viewer', 'denied')"))
            db.commit()
    engine.dispose()

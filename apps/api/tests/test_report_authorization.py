"""Report authorization: Viewer/Analyst/Approver duties, CSRF and identity.

No-database tests cover dependency ordering and sign-off identity. Integration
tests need an explicitly supplied, migrated disposable ``TEST_DATABASE_URL``;
they never fall back to the running application database.
"""
import json
import os
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api import auth as auth_api
from app.api import reports
from app.models.user import UserRole, UserRoleAssignment
from app.services import auth as auth_service

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
requires_db = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="requires a migrated disposable database in TEST_DATABASE_URL",
)

PASSWORD = "correcthorse123"
MMSI = 123456789


# ---------------------------------------------------------------------------
# No-database tests
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row

    def one(self):
        return self._row


class _FakeReportDB:
    def __init__(self, row=None):
        self.row = row
        self.updates = []
        self.committed = False

    def execute(self, statement, parameters):
        sql = str(statement)
        if sql.lstrip().upper().startswith("SELECT"):
            return _Result(None if self.row is None else SimpleNamespace(_mapping=dict(self.row)))
        self.updates.append(parameters)
        self.row.update(signed_by=parameters["officer"], signed_at=parameters["now"])
        return _Result(SimpleNamespace(_mapping=dict(self.row)))

    def commit(self):
        self.committed = True


def _report_row(**overrides):
    snapshot = {"mmsi": MMSI, "track": []}
    row = {
        "id": 1,
        "mmsi": MMSI,
        "snapshot": snapshot,
        "sha256": reports.digest(snapshot),
        "signed_at": None,
        "signed_by": None,
        "created_at": datetime.now(timezone.utc),
    }
    row.update(overrides)
    return row


def test_sign_persists_authenticated_username_not_submitted_officer():
    db = _FakeReportDB(_report_row())
    request = reports.SignReport(officer="Forged Officer", reviewed=True)
    result = reports.sign_report(
        1, request, current_user=SimpleNamespace(username="approver1"), db=db
    )

    assert result["signed_by"] == "approver1"
    assert result["integrity_ok"] is True
    assert db.updates[0]["officer"] == "approver1"
    assert "Forged Officer" not in str(result)


def test_sign_without_review_has_no_database_effect():
    class NoTouchDB:
        def execute(self, *args, **kwargs):
            raise AssertionError("denied request must not touch report data")

    with pytest.raises(HTTPException) as exc:
        reports.sign_report(
            1,
            reports.SignReport(officer="Forged Officer", reviewed=False),
            current_user=SimpleNamespace(username="approver1"),
            db=NoTouchDB(),
        )
    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "row, status_code",
    [
        (None, 404),
        (_report_row(sha256="0" * 64), 409),
        (_report_row(signed_at=datetime.now(timezone.utc), signed_by="earlier"), 409),
    ],
)
def test_sign_preserves_not_found_integrity_and_already_signed_errors(row, status_code):
    db = _FakeReportDB(row)
    with pytest.raises(HTTPException) as exc:
        reports.sign_report(
            1,
            reports.SignReport(officer="Forged Officer", reviewed=True),
            current_user=SimpleNamespace(username="approver1"),
            db=db,
        )
    assert exc.value.status_code == status_code
    assert db.updates == []


def _route_dependencies(method, path):
    from app.main import app

    route = next(
        item
        for item in app.routes
        if getattr(item, "path", None) == path and method in item.methods
    )
    return [dependency.call for dependency in route.dependant.dependencies]


def test_identity_dependencies_resolve_before_csrf():
    prefix = "/api/v1/reports"
    assert _route_dependencies("GET", f"{prefix}/")[0] is auth_api.require_viewer
    assert _route_dependencies("GET", f"{prefix}/{{report_id}}")[0] is auth_api.require_viewer
    assert _route_dependencies("GET", f"{prefix}/{{report_id}}/manifest")[0] is auth_api.require_viewer
    assert _route_dependencies("GET", f"{prefix}/{{report_id}}/export.pdf")[0] is auth_api.require_viewer

    create = _route_dependencies("POST", f"{prefix}/")
    assert create[0] is auth_api.require_analyst
    assert create[1] is auth_api.csrf_protect

    sign = _route_dependencies("POST", f"{prefix}/{{report_id}}/sign")
    assert sign[0] is auth_api.require_approver
    assert sign[1] is auth_api.csrf_protect


class _RouteDB:
    """In-memory stand-in for report SQL; route dependencies stay real."""

    def __init__(self):
        self.reports = []
        self.next_id = 1

    def execute(self, statement, parameters):
        sql = str(statement)
        if "FROM incident_reports" in sql and "FOR UPDATE" not in sql:
            return []
        if "sar_detections" in sql:
            return []
        if "INSERT INTO incident_reports" in sql:
            row = {
                "id": self.next_id,
                "mmsi": parameters["mmsi"],
                "snapshot": json.loads(parameters["snapshot"]),
                "sha256": parameters["sha"],
                "signed_at": None,
                "signed_by": None,
                "created_at": datetime.now(timezone.utc),
            }
            self.next_id += 1
            self.reports.append(row)
            return _Result(SimpleNamespace(_mapping=dict(row)))
        if "FOR UPDATE" in sql:
            row = next((item for item in self.reports if item["id"] == parameters["id"]), None)
            return _Result(None if row is None else SimpleNamespace(_mapping=dict(row)))
        if "UPDATE incident_reports" in sql:
            row = next(item for item in self.reports if item["id"] == parameters["id"])
            row["signed_by"] = parameters["officer"]
            row["signed_at"] = parameters["now"]
            return _Result(SimpleNamespace(_mapping=dict(row)))
        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self):
        pass


def test_route_matrix_without_database():
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.schemas.user import UserResponse

    roles = {
        "viewer1": [UserRole.VIEWER],
        "analyst1": [UserRole.ANALYST],
        "approver1": [UserRole.APPROVER],
        "dual1": [UserRole.ANALYST, UserRole.APPROVER],
        "admin1": [UserRole.ADMINISTRATOR],
    }

    def fake_current_user(request: Request):
        username = request.headers.get("X-Test-User")
        if not username:
            raise HTTPException(401, "Not authenticated")
        return UserResponse(
            id="00000000-0000-0000-0000-000000000001",
            username=username,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            roles=roles[username],
        )

    db = _RouteDB()
    app = FastAPI()
    app.include_router(reports.router, prefix="/api/v1/reports")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[auth_api.get_current_user] = fake_current_user

    def headers(user=None, token=None):
        value = {"X-Test-User": user} if user else {}
        if token:
            value[auth_api.CSRF_HEADER] = token
        return value

    def cookies(token=None):
        return {auth_api.CSRF_COOKIE: token} if token else {}

    with TestClient(app) as client:
        with patch.object(reports, "get_vessel", return_value=_synthetic_vessel()):
            anonymous = client.post("/api/v1/reports/", json={"mmsi": MMSI})
            assert anonymous.status_code == 401

            for user in ("viewer1", "approver1"):
                denied = client.post(
                    "/api/v1/reports/",
                    json={"mmsi": MMSI},
                    headers=headers(user, "token"),
                    cookies=cookies("token"),
                )
                assert denied.status_code == 403
            assert db.reports == []

            # CSRF absent or mismatched is 403 for an authorised Analyst.
            assert client.post(
                "/api/v1/reports/",
                json={"mmsi": MMSI},
                headers=headers("analyst1"),
                cookies=cookies("token"),
            ).status_code == 403
            assert client.post(
                "/api/v1/reports/",
                json={"mmsi": MMSI},
                headers=headers("analyst1", "wrong"),
                cookies=cookies("token"),
            ).status_code == 403
            assert db.reports == []

            drafted = client.post(
                "/api/v1/reports/",
                json={"mmsi": MMSI},
                headers=headers("analyst1", "token"),
                cookies=cookies("token"),
            )
            assert drafted.status_code == 201, drafted.text
            report_id = drafted.json()["id"]

            # Analyst and Viewer cannot approve.
            for user in ("analyst1", "viewer1"):
                denied = client.post(
                    f"/api/v1/reports/{report_id}/sign",
                    json={"officer": "Forged Officer", "reviewed": True},
                    headers=headers(user, "token"),
                    cookies=cookies("token"),
                )
                assert denied.status_code == 403
            # Approver with absent or wrong CSRF cannot approve.
            assert client.post(
                f"/api/v1/reports/{report_id}/sign",
                json={"officer": "Forged Officer", "reviewed": True},
                headers=headers("approver1"),
                cookies=cookies("token"),
            ).status_code == 403
            assert client.post(
                f"/api/v1/reports/{report_id}/sign",
                json={"officer": "Forged Officer", "reviewed": True},
                headers=headers("approver1", "wrong"),
                cookies=cookies("token"),
            ).status_code == 403
            assert db.reports[0]["signed_at"] is None

            approved = client.post(
                f"/api/v1/reports/{report_id}/sign",
                json={"officer": "Forged Officer", "reviewed": True},
                headers=headers("approver1", "token"),
                cookies=cookies("token"),
            )
            assert approved.status_code == 200, approved.text
            assert approved.json()["signed_by"] == "approver1"
            assert "Forged Officer" not in str(approved.json())

            for user in ("admin1", "dual1"):
                created = client.post(
                    "/api/v1/reports/",
                    json={"mmsi": MMSI},
                    headers=headers(user, "token"),
                    cookies=cookies("token"),
                )
                assert created.status_code == 201, created.text
                signed = client.post(
                    f"/api/v1/reports/{created.json()['id']}/sign",
                    json={"officer": "Forged Officer", "reviewed": True},
                    headers=headers(user, "token"),
                    cookies=cookies("token"),
                )
                assert signed.status_code == 200
                assert signed.json()["signed_by"] == user

            anonymous_sign = client.post(
                "/api/v1/reports/1/sign",
                json={"officer": "Anonymous", "reviewed": True},
            )
            assert anonymous_sign.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests (disposable migrated database)
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    from sqlalchemy import create_engine
    from sqlmodel import Session

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
def accounts(db):
    created = {}
    for username, role in (
        ("viewer1", UserRole.VIEWER),
        ("analyst1", UserRole.ANALYST),
        ("approver1", UserRole.APPROVER),
        ("admin1", UserRole.ADMINISTRATOR),
    ):
        created[username] = auth_service.create_user(
            db, username=username, password=PASSWORD, role=role
        )
    dual = auth_service.create_user(
        db, username="dual1", password=PASSWORD, role=UserRole.ANALYST
    )
    db.add(UserRoleAssignment(user_id=dual.id, role=UserRole.APPROVER))
    db.commit()
    created["dual1"] = dual
    return created


@pytest.fixture
def clients(db):
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    stack = ExitStack()
    app.dependency_overrides[get_db] = lambda: db
    auth_service.reset_login_throttle()

    def make(username=None):
        client = stack.enter_context(TestClient(app))
        if username is None:
            return client, None
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": PASSWORD},
        )
        assert response.status_code == 200, response.text
        return client, response.json()["csrf_token"]

    try:
        yield make
    finally:
        app.dependency_overrides.clear()
        auth_service.reset_login_throttle()
        stack.close()


def _synthetic_vessel():
    return {
        "mmsi": MMSI,
        "name": "Synthetic vessel",
        "vessel_type": "cargo",
        "length": 100,
        "last_seen": "2026-11-04T00:00:00Z",
        "position": {"lat": 8.9, "lon": 78.9},
        "course": 90,
        "speed": 5,
        "score": 0.2,
        "level": "low",
        "state": "tracked",
        "headline": "Synthetic fixture",
        "reasons": [],
        "dark": False,
        "track": [{"t": "2026-11-04T00:00:00Z", "lat": 8.9, "lon": 78.9, "speed": 5, "course": 90}],
    }


def _create_report(client, csrf, **payload):
    body = {"mmsi": MMSI, **payload}
    with patch.object(reports, "get_vessel", return_value=_synthetic_vessel()):
        response = client.post(
            "/api/v1/reports/",
            json=body,
            headers={auth_api.CSRF_HEADER: csrf},
        )
    return response


def _sign(client, csrf, report_id, officer="Typed Officer", reviewed=True):
    return client.post(
        f"/api/v1/reports/{report_id}/sign",
        json={"officer": officer, "reviewed": reviewed},
        headers={auth_api.CSRF_HEADER: csrf},
    )


def _count_reports(db):
    return db.execute(text("SELECT count(*) FROM incident_reports")).scalar_one()


@requires_db
def test_anonymous_is_rejected_everywhere(clients):
    client, _ = clients()
    assert client.get("/api/v1/reports/").status_code == 401
    assert client.post("/api/v1/reports/", json={"mmsi": MMSI}).status_code == 401
    assert client.post(
        "/api/v1/reports/1/sign", json={"officer": "Anonymous", "reviewed": True}
    ).status_code == 401


@requires_db
def test_role_matrix_and_denied_requests_leave_data_unchanged(db, accounts, clients):
    viewer, viewer_csrf = clients("viewer1")
    analyst, analyst_csrf = clients("analyst1")
    approver, approver_csrf = clients("approver1")
    dual, dual_csrf = clients("dual1")
    admin, admin_csrf = clients("admin1")

    assert viewer.get("/api/v1/reports/").status_code == 200
    before = _count_reports(db)

    # Viewer and Approver-only cannot draft; denied requests write nothing.
    assert _create_report(viewer, viewer_csrf).status_code == 403
    assert _create_report(approver, approver_csrf).status_code == 403
    assert _count_reports(db) == before

    drafted = _create_report(analyst, analyst_csrf)
    assert drafted.status_code == 201, drafted.text
    report_id = drafted.json()["id"]
    assert drafted.json()["signed_at"] is None

    # Analyst and Viewer cannot approve.
    assert _sign(analyst, analyst_csrf, report_id).status_code == 403
    assert _sign(viewer, viewer_csrf, report_id).status_code == 403
    assert _sign(approver, "wrong-csrf", report_id).status_code == 403
    assert db.execute(
        text("SELECT signed_at FROM incident_reports WHERE id = :id"), {"id": report_id}
    ).scalar_one() is None

    # Approval identity is the authenticated user, never the typed officer.
    approved = _sign(approver, approver_csrf, report_id, officer="Forged Officer")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["signed_by"] == "approver1"
    assert "Forged Officer" not in str(body)
    signed_at = datetime.fromisoformat(body["signed_at"])
    assert signed_at.tzinfo is not None and signed_at.utcoffset() == timedelta(0)

    duplicate = _sign(approver, approver_csrf, report_id)
    assert duplicate.status_code == 409

    # Administrator implies Analyst and Approver; explicit dual role grants both.
    admin_report = _create_report(admin, admin_csrf)
    assert admin_report.status_code == 201, admin_report.text
    admin_signed = _sign(admin, admin_csrf, admin_report.json()["id"])
    assert admin_signed.status_code == 200
    assert admin_signed.json()["signed_by"] == "admin1"

    dual_report = _create_report(dual, dual_csrf)
    assert dual_report.status_code == 201, dual_report.text
    dual_signed = _sign(dual, dual_csrf, dual_report.json()["id"])
    assert dual_signed.status_code == 200
    assert dual_signed.json()["signed_by"] == "dual1"


@requires_db
def test_csrf_is_required_and_denied_requests_write_nothing(db, accounts, clients):
    analyst, csrf = clients("analyst1")
    approver, approver_csrf = clients("approver1")
    before = _count_reports(db)

    assert analyst.post("/api/v1/reports/", json={"mmsi": MMSI}).status_code == 403
    assert analyst.post(
        "/api/v1/reports/",
        json={"mmsi": MMSI},
        headers={auth_api.CSRF_HEADER: "wrong"},
    ).status_code == 403
    assert _count_reports(db) == before

    created = _create_report(analyst, csrf)
    assert created.status_code == 201
    report_id = created.json()["id"]

    assert approver.post(
        f"/api/v1/reports/{report_id}/sign",
        json={"officer": "Forged Officer", "reviewed": True},
    ).status_code == 403
    assert approver.post(
        f"/api/v1/reports/{report_id}/sign",
        json={"officer": "Forged Officer", "reviewed": True},
        headers={auth_api.CSRF_HEADER: "wrong"},
    ).status_code == 403
    assert db.execute(
        text("SELECT signed_at FROM incident_reports WHERE id = :id"), {"id": report_id}
    ).scalar_one() is None

    approved = _sign(approver, approver_csrf, report_id)
    assert approved.status_code == 200
    assert approved.json()["signed_by"] == "approver1"


@requires_db
def test_sst_context_and_checksum_tamper_detection(db, accounts, clients):
    analyst, csrf = clients("analyst1")
    approver, approver_csrf = clients("approver1")
    context = {
        "status": "available",
        "dataset": "synthetic-sst",
        "mode": "historical",
        "values": [{"temperature_c": 28.0, "observed_at": "2026-10-19T00:00:00Z"}],
    }
    with patch.object(reports, "load_satellite_observations", return_value=context):
        created = _create_report(analyst, csrf, include_regional_ocean_context=True)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["integrity_ok"] is True
    assert body["snapshot"]["regional_ocean_context"]["dataset"] == "synthetic-sst"
    assert "not necessarily concurrent" in body["snapshot"]["regional_ocean_context"]["association"]

    report_id = body["id"]
    db.execute(
        text("UPDATE incident_reports SET sha256 = :hash WHERE id = :id"),
        {"hash": "0" * 64, "id": report_id},
    )
    db.commit()

    listed = next(item for item in analyst.get("/api/v1/reports/").json() if item["id"] == report_id)
    assert listed["integrity_ok"] is False
    assert _sign(approver, approver_csrf, report_id).status_code == 409
    assert db.execute(
        text("SELECT signed_at FROM incident_reports WHERE id = :id"), {"id": report_id}
    ).scalar_one() is None

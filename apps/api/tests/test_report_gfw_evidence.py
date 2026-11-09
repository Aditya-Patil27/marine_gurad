"""A selected historical GFW event is bound to the hashed report/case path."""
import asyncio
import json
import os
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api import cases, gfw, reports

MMSI = 234567892
PAGE = {
    "source": "Global Fishing Watch",
    "dataset": "public-global-fishing-events:latest",
    "source_url": "https://example.com",
    "retrieved_at": "2026-11-07T00:00:00Z",
    "requested_region": {},
    "requested_start": "2024-01-01",
    "requested_end_exclusive": "2024-02-01",
    "limitations": "Historical, inferred apparent fishing events; not live tracking, proven fishing or evidence of illegality.",
    "data": {"entries": [{
        "id": "event-1",
        "type": "fishing",
        "start": "2024-01-03T00:00:00Z",
        "end": "2024-01-03T04:00:00Z",
        "position": {"lat": 8.5, "lon": 78.5},
        "vessel": {"id": "v1", "name": "Example", "ssvid": str(MMSI), "flag": "IN"},
    }]},
}
SST = {
    "status": "available",
    "dataset": "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE",
    "mode": "historical",
    "values": [{"observed_at": "2026-10-19T00:00:00Z", "temperature_c": 28.0}],
}


class FakeDB:
    def execute(self, statement, parameters):
        if "sar_detections" in str(statement):
            return []
        snapshot = json.loads(parameters["snapshot"])
        return SimpleNamespace(one=lambda: SimpleNamespace(_mapping={"snapshot": snapshot, "sha256": parameters["sha"]}))

    def commit(self):
        pass


def _request(**overrides):
    values = {
        "mmsi": MMSI,
        "gfw_event_id": "event-1",
        "gfw_start_date": date(2024, 1, 1),
        "gfw_end_date": date(2024, 2, 1),
    }
    values.update(overrides)
    return reports.CreateReport(**values)


def test_selected_event_is_hashed_with_source_ids_dates_and_independent_sst():
    request = _request(include_gfw_ocean_context=True)
    with patch.object(gfw, "regional_events", AsyncMock(return_value=PAGE)), \
            patch.object(gfw, "load_satellite_observations", return_value=SST):
        evidence = asyncio.run(reports.load_gfw_evidence(request))
    with patch.object(reports, "get_vessel", return_value={"mmsi": MMSI}):
        result = reports.create_report(request, gfw_evidence=evidence, db=FakeDB())

    bound = result["snapshot"]["gfw_event_evidence"]
    assert bound["snapshot"]["event"]["id"] == "event-1"
    assert bound["snapshot"]["event"]["start"] == "2024-01-03T00:00:00Z"
    assert bound["snapshot"]["event"]["position"] == {"lat": 8.5, "lon": 78.5}
    assert bound["snapshot"]["requested_start"] == "2024-01-01"
    assert bound["snapshot"]["requested_end_exclusive"] == "2024-02-01"
    assert "not live tracking" in bound["snapshot"]["limitations"]
    context = bound["snapshot"]["regional_ocean_context"]
    assert context["values"][0]["observed_at"] == "2026-10-19T00:00:00Z"
    assert "not necessarily concurrent" in context["association"]
    assert "not a vessel track" in bound["association"]
    assert result["integrity_ok"]

    result["snapshot"]["gfw_event_evidence"]["snapshot"]["event"]["id"] = "changed"
    assert reports.digest(result["snapshot"]) != result["sha256"]


def test_report_without_source_evidence_stays_compatible():
    with patch.object(reports, "get_vessel", return_value={"mmsi": MMSI}):
        result = reports.create_report(reports.CreateReport(mmsi=MMSI), db=FakeDB())
    assert "gfw_event_evidence" not in result["snapshot"]
    assert result["integrity_ok"]


def test_event_only_report_hashes_unavailable_ais_and_skips_vessel_lookup():
    request = _request(event_only=True)
    with patch.object(gfw, "regional_events", AsyncMock(return_value=PAGE)):
        evidence = asyncio.run(reports.load_gfw_evidence(request))
    with patch.object(reports, "get_vessel", side_effect=AssertionError("no vessel lookup")):
        result = reports.create_report(request, gfw_evidence=evidence, db=FakeDB())
    snapshot = result["snapshot"]
    assert snapshot["evidence_basis"] == "gfw_event_only"
    assert snapshot["ais_evidence"]["status"] == "unavailable"
    assert snapshot["assessment"]["status"] == "unavailable"
    assert "persisted_assessment" not in snapshot
    assert snapshot["gfw_event_evidence"]["sha256"] == evidence["sha256"]
    assert "not a vessel track" in snapshot["limitations"]
    assert result["integrity_ok"]
    snapshot["gfw_event_evidence"]["snapshot"]["event"]["id"] = "changed"
    assert reports.digest(snapshot) != result["sha256"]


@pytest.mark.parametrize("overrides", [
    {"assessment_id": uuid4()},
    {"window_start": datetime(2024, 1, 1), "window_end": datetime(2024, 2, 1)},
    {"include_weather_context": True},
    {"gfw_event_id": None, "gfw_start_date": None, "gfw_end_date": None},
])
def test_event_only_rejects_conflicting_basis_before_provider_work(overrides):
    with patch.object(gfw, "regional_events", side_effect=AssertionError("provider called")):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(reports.load_gfw_evidence(_request(event_only=True, **overrides)))
    assert exc.value.status_code == 422


def test_case_creation_requires_exactly_one_basis():
    for payload in (
        cases.CreateCase(title="No basis"),
        cases.CreateCase(title="Both", assessment_id=uuid4(), report_id=1),
    ):
        with pytest.raises(HTTPException) as exc:
            cases.create_case(payload, user=SimpleNamespace(username="analyst"), db=object())
        assert exc.value.status_code == 422



def test_missing_or_mismatched_event_fails_before_any_insert():
    missing = PAGE | {"data": {"entries": []}}
    with patch.object(gfw, "regional_events", AsyncMock(return_value=missing)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(reports.load_gfw_evidence(_request()))
    assert exc.value.status_code == 404

    wrong_vessel = PAGE | {"data": {"entries": [
        {**PAGE["data"]["entries"][0], "vessel": {"id": "v1", "ssvid": "999999999"}}
    ]}}
    with patch.object(gfw, "regional_events", AsyncMock(return_value=wrong_vessel)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(reports.load_gfw_evidence(_request()))
    assert exc.value.status_code == 409


def test_unavailable_sst_fails_before_any_insert():
    with patch.object(gfw, "regional_events", AsyncMock(return_value=PAGE)), \
            patch.object(gfw, "load_satellite_observations", side_effect=HTTPException(503)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(reports.load_gfw_evidence(_request(include_gfw_ocean_context=True)))
    assert exc.value.status_code == 503


def test_route_binds_the_event_and_writes_no_report_on_failure():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.database import get_db

    class DB:
        def __init__(self):
            self.inserted = []

        def execute(self, statement, parameters):
            if "sar_detections" in str(statement):
                return []
            if "INSERT INTO incident_reports" in str(statement):
                snapshot = json.loads(parameters["snapshot"])
                self.inserted.append(snapshot)
                return SimpleNamespace(one=lambda: SimpleNamespace(_mapping={"snapshot": snapshot, "sha256": parameters["sha"]}))
            raise AssertionError(str(statement))

        def commit(self):
            pass

    db = DB()
    app = FastAPI()
    app.include_router(reports.router, prefix="/reports")
    app.dependency_overrides[reports.require_analyst] = lambda: SimpleNamespace(username="analyst")
    app.dependency_overrides[reports.csrf_protect] = lambda: None
    app.dependency_overrides[get_db] = lambda: db
    body = {"mmsi": MMSI, "gfw_event_id": "event-1",
            "gfw_start_date": "2024-01-01", "gfw_end_date": "2024-02-01"}
    with TestClient(app) as client, \
            patch.object(reports, "get_vessel", return_value={"mmsi": MMSI}), \
            patch.object(gfw, "regional_events", AsyncMock(return_value=PAGE)):
        created = client.post("/reports/", json=body)
        assert created.status_code == 201, created.text
        assert created.json()["snapshot"]["gfw_event_evidence"]["snapshot"]["event"]["id"] == "event-1"

        before = len(db.inserted)
        with patch.object(gfw, "regional_events", AsyncMock(return_value=PAGE | {"data": {"entries": []}})):
            failed = client.post("/reports/", json=body)
        assert failed.status_code == 404
        assert len(db.inserted) == before


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL")
def test_event_evidence_survives_into_a_case_revision():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    assessment_id = uuid4()
    user = SimpleNamespace(username="analyst")
    request = _request(assessment_id=assessment_id)
    evidence = gfw.canonical_event_evidence(PAGE, "event-1")
    try:
        with Session(engine) as db:
            db.execute(text("""INSERT INTO vessel_assessments (id,mmsi,rule_version,source_mode,evaluated_at,
                lookback_hours,score,level,factors,checks) VALUES (:id,:mmsi,'v1','unknown',now(),24,0.2,'low','[]','[]')"""),
                {"id": str(assessment_id), "mmsi": MMSI})
            db.commit()
            with patch.object(reports, "get_vessel", return_value={"mmsi": MMSI}):
                created = reports.create_report(request, gfw_evidence=evidence, db=db)
            case = cases.create_case(cases.CreateCase(assessment_id=assessment_id, title="GFW review"), user=user, db=db)
            revision = cases.add_revision(
                case["id"], cases.AddRevision(report_id=created["id"], expected_version=0), user=user, db=db
            )
            assert revision["report_sha256"] == created["sha256"]
            detail = cases.get_case(case["id"], db=db)
            assert detail["revisions"][0]["integrity_ok"]
            persisted = detail["revisions"][0]["snapshot"]["gfw_event_evidence"]
            assert persisted["sha256"] == evidence["sha256"]
            assert persisted["snapshot"]["event"]["id"] == "event-1"
            assert persisted["snapshot"]["event"]["start"] == "2024-01-03T00:00:00Z"
            assert "not live tracking" in persisted["snapshot"]["limitations"]
    finally:
        engine.dispose()


def _insert_report(db, snapshot, mmsi=MMSI):
    return db.execute(text("""INSERT INTO incident_reports (mmsi, snapshot, sha256)
        VALUES (:mmsi, CAST(:snapshot AS jsonb), :sha) RETURNING id"""),
        {"mmsi": mmsi, "snapshot": json.dumps(snapshot), "sha": reports.digest(snapshot)}).one().id


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL")
def test_event_only_case_and_revision_round_trip_on_migration_014():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    user = SimpleNamespace(username="analyst")
    evidence = gfw.canonical_event_evidence(PAGE, "event-1")
    try:
        with Session(engine) as db:
            nullable = db.execute(text("""SELECT is_nullable FROM information_schema.columns
                WHERE table_name = 'investigation_cases' AND column_name = 'assessment_id'""")).scalar()
            assert nullable == "YES", "migration 014 did not apply"

            # No vessel row exists for MMSI: an event-only report must not need one.
            created = reports.create_report(_request(event_only=True), gfw_evidence=evidence, db=db)
            assert not db.execute(text("SELECT 1 FROM vessel_tracks WHERE mmsi = :mmsi"), {"mmsi": MMSI}).first()
            assert created["snapshot"]["evidence_basis"] == "gfw_event_only"

            case = cases.create_case(cases.CreateCase(report_id=created["id"], title="GFW review"),
                                     user=user, db=db)
            assert case["assessment_id"] is None and case["version"] == 1 and case["mmsi"] == MMSI
            detail = cases.get_case(case["id"], db=db)
            assert [(r["version"], r["integrity_ok"]) for r in detail["revisions"]] == [(1, True)]
            assert detail["revisions"][0]["report_sha256"] == created["sha256"]
            assert [event["event"] for event in detail["events"]] == ["opened"]

            second = reports.create_report(_request(event_only=True), gfw_evidence=evidence, db=db)
            revision = cases.add_revision(case["id"], cases.AddRevision(report_id=second["id"], expected_version=1),
                                          user=user, db=db)
            assert revision["version"] == 2

            assessment_id = uuid4()
            db.execute(text("""INSERT INTO vessel_assessments (id,mmsi,rule_version,source_mode,evaluated_at,
                lookback_hours,score,level,factors,checks) VALUES (:id,:mmsi,'v1','unknown',now(),24,0.2,'low','[]','[]')"""),
                {"id": str(assessment_id), "mmsi": 234567894})
            db.commit()
            backed = cases.create_case(cases.CreateCase(assessment_id=assessment_id, title="Assessment review"),
                                       user=user, db=db)
            assert str(backed["assessment_id"]) == str(assessment_id) and backed["version"] == 0
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL")
def test_event_only_case_rejects_unverified_reports_before_insert():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    user = SimpleNamespace(username="analyst")
    evidence = gfw.canonical_event_evidence(PAGE, "event-1")
    try:
        with Session(engine) as db:
            missing = cases.CreateCase(report_id=999999999, title="Missing")
            with pytest.raises(HTTPException) as not_found:
                cases.create_case(missing, user=user, db=db)
            assert not_found.value.status_code == 404

            backed = _insert_report(db, {"mmsi": MMSI, "persisted_assessment": {"id": str(uuid4())}})
            with pytest.raises(HTTPException) as wrong_basis:
                cases.create_case(cases.CreateCase(report_id=backed, title="Wrong basis"), user=user, db=db)
            assert wrong_basis.value.status_code == 409

            tampered = _insert_report(db, {"mmsi": MMSI, "evidence_basis": "gfw_event_only",
                                           "gfw_event_evidence": evidence})
            db.execute(text("UPDATE incident_reports SET snapshot = jsonb_set(snapshot, '{evidence_basis}', '\"changed\"') WHERE id = :id"),
                       {"id": tampered})
            db.commit()
            with pytest.raises(HTTPException) as integrity:
                cases.create_case(cases.CreateCase(report_id=tampered, title="Tampered"), user=user, db=db)
            assert integrity.value.status_code == 409

            bad_evidence = json.loads(json.dumps(evidence))
            bad_evidence["snapshot"]["event"]["id"] = "changed"
            bad_canonical = _insert_report(db, {"mmsi": MMSI, "evidence_basis": "gfw_event_only",
                                                "gfw_event_evidence": bad_evidence})
            with pytest.raises(HTTPException) as canonical:
                cases.create_case(cases.CreateCase(report_id=bad_canonical, title="Bad canonical"), user=user, db=db)
            assert canonical.value.status_code == 409

            other = gfw.canonical_event_evidence(
                PAGE | {"data": {"entries": [PAGE["data"]["entries"][0] | {"vessel": {"id": "v1", "ssvid": "999999999"}}]}},
                "event-1",
            )
            mismatched = _insert_report(db, {"mmsi": MMSI, "evidence_basis": "gfw_event_only",
                                             "gfw_event_evidence": other})
            with pytest.raises(HTTPException) as wrong_vessel:
                cases.create_case(cases.CreateCase(report_id=mismatched, title="Wrong vessel"), user=user, db=db)
            assert wrong_vessel.value.status_code == 409

            assert not db.execute(text("SELECT 1 FROM investigation_cases WHERE title IN ('Missing','Wrong basis','Tampered','Bad canonical','Wrong vessel')")).first()
            db.rollback()
    finally:
        engine.dispose()

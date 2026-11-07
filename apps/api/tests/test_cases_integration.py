"""Critical case revision behavior on an explicitly supplied disposable database."""
import json
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api import cases
from app.api.reports import digest


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL")
def test_case_revision_identity_concurrency_and_integrity():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    assessment_id = uuid4()
    user = SimpleNamespace(username="analyst")
    try:
        with Session(engine) as db:
            db.execute(text("""INSERT INTO vessel_assessments (id,mmsi,rule_version,source_mode,evaluated_at,
                lookback_hours,score,level,factors,checks) VALUES (:id,234567890,'v1','unknown',now(),24,0.2,'low','[]','[]')"""),
                {"id": str(assessment_id)})
            snapshot = {"mmsi": 234567890, "persisted_assessment": {"id": str(assessment_id)}}
            row = db.execute(text("""INSERT INTO incident_reports (mmsi,snapshot,sha256)
                VALUES (234567890, CAST(:snapshot AS jsonb), :sha) RETURNING id"""),
                {"snapshot": json.dumps(snapshot), "sha": digest(snapshot)}).one()
            db.commit()
            case = cases.create_case(cases.CreateCase(assessment_id=assessment_id, title="Review"), user=user, db=db)
            revision = cases.add_revision(case["id"], cases.AddRevision(report_id=row.id, expected_version=0), user=user, db=db)
            assert revision["version"] == 1 and revision["created_by"] == "analyst"
            assert cases.get_case(case["id"], db=db)["revisions"][0]["integrity_ok"]
            with pytest.raises(HTTPException) as conflict:
                cases.add_revision(case["id"], cases.AddRevision(report_id=row.id, expected_version=0), user=user, db=db)
            assert conflict.value.status_code == 409
            db.rollback()
            db.execute(text("UPDATE incident_reports SET snapshot = '{}'::jsonb WHERE id = :id"), {"id": row.id})
            db.commit()
            assert not cases.get_case(case["id"], db=db)["revisions"][0]["integrity_ok"]
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL")
def test_case_creation_and_status_events_are_atomic_and_versioned():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    assessment_id = uuid4()
    user = SimpleNamespace(username="analyst")
    try:
        with Session(engine) as db:
            db.execute(text("""INSERT INTO vessel_assessments (id,mmsi,rule_version,source_mode,evaluated_at,
                lookback_hours,score,level,factors,checks) VALUES (:id,234567891,'v1','unknown',now(),24,0.2,'low','[]','[]')"""),
                {"id": str(assessment_id)})
            db.commit()
            case = cases.create_case(cases.CreateCase(assessment_id=assessment_id, title="Review"), user=user, db=db)
            events = db.execute(
                text("SELECT event, actor FROM case_events WHERE case_id = :id ORDER BY id"),
                {"id": str(case["id"])},
            ).all()
            assert [(event.event, event.actor) for event in events] == [("opened", "analyst")]

            closed = cases.close_case(
                case["id"], cases.StatusTransition(expected_version=0, note="done"),
                user=user, db=db,
            )
            assert closed["status"] == "closed" and closed["version"] == 1
            with pytest.raises(HTTPException) as stale:
                cases.close_case(case["id"], cases.StatusTransition(expected_version=0), user=user, db=db)
            assert stale.value.status_code == 409
            reopened = cases.reopen_case(
                case["id"], cases.StatusTransition(expected_version=1),
                user=user, db=db,
            )
            assert reopened["status"] == "open" and reopened["version"] == 2
            assert [event["event"] for event in reopened["events"]] == ["opened", "closed", "reopened"]
            with pytest.raises(HTTPException) as invalid:
                cases.reopen_case(case["id"], cases.StatusTransition(expected_version=2), user=user, db=db)
            assert invalid.value.status_code == 409
    finally:
        engine.dispose()

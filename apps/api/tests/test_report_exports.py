"""Focused checks for canonical reviewed-report retrieval and export."""
from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api import reports


MMSI = 123456789


class _Result:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class _SourceDB:
    def __init__(self, assessment=None):
        self.assessment = assessment

    def execute(self, statement, _parameters):
        if "vessel_assessments" in str(statement):
            return _Result(self.assessment)
        raise AssertionError(str(statement))


def _row(snapshot, *, canonical=True, signed=True):
    data = {
        "id": 44,
        "mmsi": MMSI,
        "snapshot": snapshot,
        "sha256": reports.digest(snapshot),
        "signed_at": "2026-11-08T00:00:00+00:00" if signed else None,
        "signed_by": "approver",
    }
    if canonical:
        data["canonical_snapshot"] = reports.canonical_bytes(snapshot)
    return SimpleNamespace(_mapping=data)


def test_manifest_preserves_canonical_bytes_and_decimal_scale_and_pdf_is_deterministic():
    snapshot = {"mmsi": MMSI, "value": 59.0, "limitations": "Review required."}
    manifest = reports._validated_manifest(_row(snapshot), _SourceDB())

    assert '"value":59.0' in manifest["canonical_json"]
    assert manifest["canonical_sha256"] == reports.digest(snapshot)
    assert reports._reviewed_pdf(manifest) == reports._reviewed_pdf(manifest)
    assert b"Report ID: 44" in reports._reviewed_pdf(manifest)


@pytest.mark.parametrize(
    "snapshot, db",
    [
        ({"mmsi": MMSI, "value": 59.0}, _SourceDB()),
        (
            {"mmsi": MMSI, "persisted_assessment": {"id": "missing"}},
            _SourceDB(),
        ),
    ],
)
def test_tampered_or_unreferenced_snapshot_cannot_build_manifest(snapshot, db):
    row = _row(snapshot)
    row._mapping["canonical_snapshot"] = b'{"mmsi":123456789,"value":59}'
    with pytest.raises(HTTPException) as exc:
        reports._validated_manifest(row, db)
    assert exc.value.status_code == 409


def test_unreferenced_assessment_cannot_build_manifest():
    snapshot = {"mmsi": MMSI, "persisted_assessment": {"id": "missing"}}
    with pytest.raises(HTTPException) as exc:
        reports._validated_manifest(_row(snapshot), _SourceDB())
    assert exc.value.status_code == 409


def test_stale_approval_is_rejected_before_signing():
    class DB:
        def __init__(self):
            self.updated = False
            self.row = _row({"mmsi": MMSI}, canonical=False)

        def execute(self, statement, _parameters):
            if str(statement).lstrip().startswith("SELECT"):
                return _Result(self.row)
            self.updated = True
            return _Result(self.row)

    db = DB()
    with pytest.raises(HTTPException) as exc:
        reports.sign_report(
            44,
            reports.SignReport(officer="ignored", reviewed=True, expected_sha256="0" * 64),
            current_user=SimpleNamespace(username="approver"),
            db=db,
        )
    assert exc.value.status_code == 409
    assert not db.updated


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires a migrated disposable TEST_DATABASE_URL")
def test_database_round_trip_keeps_canonical_decimal_bytes_and_detects_tampering():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    snapshot = {"mmsi": MMSI, "value": 59.0}
    canonical = reports.canonical_bytes(snapshot)
    try:
        with Session(engine) as db:
            report_id = db.execute(
                text("""INSERT INTO incident_reports (mmsi, snapshot, sha256, canonical_snapshot)
                    VALUES (:mmsi, CAST(:snapshot AS jsonb), :sha, :canonical) RETURNING id"""),
                {
                    "mmsi": MMSI,
                    "snapshot": canonical.decode("utf-8"),
                    "sha": reports.digest(snapshot),
                    "canonical": canonical,
                },
            ).scalar_one()
            db.commit()
            row = db.execute(text("SELECT * FROM incident_reports WHERE id = :id"), {"id": report_id}).first()
            manifest = reports._validated_manifest(row, db)
            assert '"value":59.0' in manifest["canonical_json"]

            db.execute(
                text("UPDATE incident_reports SET snapshot = CAST(:snapshot AS jsonb) WHERE id = :id"),
                {"snapshot": '{"mmsi":123456789,"value":59}', "id": report_id},
            )
            db.commit()
            tampered = db.execute(text("SELECT * FROM incident_reports WHERE id = :id"), {"id": report_id}).first()
            with pytest.raises(HTTPException) as exc:
                reports._validated_manifest(tampered, db)
            assert exc.value.status_code == 409
    finally:
        engine.dispose()

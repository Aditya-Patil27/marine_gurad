"""Immutable evidence snapshots and local officer sign-off; no dispatch."""
import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.vessels import get_vessel
from app.database import get_db

router = APIRouter()


def digest(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def report(row):
    value = dict(row._mapping)
    value["integrity_ok"] = digest(value["snapshot"]) == value["sha256"]
    return value


class CreateReport(BaseModel):
    mmsi: int = Field(ge=100000000, le=999999999)


class SignReport(BaseModel):
    officer: str = Field(min_length=1, max_length=120)
    reviewed: bool


@router.get("/")
def list_reports(db: Session = Depends(get_db)):
    return [report(row) for row in db.execute(text("SELECT * FROM incident_reports ORDER BY created_at DESC LIMIT 100"))]


@router.post("/", status_code=201)
def create_report(request: CreateReport, db: Session = Depends(get_db)):
    snapshot = get_vessel(request.mmsi, 24, db)
    detections = db.execute(text("""SELECT id, observed_at, latitude, longitude, source, scene_id,
        confidence, match_distance_m, match_time_seconds FROM sar_detections
        WHERE matched_mmsi = :mmsi ORDER BY observed_at DESC LIMIT 100"""), {"mmsi": request.mmsi})
    snapshot["sar_candidates"] = []
    for row in detections:
        candidate = dict(row._mapping)
        candidate["observed_at"] = candidate["observed_at"].isoformat()
        snapshot["sar_candidates"].append(candidate)
    sha = digest(snapshot)
    row = db.execute(text("""INSERT INTO incident_reports (mmsi, snapshot, sha256)
        VALUES (:mmsi, CAST(:snapshot AS jsonb), :sha) RETURNING *"""),
        {"mmsi": request.mmsi, "snapshot": json.dumps(snapshot, ensure_ascii=False), "sha": sha}).one()
    db.commit()
    return report(row)


@router.post("/{report_id}/sign")
def sign_report(report_id: int, request: SignReport, db: Session = Depends(get_db)):
    officer = request.officer.strip()
    if not request.reviewed or not officer:
        raise HTTPException(400, "Officer name and evidence review are required")
    row = db.execute(text("SELECT * FROM incident_reports WHERE id = :id FOR UPDATE"), {"id": report_id}).first()
    if not row:
        raise HTTPException(404, "Report not found")
    current = report(row)
    if not current["integrity_ok"]:
        raise HTTPException(409, "Evidence snapshot failed integrity verification")
    if current["signed_at"]:
        raise HTTPException(409, "Report has already been signed")
    row = db.execute(text("""UPDATE incident_reports SET signed_by = :officer, signed_at = :now
        WHERE id = :id RETURNING *"""), {"officer": officer, "now": datetime.now(timezone.utc), "id": report_id}).one()
    db.commit()
    return report(row)

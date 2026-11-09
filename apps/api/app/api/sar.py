"""Store permitted point SAR observations and bounded AIS association candidates."""
import json
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import csrf_protect, require_analyst, require_viewer
from app.database import get_db
from app.schemas.user import UserResponse

router = APIRouter()


def _utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class Detection(BaseModel):
    observed_at: datetime
    publication_at: datetime | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source: str = Field(min_length=1, max_length=200)
    scene_id: str = Field(min_length=1, max_length=300)
    confidence: float | None = Field(default=None, ge=0, le=1)
    license_reference: str | None = Field(default=None, max_length=500)
    provider_match_result: dict | None = None
    coverage_status: Literal["verified", "unknown"] = "unknown"

    @field_validator("observed_at", "publication_at")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must include a timezone")
        return value


def _detail(db: Session, detection_id: int):
    row = db.execute(text("SELECT * FROM sar_detections WHERE id=:id"), {"id": detection_id}).mappings().first()
    if row is None:
        raise HTTPException(404, "SAR detection not found")
    candidates = db.execute(text("""SELECT mmsi,distance_m,time_difference_seconds,
        feasible_motion,candidate_rank,input_points FROM sar_detection_candidates
        WHERE detection_id=:id ORDER BY candidate_rank,mmsi"""), {"id": detection_id}).mappings()
    item = dict(row)
    for key in ("observed_at", "publication_at", "created_at"):
        item[key] = _utc(item.get(key))
    item["provider_match_result"] = item.get("provider_match_result") or None
    item["candidates"] = [dict(candidate) for candidate in candidates]
    item["image"] = {"status": "unavailable", "reason": "No licensed crop location was supplied."}
    item["interpretation"] = {
        "matched": "One bounded AIS candidate; identity still requires analyst review.",
        "ambiguous": "Multiple plausible AIS candidates; no vessel identity selected.",
        "unmatched": "No AIS candidate inside the baseline window despite verified input coverage.",
        "insufficient_coverage": "No candidate; nearby AIS coverage is unknown.",
    }[item["association_state"]]
    return item


@router.post("/detections", status_code=201)
def record_detection(
    item: Detection,
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    if db.execute(text("SELECT 1 FROM sar_detections WHERE source=:source AND scene_id=:scene LIMIT 1"),
                  {"source": item.source.strip(), "scene": item.scene_id.strip()}).first():
        raise HTTPException(409, "A detection from this source and scene_id already exists")
    start, end = item.observed_at - timedelta(minutes=15), item.observed_at + timedelta(minutes=15)
    candidates = db.execute(text("""SELECT mmsi,
        min(ST_Distance(location::geography, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography)) distance_m,
        min(ABS(EXTRACT(EPOCH FROM (timestamp-:observed)))) time_difference_seconds,
        count(*) input_points
      FROM vessel_tracks WHERE timestamp BETWEEN :start AND :end
        AND ST_DWithin(location::geography,ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography,2000)
      GROUP BY mmsi ORDER BY distance_m,time_difference_seconds,mmsi LIMIT 10"""), {
        "lon": item.longitude, "lat": item.latitude, "start": start,
        "end": end, "observed": item.observed_at,
    }).mappings().all()
    state = "matched" if len(candidates) == 1 else "ambiguous" if candidates else (
        "unmatched" if item.coverage_status == "verified" else "insufficient_coverage"
    )
    matched = candidates[0] if state == "matched" else None
    try:
        row = db.execute(text("""INSERT INTO sar_detections
          (observed_at,publication_at,latitude,longitude,source,scene_id,confidence,
           license_reference,provider_match_result,association_state,matched_mmsi,
           match_distance_m,match_time_seconds)
          VALUES (:observed,:publication,:lat,:lon,:source,:scene,:confidence,:license,
           CAST(:provider_match AS jsonb),:state,:mmsi,:distance,:age) RETURNING id"""), {
            "observed": item.observed_at, "publication": item.publication_at,
            "lat": item.latitude, "lon": item.longitude, "source": item.source.strip(),
            "scene": item.scene_id.strip(), "confidence": item.confidence,
            "license": item.license_reference,
            "provider_match": json.dumps(item.provider_match_result) if item.provider_match_result is not None else None,
            "state": state, "mmsi": matched["mmsi"] if matched else None,
            "distance": matched["distance_m"] if matched else None,
            "age": matched["time_difference_seconds"] if matched else None,
        }).one()
        for rank, candidate in enumerate(candidates, 1):
            db.execute(text("""INSERT INTO sar_detection_candidates
              (detection_id,mmsi,distance_m,time_difference_seconds,feasible_motion,candidate_rank,input_points)
              VALUES (:id,:mmsi,:distance,:seconds,true,:rank,:points)"""), {
                "id": row.id, "mmsi": candidate["mmsi"], "distance": candidate["distance_m"],
                "seconds": candidate["time_difference_seconds"], "rank": rank,
                "points": candidate["input_points"],
            })
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A detection from this source and scene_id already exists") from exc
    return _detail(db, row.id)


@router.get("/detections")
def list_detections(_viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    ids = db.execute(text("SELECT id FROM sar_detections ORDER BY observed_at DESC,id DESC LIMIT 100")).scalars()
    return [_detail(db, detection_id) for detection_id in ids]


@router.get("/detections/{detection_id}")
def get_detection(detection_id: int, _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    return _detail(db, detection_id)

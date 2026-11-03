"""Record external georeferenced SAR detections and find nearby AIS candidates."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()


class Detection(BaseModel):
    observed_at: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source: str = Field(min_length=1, max_length=200)
    scene_id: str = Field(min_length=1, max_length=300)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("observed_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


@router.post("/detections", status_code=201)
def record_detection(item: Detection, db: Session = Depends(get_db)):
    # A nearby AIS ping is a candidate, not verified vessel identity. Missing AIS
    # coverage must never be interpreted as proof of deliberate evasion.
    params = {"lon": item.longitude, "lat": item.latitude, "start": item.observed_at - timedelta(minutes=15),
              "end": item.observed_at + timedelta(minutes=15), "observed": item.observed_at}
    candidate = db.execute(text("""SELECT mmsi,
        ST_Distance(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_m,
        ABS(EXTRACT(EPOCH FROM (timestamp - :observed))) AS age_seconds
        FROM vessel_tracks WHERE timestamp BETWEEN :start AND :end
        AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 2000)
        ORDER BY distance_m, age_seconds LIMIT 1"""), params).first()
    row = db.execute(text("""INSERT INTO sar_detections
        (observed_at, latitude, longitude, source, scene_id, confidence, matched_mmsi, match_distance_m, match_time_seconds)
        VALUES (:observed, :lat, :lon, :source, :scene, :confidence, :mmsi, :distance, :age) RETURNING *"""),
        {**params, "source": item.source, "scene": item.scene_id, "confidence": item.confidence,
         "mmsi": candidate.mmsi if candidate else None, "distance": candidate.distance_m if candidate else None,
         "age": candidate.age_seconds if candidate else None}).one()
    db.commit()
    return {**dict(row._mapping), "interpretation": "AIS candidate only" if candidate else "No nearby AIS candidate; coverage unknown"}


@router.get("/detections")
def list_detections(db: Session = Depends(get_db)):
    return [dict(r._mapping) for r in db.execute(text("SELECT * FROM sar_detections ORDER BY observed_at DESC LIMIT 100"))]

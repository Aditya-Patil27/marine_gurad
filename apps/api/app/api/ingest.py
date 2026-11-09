from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.auth import csrf_protect, require_analyst
from app.database import get_db
from app.models.vessel import VesselTrack, VesselType, get_vessel_type_from_code
from app.schemas.user import UserResponse
from app.models.pollution import PollutionEvent, PollutionType
from app.services.pollution_detector import PollutionDetector
from app.services.fleet import rescore_all
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import uuid4
import hashlib
import json
import math
from sqlalchemy import text
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, box

router = APIRouter()

SourceMode = Literal["live", "historical", "replay", "synthetic", "unknown"]


class AISRecord(BaseModel):
    mmsi: int
    latitude: float
    longitude: float
    timestamp: datetime
    vessel_type: Optional[int] = None  # AIS numeric code
    flag: Optional[str] = None
    speed: Optional[float] = None  # SOG
    course: Optional[float] = None  # COG
    heading: Optional[float] = None
    vessel_name: Optional[str] = None
    imo: Optional[str] = None
    callsign: Optional[str] = None
    nav_status: Optional[int] = None
    length: Optional[float] = None
    width: Optional[float] = None
    draft: Optional[float] = None
    cargo: Optional[int] = None
    transceiver_class: Optional[str] = None
    source_record_id: Optional[str] = Field(default=None, max_length=160)


class AISBatch(BaseModel):
    records: List[AISRecord] = Field(min_length=1, max_length=1000)
    # Caller-declared provenance only. Omitted values stay conservative and are
    # never upgraded from a configured provider or guess.
    source: Optional[str] = Field(default=None, max_length=120)
    source_mode: SourceMode = "unknown"


@router.post("/ais")
def ingest_ais_data(
    batch: AISBatch = Body(...),
    # Identity before CSRF so anonymous requests get 401, not 403. All
    # dependencies resolve before the body, so denied requests write nothing.
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db)
):
    """Bounded idempotent AIS import with per-record quality quarantine."""

    inserted_count = duplicate_count = quarantined_count = 0
    declared_source = (batch.source or "caller-supplied AIS ingest").strip() or "unknown"
    job_id = uuid4()
    now = datetime.now(timezone.utc)
    db.execute(text("""INSERT INTO source_jobs
        (id,kind,state,progress,attempts,checkpoint,triggered_by,created_at,started_at)
        VALUES (:id,'ais_import','running',0,1,'{}'::jsonb,:actor,:now,:now)"""),
        {"id": str(job_id), "actor": _analyst.username, "now": now})

    def quarantine(index, record, reason, record_id):
        nonlocal quarantined_count
        quarantined_count += 1
        summary = {"mmsi": record.mmsi, "timestamp": record.timestamp.isoformat(),
                   "latitude": record.latitude, "longitude": record.longitude}
        db.execute(text("""INSERT INTO ingest_quarantine
            (job_id,record_index,source_record_id,reason,record_summary)
            VALUES (:job,:index,:record_id,:reason,CAST(:summary AS jsonb))"""), {
            "job": str(job_id), "index": index, "record_id": record_id,
            "reason": reason[:300], "summary": json.dumps(summary, separators=(",", ":")),
        })

    last_checkpoint = None
    for index, record in enumerate(batch.records):
        canonical = f"{record.mmsi}|{record.timestamp.isoformat()}|{record.latitude:.6f}|{record.longitude:.6f}"
        record_id = record.source_record_id or hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        reasons = []
        quality_flags = []
        if not 100000000 <= record.mmsi <= 999999999:
            reasons.append("MMSI must be a nine-digit identifier")
        if not all(math.isfinite(value) for value in (record.latitude, record.longitude)):
            reasons.append("Coordinates must be finite")
        elif not (-90 <= record.latitude <= 90 and -180 <= record.longitude <= 180):
            reasons.append("Coordinates are outside WGS84 bounds")
        if record.timestamp.tzinfo is None or record.timestamp.utcoffset() is None:
            reasons.append("Timestamp must include a UTC offset")
        if record.speed is not None:
            if not math.isfinite(record.speed) or record.speed < 0 or record.speed > 102.3:
                reasons.append("Speed is outside the AIS range")
            elif record.speed == 102.3:
                quality_flags.append("speed_unavailable")
        if record.course is not None:
            if not math.isfinite(record.course) or record.course < 0 or record.course > 360:
                reasons.append("Course is outside the AIS range")
            elif record.course == 360:
                quality_flags.append("course_unavailable")
        if record.heading is not None and record.heading != 511 and not 0 <= record.heading <= 359:
            reasons.append("Heading is outside the AIS range")
        if reasons:
            quarantine(index, record, "; ".join(reasons), record_id)
            continue
        observed_at = record.timestamp.astimezone(timezone.utc)
        existing = db.execute(text("""SELECT 1 FROM vessel_tracks
            WHERE source=:source AND source_record_id=:record_id LIMIT 1"""),
            {"source": declared_source, "record_id": record_id}).first()
        if existing is not None:
            duplicate_count += 1
            last_checkpoint = {"record_index": index, "source_record_id": record_id,
                               "observed_at": observed_at.isoformat()}
            continue
        latest = db.execute(text("SELECT max(timestamp) FROM vessel_tracks WHERE mmsi=:mmsi"),
                            {"mmsi": record.mmsi}).scalar_one_or_none()
        if latest is not None:
            latest = latest.replace(tzinfo=timezone.utc) if latest.tzinfo is None else latest.astimezone(timezone.utc)
            if observed_at < latest:
                quality_flags.append("late_or_out_of_order")
        heading = None if record.heading == 511 else record.heading
        speed = None if record.speed == 102.3 else record.speed
        course = None if record.course == 360 else record.course
        db.add(VesselTrack(
            mmsi=record.mmsi,
            vessel_type=get_vessel_type_from_code(record.vessel_type) if record.vessel_type is not None else None,
            flag=record.flag, location=from_shape(Point(record.longitude, record.latitude), srid=4326),
            timestamp=observed_at, speed=speed, course=course, heading=heading,
            vessel_name=record.vessel_name, imo=record.imo, callsign=record.callsign,
            nav_status=record.nav_status, length=record.length, width=record.width,
            draft=record.draft, cargo=record.cargo, transceiver_class=record.transceiver_class,
            source=declared_source, source_mode=batch.source_mode, source_record_id=record_id,
            ingested_at=now, quality_flags=quality_flags,
        ))
        inserted_count += 1
        last_checkpoint = {"record_index": index, "source_record_id": record_id,
                           "observed_at": observed_at.isoformat()}

    db.flush()
    finished = datetime.now(timezone.utc)
    db.execute(text("""UPDATE source_jobs SET state='succeeded',progress=100,
        checkpoint=CAST(:checkpoint AS jsonb),finished_at=:finished,version=version+1 WHERE id=:id"""), {
        "checkpoint": json.dumps(last_checkpoint or {}, separators=(",", ":")),
        "finished": finished, "id": str(job_id),
    })
    db.commit()

    # Scores depend on neighbours (encounters, receiver outages), so rescore the whole recent fleet
    rescored = rescore_all(db) if inserted_count else 0

    return {
        "status": "success",
        "inserted": inserted_count,
        "duplicates": duplicate_count,
        "quarantined": quarantined_count,
        "rescored": rescored,
        "total": len(batch.records),
        "job_id": str(job_id),
        "checkpoint": last_checkpoint or {},
    }

@router.post("/satellite-image")
def ingest_satellite_image(
    image_url: str = Body(..., embed=True),
    latitude: float = Body(0.0, embed=True),
    longitude: float = Body(0.0, embed=True),
    # Identity before CSRF; see ingest_ais_data for ordering rationale.
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db)
):
    """Process satellite image for pollution detection"""

    if not image_url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="image_url must be an http(s) URL")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="latitude/longitude out of range")

    detector = PollutionDetector()
    if detector.model is None:
        raise HTTPException(status_code=503, detail="Pollution detection model is not loaded")

    try:
        # Sync handler runs in FastAPI's threadpool, so inference doesn't block the event loop
        detections = detector.detect_sync(image_url)
        
        saved_count = 0
        for detection in detections:
            try:
                # Create polygon from bounding box (scaled to geo coordinates)
                # In production, this would use proper satellite image georeferencing
                # with actual GeoTIFF metadata or image corner coordinates
                bbox = detection.get("bbox", [0, 0, 1, 1])

                # Validate bbox has 4 values
                if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                    print(f"Invalid bbox format: {bbox}, skipping detection")
                    continue

                # Scale factor: converts pixel coordinates to approximate degrees
                # This is a placeholder - production should use actual image georeferencing
                # A typical Sentinel-2 pixel at 10m resolution covers ~0.00009 degrees
                scale = 0.0001  # ~10m per pixel approximation

                # Ensure coordinates are within valid geographic bounds
                min_lon = max(-180, min(180, longitude + bbox[0] * scale))
                min_lat = max(-90, min(90, latitude + bbox[1] * scale))
                max_lon = max(-180, min(180, longitude + bbox[2] * scale))
                max_lat = max(-90, min(90, latitude + bbox[3] * scale))

                polygon = box(min_lon, min_lat, max_lon, max_lat)
                wkb_polygon = from_shape(polygon, srid=4326)
                
                # Map detection type to enum
                try:
                    pollution_type = PollutionType(detection.get("type"))
                except ValueError:
                    # Unknown classes must not be recorded as oil spills
                    continue
                
                # Create and save PollutionEvent
                pollution_event = PollutionEvent(
                    type=pollution_type,
                    severity=detection.get("confidence", 0.5),
                    detected_at=datetime.utcnow(),
                    zone=wkb_polygon,
                    image_source=image_url,
                    confidence=detection.get("confidence", 0.0)
                )
                
                db.add(pollution_event)
                saved_count += 1
                
            except Exception as e:
                print(f"Error saving pollution event: {e}")
                continue
        
        db.commit()
        
        return {
            "status": "success",
            "detections": len(detections),
            "saved": saved_count,
            "results": detections
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

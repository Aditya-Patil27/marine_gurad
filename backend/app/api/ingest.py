from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.vessel import VesselTrack, VesselType, get_vessel_type_from_code
from app.models.pollution import PollutionEvent, PollutionType
from app.services.pollution_detector import PollutionDetector
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, box

router = APIRouter()


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


class AISBatch(BaseModel):
    records: List[AISRecord]


@router.post("/ais")
def ingest_ais_data(
    batch: AISBatch = Body(...),
    db: Session = Depends(get_db)
):
    """Webhook endpoint to receive AIS data"""

    inserted_count = 0

    for record in batch.records:
        try:
            # Create point geometry
            point = Point(record.longitude, record.latitude)
            wkb_element = from_shape(point, srid=4326)

            # Convert vessel type code to enum
            vessel_type = None
            if record.vessel_type is not None:
                vessel_type = get_vessel_type_from_code(record.vessel_type)

            # Handle heading (511 = not available in AIS spec)
            heading = record.heading
            if heading is not None and heading == 511.0:
                heading = None

            # Create vessel track
            vessel_track = VesselTrack(
                mmsi=record.mmsi,
                vessel_type=vessel_type,
                flag=record.flag,
                location=wkb_element,
                timestamp=record.timestamp,
                speed=record.speed,
                course=record.course,
                heading=heading,
                vessel_name=record.vessel_name,
                imo=record.imo,
                callsign=record.callsign,
                nav_status=record.nav_status,
                length=record.length,
                width=record.width,
                draft=record.draft,
                cargo=record.cargo,
                transceiver_class=record.transceiver_class,
                is_dark=False,  # Would calculate from gaps
                risk_score=0.0  # Would calculate from ML model
            )

            db.add(vessel_track)
            inserted_count += 1

        except Exception as e:
            print(f"Error inserting AIS record {record.mmsi}: {e}")
            continue

    db.commit()

    return {
        "status": "success",
        "inserted": inserted_count,
        "total": len(batch.records)
    }

@router.post("/satellite-image")
def ingest_satellite_image(
    image_url: str = Body(..., embed=True),
    latitude: float = Body(0.0, embed=True),
    longitude: float = Body(0.0, embed=True),
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

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.vessel import VesselTrack, VesselType
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
    vessel_type: Optional[str] = None
    flag: Optional[str] = None
    speed: Optional[float] = None
    course: Optional[float] = None

class AISBatch(BaseModel):
    records: List[AISRecord]

@router.post("/ais")
async def ingest_ais_data(
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
            
            # Create vessel track
            vessel_track = VesselTrack(
                mmsi=record.mmsi,
                vessel_type=record.vessel_type,
                flag=record.flag,
                location=wkb_element,
                timestamp=record.timestamp,
                speed=record.speed,
                course=record.course,
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
async def ingest_satellite_image(
    image_url: str = Body(..., embed=True),
    latitude: float = Body(0.0, embed=True),
    longitude: float = Body(0.0, embed=True),
    db: Session = Depends(get_db)
):
    """Process satellite image for pollution detection"""
    
    detector = PollutionDetector()
    
    try:
        # Detect pollution
        detections = await detector.detect(image_url)
        
        saved_count = 0
        for detection in detections:
            try:
                # Create polygon from bounding box (scaled to geo coordinates)
                # In production, this would use proper satellite image georeferencing
                bbox = detection.get("bbox", [0, 0, 1, 1])
                scale = 0.001  # Approximate degree scale for bbox
                
                polygon = box(
                    longitude + bbox[0] * scale,
                    latitude + bbox[1] * scale,
                    longitude + bbox[2] * scale,
                    latitude + bbox[3] * scale
                )
                wkb_polygon = from_shape(polygon, srid=4326)
                
                # Map detection type to enum
                pollution_type_str = detection.get("type", "OIL")
                try:
                    pollution_type = PollutionType(pollution_type_str)
                except ValueError:
                    pollution_type = PollutionType.OIL
                
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

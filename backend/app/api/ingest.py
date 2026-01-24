from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.vessel import VesselTrack, VesselType
from app.services.pollution_detector import PollutionDetector
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

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
    db: Session = Depends(get_db)
):
    """Process satellite image for pollution detection"""
    
    detector = PollutionDetector()
    
    try:
        # Detect pollution
        detections = await detector.detect(image_url)
        
        # Store detections in database
        # This would create PollutionEvent records
        
        return {
            "status": "success",
            "detections": len(detections),
            "results": detections
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

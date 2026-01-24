from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class Alert(BaseModel):
    id: str
    type: str  # POLLUTION, IUU_FISHING, MPA_VIOLATION
    severity: str  # HIGH, MEDIUM, LOW
    title: str
    description: str
    timestamp: datetime
    location: dict
    metadata: Optional[dict] = None

@router.get("/", response_model=List[Alert])
async def get_alerts(
    limit: int = Query(50, le=100),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get active alerts with predictive warnings"""
    
    alerts = []
    
    # High-risk vessel alerts
    vessel_query = text("""
        SELECT 
            mmsi,
            vessel_type,
            risk_score,
            timestamp,
            ST_X(location::geometry) as lon,
            ST_Y(location::geometry) as lat
        FROM vessel_tracks
        WHERE risk_score > 0.7
        AND timestamp > NOW() - INTERVAL '6 hours'
        ORDER BY risk_score DESC
        LIMIT :limit
    """)
    
    vessel_result = db.execute(vessel_query, {"limit": limit})
    
    for row in vessel_result:
        alerts.append({
            "id": f"vessel-{row.mmsi}-{row.timestamp.timestamp()}",
            "type": "IUU_FISHING",
            "severity": "HIGH" if row.risk_score > 0.85 else "MEDIUM",
            "title": f"Suspicious Vessel Activity - MMSI {row.mmsi}",
            "description": f"Vessel showing dark activity patterns. Risk score: {row.risk_score:.2f}",
            "timestamp": row.timestamp,
            "location": {"lat": row.lat, "lon": row.lon},
            "metadata": {
                "mmsi": row.mmsi,
                "vessel_type": row.vessel_type,
                "risk_score": row.risk_score
            }
        })
    
    # Pollution alerts
    pollution_query = text("""
        SELECT 
            id,
            type,
            severity,
            detected_at,
            ST_AsGeoJSON(ST_Centroid(zone::geometry)) as centroid
        FROM pollution_events
        WHERE detected_at > NOW() - INTERVAL '24 hours'
        ORDER BY severity DESC
        LIMIT :limit
    """)
    
    pollution_result = db.execute(pollution_query, {"limit": limit})
    
    for row in pollution_result:
        import json
        centroid = json.loads(row.centroid)
        
        alerts.append({
            "id": str(row.id),
            "type": "POLLUTION",
            "severity": "HIGH" if row.severity > 0.7 else "MEDIUM",
            "title": f"{row.type} Pollution Detected",
            "description": f"Severity: {row.severity:.2f}",
            "timestamp": row.detected_at,
            "location": {
                "lat": centroid["coordinates"][1],
                "lon": centroid["coordinates"][0]
            },
            "metadata": {
                "pollution_type": row.type,
                "severity": row.severity
            }
        })
    
    # Sort by timestamp descending
    alerts.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return alerts[:limit]

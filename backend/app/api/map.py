from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.vessel import VesselGeoJSON
from app.schemas.pollution import PollutionGeoJSON
from app.schemas.mpa import MPAGeoJSON
from typing import Optional
from shapely import wkb
from shapely.geometry import mapping
import json

router = APIRouter()

@router.get("/layers", response_model=dict)
async def get_map_layers(
    layer_type: str = Query(..., description="Layer type: vessels, pollution, or mpas"),
    bbox: Optional[str] = Query(None, description="Bounding box: minLon,minLat,maxLon,maxLat"),
    db: Session = Depends(get_db)
):
    """Get GeoJSON data for map layers with optional bbox filtering"""
    
    if layer_type == "vessels":
        return await get_vessels_layer(bbox, db)
    elif layer_type == "pollution":
        return await get_pollution_layer(bbox, db)
    elif layer_type == "mpas":
        return await get_mpas_layer(bbox, db)
    else:
        return {"type": "FeatureCollection", "features": []}

async def get_vessels_layer(bbox: Optional[str], db: Session):
    """Fetch vessel tracks as GeoJSON"""
    query = text("""
        SELECT 
            mmsi,
            vessel_type,
            flag,
            timestamp,
            is_dark,
            risk_score,
            speed,
            course,
            ST_AsGeoJSON(location) as geometry
        FROM vessel_tracks
        WHERE timestamp > NOW() - INTERVAL '24 hours'
    """)
    
    if bbox:
        coords = [float(x) for x in bbox.split(',')]
        query = text(f"""
            {query.text}
            AND ST_Intersects(
                location,
                ST_MakeEnvelope({coords[0]}, {coords[1]}, {coords[2]}, {coords[3]}, 4326)
            )
        """)
    
    result = db.execute(query)
    features = []
    
    for row in result:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row.geometry),
            "properties": {
                "mmsi": row.mmsi,
                "vessel_type": row.vessel_type,
                "flag": row.flag,
                "timestamp": row.timestamp.isoformat(),
                "is_dark": row.is_dark,
                "risk_score": row.risk_score,
                "speed": row.speed,
                "course": row.course,
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

async def get_pollution_layer(bbox: Optional[str], db: Session):
    """Fetch pollution events as GeoJSON"""
    query = text("""
        SELECT 
            id,
            type,
            severity,
            detected_at,
            confidence,
            image_source,
            ST_AsGeoJSON(zone) as geometry
        FROM pollution_events
        WHERE detected_at > NOW() - INTERVAL '7 days'
    """)
    
    if bbox:
        coords = [float(x) for x in bbox.split(',')]
        query = text(f"""
            {query.text}
            AND ST_Intersects(
                zone,
                ST_MakeEnvelope({coords[0]}, {coords[1]}, {coords[2]}, {coords[3]}, 4326)
            )
        """)
    
    result = db.execute(query)
    features = []
    
    for row in result:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row.geometry),
            "properties": {
                "id": str(row.id),
                "type": row.type,
                "severity": row.severity,
                "detected_at": row.detected_at.isoformat(),
                "confidence": row.confidence,
                "image_source": row.image_source,
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

async def get_mpas_layer(bbox: Optional[str], db: Session):
    """Fetch Marine Protected Areas as GeoJSON"""
    query = text("""
        SELECT 
            id,
            name,
            designation,
            iucn_category,
            country,
            ST_AsGeoJSON(boundary) as geometry
        FROM marine_protected_areas
    """)
    
    if bbox:
        coords = [float(x) for x in bbox.split(',')]
        query = text(f"""
            {query.text}
            WHERE ST_Intersects(
                boundary,
                ST_MakeEnvelope({coords[0]}, {coords[1]}, {coords[2]}, {coords[3]}, 4326)
            )
        """)
    
    result = db.execute(query)
    features = []
    
    for row in result:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row.geometry),
            "properties": {
                "id": row.id,
                "name": row.name,
                "designation": row.designation,
                "iucn_category": row.iucn_category,
                "country": row.country,
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

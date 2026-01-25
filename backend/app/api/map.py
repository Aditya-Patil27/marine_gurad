from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.vessel import VesselGeoJSON
from app.schemas.pollution import PollutionGeoJSON
from app.schemas.mpa import MPAGeoJSON
from typing import Optional
from shapely import wkb
from shapely.geometry import mapping, box
import json
from app.demo_data import DEMO_VESSELS, DEMO_POLLUTION, DEMO_MPAS

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
    """Fetch vessel tracks as GeoJSON - DEMO MODE with hardcoded data"""
    features = []

    for vessel in DEMO_VESSELS:
        lon, lat = vessel["coordinates"]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "mmsi": vessel["mmsi"],
                "vessel_type": vessel["vessel_type"],
                "flag": vessel["flag"],
                "timestamp": vessel["timestamp"].isoformat(),
                "is_dark": vessel["is_dark"],
                "risk_score": vessel["risk_score"],
                "speed": vessel["speed"],
                "course": vessel["course"],
            }
        })

    return {"type": "FeatureCollection", "features": features}

async def get_pollution_layer(bbox: Optional[str], db: Session):
    """Fetch pollution events as GeoJSON - DEMO MODE with hardcoded data"""
    features = []

    for pollution in DEMO_POLLUTION:
        bbox_coords = pollution["bbox"]
        polygon = box(bbox_coords[0], bbox_coords[1], bbox_coords[2], bbox_coords[3])

        features.append({
            "type": "Feature",
            "geometry": mapping(polygon),
            "properties": {
                "id": str(pollution["id"]),
                "type": pollution["type"],
                "severity": pollution["severity"],
                "detected_at": pollution["detected_at"].isoformat(),
                "confidence": pollution["confidence"],
                "image_source": pollution["image_source"],
            }
        })

    return {"type": "FeatureCollection", "features": features}

async def get_mpas_layer(bbox: Optional[str], db: Session):
    """Fetch Marine Protected Areas as GeoJSON - DEMO MODE with hardcoded data"""
    features = []

    for mpa in DEMO_MPAS:
        features.append({
            "type": "Feature",
            "geometry": mpa["boundary"],
            "properties": {
                "id": mpa["id"],
                "name": mpa["name"],
                "designation": mpa["designation"],
                "iucn_category": mpa["iucn_category"],
                "country": mpa["country"],
            }
        })

    return {"type": "FeatureCollection", "features": features}

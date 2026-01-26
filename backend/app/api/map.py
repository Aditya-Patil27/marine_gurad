from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.vessel import VesselGeoJSON
from app.schemas.pollution import PollutionGeoJSON
from app.schemas.mpa import MPAGeoJSON
from app.models.vessel import VesselTrack
from app.models.pollution import PollutionEvent
from app.models.mpa import MarineProtectedArea
from typing import Optional
from shapely import wkb
from shapely.geometry import mapping, box
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
    """Fetch vessel tracks as GeoJSON from database"""
    features = []

    # Build query with optional bbox filter
    query = text("""
        SELECT
            mmsi,
            vessel_type,
            flag,
            ST_X(location::geometry) as lon,
            ST_Y(location::geometry) as lat,
            timestamp,
            is_dark,
            risk_score,
            speed,
            course
        FROM vessel_tracks
        WHERE timestamp > NOW() - INTERVAL '1 hour'
        ORDER BY timestamp DESC
    """)

    if bbox:
        # Parse bbox: minLon,minLat,maxLon,maxLat
        coords = [float(x) for x in bbox.split(',')]
        query = text("""
            SELECT
                mmsi,
                vessel_type,
                flag,
                ST_X(location::geometry) as lon,
                ST_Y(location::geometry) as lat,
                timestamp,
                is_dark,
                risk_score,
                speed,
                course
            FROM vessel_tracks
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            AND ST_Intersects(
                location,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
            ORDER BY timestamp DESC
        """)
        result = db.execute(query, {
            "min_lon": coords[0],
            "min_lat": coords[1],
            "max_lon": coords[2],
            "max_lat": coords[3]
        })
    else:
        result = db.execute(query)

    for row in result:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row.lon, row.lat]
            },
            "properties": {
                "mmsi": row.mmsi,
                "vessel_type": row.vessel_type,
                "flag": row.flag,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "is_dark": row.is_dark,
                "risk_score": row.risk_score,
                "speed": row.speed,
                "course": row.course,
            }
        })

    return {"type": "FeatureCollection", "features": features}

async def get_pollution_layer(bbox: Optional[str], db: Session):
    """Fetch pollution events as GeoJSON from database"""
    features = []

    query = text("""
        SELECT
            id,
            type,
            severity,
            detected_at,
            confidence,
            image_source,
            ST_AsGeoJSON(zone) as zone_geojson
        FROM pollution_events
        WHERE detected_at > NOW() - INTERVAL '7 days'
        ORDER BY detected_at DESC
    """)

    if bbox:
        coords = [float(x) for x in bbox.split(',')]
        query = text("""
            SELECT
                id,
                type,
                severity,
                detected_at,
                confidence,
                image_source,
                ST_AsGeoJSON(zone) as zone_geojson
            FROM pollution_events
            WHERE detected_at > NOW() - INTERVAL '7 days'
            AND ST_Intersects(
                zone,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
            ORDER BY detected_at DESC
        """)
        result = db.execute(query, {
            "min_lon": coords[0],
            "min_lat": coords[1],
            "max_lon": coords[2],
            "max_lat": coords[3]
        })
    else:
        result = db.execute(query)

    for row in result:
        zone_geom = json.loads(row.zone_geojson)

        features.append({
            "type": "Feature",
            "geometry": zone_geom,
            "properties": {
                "id": str(row.id),
                "type": row.type,
                "severity": row.severity,
                "detected_at": row.detected_at.isoformat() if row.detected_at else None,
                "confidence": row.confidence,
                "image_source": row.image_source,
            }
        })

    return {"type": "FeatureCollection", "features": features}

async def get_mpas_layer(bbox: Optional[str], db: Session):
    """Fetch Marine Protected Areas as GeoJSON from database"""
    features = []

    query = text("""
        SELECT
            id,
            name,
            designation,
            iucn_category,
            country,
            ST_AsGeoJSON(boundary) as boundary_geojson
        FROM marine_protected_areas
    """)

    if bbox:
        coords = [float(x) for x in bbox.split(',')]
        query = text("""
            SELECT
                id,
                name,
                designation,
                iucn_category,
                country,
                ST_AsGeoJSON(boundary) as boundary_geojson
            FROM marine_protected_areas
            WHERE ST_Intersects(
                boundary,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
        """)
        result = db.execute(query, {
            "min_lon": coords[0],
            "min_lat": coords[1],
            "max_lon": coords[2],
            "max_lat": coords[3]
        })
    else:
        result = db.execute(query)

    for row in result:
        boundary_geom = json.loads(row.boundary_geojson)

        features.append({
            "type": "Feature",
            "geometry": boundary_geom,
            "properties": {
                "id": row.id,
                "name": row.name,
                "designation": row.designation,
                "iucn_category": row.iucn_category,
                "country": row.country,
            }
        })

    return {"type": "FeatureCollection", "features": features}

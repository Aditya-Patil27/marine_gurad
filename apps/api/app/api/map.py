from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.vessel import VesselGeoJSON
from app.schemas.pollution import PollutionGeoJSON
from app.schemas.mpa import MPAGeoJSON
from app.schemas.validators import BoundingBox, parse_bbox
from app.models.vessel import VesselTrack
from app.models.pollution import PollutionEvent
from app.models.mpa import MarineProtectedArea
from typing import Optional
from shapely import wkb
from shapely.geometry import mapping, box
import json

router = APIRouter()


def validate_bbox_param(bbox: Optional[str]) -> Optional[BoundingBox]:
    """
    Validate and parse bbox query parameter with proper error handling.
    
    Args:
        bbox: Raw bbox string from query parameter
        
    Returns:
        Validated BoundingBox or None
        
    Raises:
        HTTPException: If bbox format is invalid
    """
    if not bbox:
        return None
    try:
        return parse_bbox(bbox)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.get("/layers", response_model=dict)
def get_map_layers(
    layer_type: str = Query(..., description="Layer type: vessels, pollution, or mpas"),
    bbox: Optional[str] = Query(None, description="Bounding box: minLon,minLat,maxLon,maxLat"),
    db: Session = Depends(get_db)
):
    """
    Get GeoJSON data for map layers with optional bbox filtering.
    
    The bbox parameter is validated to ensure proper format and coordinate ranges.
    Invalid bbox values will return a 400 error with details.
    """
    
    # Validate bbox parameter before processing
    validated_bbox = validate_bbox_param(bbox)

    if layer_type == "vessels":
        return get_vessels_layer(validated_bbox, db)
    elif layer_type == "pollution":
        return get_pollution_layer(validated_bbox, db)
    elif layer_type == "mpas":
        return get_mpas_layer(validated_bbox, db)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid layer_type: '{layer_type}'. Must be one of: vessels, pollution, mpas"
        )

def get_vessels_layer(bbox: Optional[BoundingBox], db: Session):
    """
    Fetch the latest position of each vessel seen in the last hour as GeoJSON.
    Uses database-level coordinate extraction for better performance.
    """

    # Build query - PostgreSQL generates coordinates directly, avoiding Python-side geometry parsing
    if bbox:
        query = text("""
            SELECT DISTINCT ON (mmsi)
                mmsi,
                vessel_type,
                flag,
                ST_X(location::geometry) as lon,
                ST_Y(location::geometry) as lat,
                timestamp,
                is_dark,
                risk_score,
                speed,
                course,
                heading,
                vessel_name,
                imo,
                callsign,
                nav_status,
                length,
                width,
                draft,
                cargo,
                transceiver_class
            FROM vessel_tracks
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            AND ST_Intersects(
                location,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
            ORDER BY mmsi, timestamp DESC
        """)
        result = db.execute(query, bbox.to_dict())
    else:
        query = text("""
            SELECT DISTINCT ON (mmsi)
                mmsi,
                vessel_type,
                flag,
                ST_X(location::geometry) as lon,
                ST_Y(location::geometry) as lat,
                timestamp,
                is_dark,
                risk_score,
                speed,
                course,
                heading,
                vessel_name,
                imo,
                callsign,
                nav_status,
                length,
                width,
                draft,
                cargo,
                transceiver_class
            FROM vessel_tracks
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            ORDER BY mmsi, timestamp DESC
        """)
        result = db.execute(query)

    # Navigation status descriptions
    nav_status_map = {
        0: "Under way using engine",
        1: "At anchor",
        2: "Not under command",
        3: "Restricted manoeuvrability",
        4: "Constrained by draught",
        5: "Moored",
        6: "Aground",
        7: "Engaged in fishing",
        8: "Under way sailing",
        9: "Reserved for HSC",
        10: "Reserved for WIG",
        14: "AIS-SART active",
        15: "Not defined",
    }

    # Build features directly without intermediate json.loads calls
    features = [
        {
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
                "heading": row.heading,
                "vessel_name": row.vessel_name,
                "imo": row.imo,
                "callsign": row.callsign,
                "nav_status": row.nav_status,
                "nav_status_description": nav_status_map.get(row.nav_status, "Unknown") if row.nav_status is not None else None,
                "length": row.length,
                "width": row.width,
                "draft": row.draft,
                "cargo": row.cargo,
                "transceiver_class": row.transceiver_class,
            }
        }
        for row in result
    ]

    return {"type": "FeatureCollection", "features": features}

def get_pollution_layer(bbox: Optional[BoundingBox], db: Session):
    """
    Fetch pollution events as GeoJSON from database.
    
    Optimized to build the complete GeoJSON FeatureCollection at the database level
    for better performance with large datasets.
    """
    
    if bbox:
        # Use database-level JSON aggregation to build complete GeoJSON in one query
        query = text("""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(zone)::json,
                        'properties', json_build_object(
                            'id', id::text,
                            'type', type,
                            'severity', severity,
                            'detected_at', to_char(detected_at, 'YYYY-MM-DD"T"HH24:MI:SS'),
                            'confidence', confidence,
                            'image_source', image_source
                        )
                    )
                ) FILTER (WHERE id IS NOT NULL), '[]'::json)
            ) as geojson
            FROM pollution_events
            WHERE detected_at > NOW() - INTERVAL '7 days'
            AND ST_Intersects(
                zone,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
        """)
        result = db.execute(query, bbox.to_dict()).fetchone()
    else:
        query = text("""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(zone)::json,
                        'properties', json_build_object(
                            'id', id::text,
                            'type', type,
                            'severity', severity,
                            'detected_at', to_char(detected_at, 'YYYY-MM-DD"T"HH24:MI:SS'),
                            'confidence', confidence,
                            'image_source', image_source
                        )
                    )
                ) FILTER (WHERE id IS NOT NULL), '[]'::json)
            ) as geojson
            FROM pollution_events
            WHERE detected_at > NOW() - INTERVAL '7 days'
        """)
        result = db.execute(query).fetchone()
    
    # Return the pre-built GeoJSON directly from database
    if result and result.geojson:
        return result.geojson
    
    return {"type": "FeatureCollection", "features": []}

def get_mpas_layer(bbox: Optional[BoundingBox], db: Session):
    """
    Fetch Marine Protected Areas as GeoJSON from database.
    
    Uses database-level JSON aggregation to build the complete FeatureCollection
    in a single query, avoiding per-row json.loads overhead.
    """
    
    if bbox:
        query = text("""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(boundary)::json,
                        'properties', json_build_object(
                            'id', id,
                            'name', name,
                            'designation', designation,
                            'iucn_category', iucn_category,
                            'country', country
                        )
                    )
                ) FILTER (WHERE id IS NOT NULL), '[]'::json)
            ) as geojson
            FROM marine_protected_areas
            WHERE ST_Intersects(
                boundary,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
        """)
        result = db.execute(query, bbox.to_dict()).fetchone()
    else:
        query = text("""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(boundary)::json,
                        'properties', json_build_object(
                            'id', id,
                            'name', name,
                            'designation', designation,
                            'iucn_category', iucn_category,
                            'country', country
                        )
                    )
                ) FILTER (WHERE id IS NOT NULL), '[]'::json)
            ) as geojson
            FROM marine_protected_areas
        """)
        result = db.execute(query).fetchone()
    
    # Return the pre-built GeoJSON directly from database
    if result and result.geojson:
        return result.geojson
    
    return {"type": "FeatureCollection", "features": []}


@router.get("/zones")
def get_zones(db: Session = Depends(get_db)):
    """Protected areas plus the buffer ring the risk engine treats as protected waters."""
    from app.services.risk_engine import BUFFER_KM

    rows = db.execute(
        text("""
            SELECT id, name, designation, country,
                   ST_AsGeoJSON(boundary, 5)::json AS outline,
                   ST_AsGeoJSON(ST_Buffer(boundary::geography, :m)::geometry, 5)::json AS buffer,
                   ST_Y(ST_PointOnSurface(boundary)) AS label_lat,
                   ST_X(ST_PointOnSurface(boundary)) AS label_lon
            FROM marine_protected_areas
            ORDER BY name
        """),
        {"m": BUFFER_KM * 1000},
    )
    features = []
    for r in rows:
        props = {"id": r.id, "name": r.name, "designation": r.designation, "country": r.country,
                 "label": [r.label_lon, r.label_lat]}
        features.append({"type": "Feature", "geometry": r.outline, "properties": {**props, "kind": "outline"}})
        features.append({"type": "Feature", "geometry": r.buffer,
                         "properties": {**props, "kind": "buffer", "buffer_km": BUFFER_KM}})
    return {"type": "FeatureCollection", "features": features}

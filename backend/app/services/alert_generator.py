from sqlalchemy.orm import Session
from sqlalchemy import text
from shapely.geometry import Point, shape, mapping
from shapely import wkb
from shapely.ops import transform
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import json

from app.services.route_predictor import RoutePredictor

class AlertGenerator:
    """Service for generating predictive alerts using LSTM route prediction"""
    
    def __init__(self, db: Session):
        self.db = db
        self.route_predictor = RoutePredictor()
    
    def _get_vessel_history(self, mmsi: int, hours: int = 2) -> List[Tuple[float, float]]:
        """Retrieve recent position history for a vessel"""
        query = text("""
            SELECT 
                ST_X(location::geometry) as lon,
                ST_Y(location::geometry) as lat
            FROM vessel_tracks
            WHERE mmsi = :mmsi
            AND timestamp > NOW() - INTERVAL ':hours hours'
            ORDER BY timestamp ASC
            LIMIT 20
        """)
        
        result = self.db.execute(query, {"mmsi": mmsi, "hours": hours})
        return [(row.lon, row.lat) for row in result]
    
    def _estimate_arrival_time(self, distance_km: float, speed_knots: float) -> str:
        """Estimate time to reach MPA based on current speed"""
        if speed_knots <= 0:
            return "Unknown"
        
        # Convert nautical miles to km (1 knot = 1.852 km/h)
        speed_kmh = speed_knots * 1.852
        hours = distance_km / speed_kmh
        
        if hours < 1:
            return f"{int(hours * 60)} minutes"
        elif hours < 24:
            return f"{hours:.1f} hours"
        else:
            return f"{hours / 24:.1f} days"
    
    def check_mpa_violations(self) -> List[Dict]:
        """Check for vessels predicted to enter MPAs using LSTM trajectory prediction"""
        
        alerts = []
        
        # Query vessels near MPAs with their recent positions
        query = text("""
            SELECT 
                v.mmsi,
                v.vessel_type,
                v.risk_score,
                v.speed,
                ST_X(v.location::geometry) as lon,
                ST_Y(v.location::geometry) as lat,
                ST_AsGeoJSON(v.location) as vessel_location,
                m.name as mpa_name,
                m.id as mpa_id,
                ST_AsGeoJSON(m.boundary) as mpa_boundary,
                ST_Distance(v.location::geography, m.boundary::geography) as distance_meters
            FROM vessel_tracks v
            CROSS JOIN LATERAL (
                SELECT id, name, boundary
                FROM marine_protected_areas
                WHERE ST_DWithin(v.location::geography, boundary::geography, 100000)
                ORDER BY ST_Distance(v.location::geography, boundary::geography)
                LIMIT 1
            ) m
            WHERE v.timestamp > NOW() - INTERVAL '1 hour'
            AND v.risk_score > 0.3
        """)
        
        result = self.db.execute(query)
        
        for row in result:
            # Get vessel position history for prediction
            positions = self._get_vessel_history(row.mmsi)
            
            # Need at least 3 positions for prediction
            if len(positions) < 3:
                positions = [(row.lon, row.lat)]  # Use current position only
            
            # Predict future trajectory using LSTM
            predicted_trajectory = self.route_predictor.predict_trajectory(
                positions=positions,
                steps=12  # Predict 12 steps ahead (e.g., 2 hours if 10-min intervals)
            )
            
            # Check if predicted path intersects with MPA boundary
            mpa_geojson = json.loads(row.mpa_boundary)
            mpa_polygon = shape(mpa_geojson)
            
            will_violate = predicted_trajectory.intersects(mpa_polygon)
            is_currently_inside = Point(row.lon, row.lat).within(mpa_polygon)
            
            # Calculate estimated time to MPA
            speed = row.speed or 10  # Default speed if not available
            estimated_time = self._estimate_arrival_time(
                row.distance_meters / 1000, 
                speed
            )
            
            # Generate alert based on prediction
            if is_currently_inside:
                alerts.append({
                    "type": "MPA_VIOLATION",
                    "severity": "critical",
                    "mmsi": row.mmsi,
                    "vessel_type": row.vessel_type,
                    "mpa_name": row.mpa_name,
                    "mpa_id": row.mpa_id,
                    "distance_km": 0,
                    "risk_score": row.risk_score,
                    "estimated_time": "Currently inside",
                    "predicted_violation": True,
                    "trajectory": mapping(predicted_trajectory)
                })
            elif will_violate:
                alerts.append({
                    "type": "MPA_APPROACH_PREDICTED",
                    "severity": "high",
                    "mmsi": row.mmsi,
                    "vessel_type": row.vessel_type,
                    "mpa_name": row.mpa_name,
                    "mpa_id": row.mpa_id,
                    "distance_km": round(row.distance_meters / 1000, 2),
                    "risk_score": row.risk_score,
                    "estimated_time": estimated_time,
                    "predicted_violation": True,
                    "trajectory": mapping(predicted_trajectory)
                })
            elif row.distance_meters < 10000:  # Within 10km but not predicted to violate
                alerts.append({
                    "type": "MPA_APPROACH",
                    "severity": "medium",
                    "mmsi": row.mmsi,
                    "vessel_type": row.vessel_type,
                    "mpa_name": row.mpa_name,
                    "mpa_id": row.mpa_id,
                    "distance_km": round(row.distance_meters / 1000, 2),
                    "risk_score": row.risk_score,
                    "estimated_time": estimated_time,
                    "predicted_violation": False,
                    "trajectory": mapping(predicted_trajectory)
                })
        
        return alerts
    
    def check_dark_vessels(self) -> List[Dict]:
        """Detect vessels going dark (AIS gaps)"""
        
        # Would analyze AIS transmission gaps
        # This is a simplified version
        
        return []

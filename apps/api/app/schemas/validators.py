"""
Custom Pydantic validators for geospatial and other input validation.
"""
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Tuple, List, Any
import re


class BoundingBox(BaseModel):
    """
    Validated bounding box for geospatial queries.
    Accepts format: "minLon,minLat,maxLon,maxLat" as string or parsed components.
    
    Example valid values:
        - "-122.5,37.0,-122.0,38.0"
        - BoundingBox(min_lon=-122.5, min_lat=37.0, max_lon=-122.0, max_lat=38.0)
    """
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    
    @field_validator('min_lon', 'max_lon')
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        """Validate longitude is within valid range [-180, 180]"""
        if not -180 <= v <= 180:
            raise ValueError(f'Longitude must be between -180 and 180, got {v}')
        return v
    
    @field_validator('min_lat', 'max_lat')
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        """Validate latitude is within valid range [-90, 90]"""
        if not -90 <= v <= 90:
            raise ValueError(f'Latitude must be between -90 and 90, got {v}')
        return v
    
    @model_validator(mode='after')
    def validate_bbox_order(self) -> 'BoundingBox':
        """Validate that min values are less than max values"""
        if self.min_lon > self.max_lon:
            raise ValueError(f'min_lon ({self.min_lon}) must be <= max_lon ({self.max_lon})')
        if self.min_lat > self.max_lat:
            raise ValueError(f'min_lat ({self.min_lat}) must be <= max_lat ({self.max_lat})')
        return self
    
    @classmethod
    def from_string(cls, bbox_str: str) -> 'BoundingBox':
        """
        Parse a bounding box from string format "minLon,minLat,maxLon,maxLat"
        
        Args:
            bbox_str: Comma-separated bounding box coordinates
            
        Returns:
            BoundingBox instance
            
        Raises:
            ValueError: If the format is invalid or coordinates are out of range
        """
        if not bbox_str:
            raise ValueError("Bounding box string cannot be empty")
        
        # Remove whitespace and validate format
        bbox_str = bbox_str.strip()
        
        # Check format with regex (optional signs, digits, optional decimals)
        pattern = r'^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$'
        if not re.match(pattern, bbox_str):
            raise ValueError(
                f'Invalid bounding box format: "{bbox_str}". '
                'Expected format: minLon,minLat,maxLon,maxLat (e.g., "-122.5,37.0,-122.0,38.0")'
            )
        
        try:
            parts = bbox_str.split(',')
            if len(parts) != 4:
                raise ValueError(
                    f'Bounding box must have exactly 4 values, got {len(parts)}. '
                    'Expected format: minLon,minLat,maxLon,maxLat'
                )
            
            min_lon, min_lat, max_lon, max_lat = [float(x.strip()) for x in parts]
            return cls(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
            
        except ValueError as e:
            if "could not convert" in str(e).lower() or "invalid literal" in str(e).lower():
                raise ValueError(
                    f'Invalid numeric values in bounding box: "{bbox_str}". '
                    'All coordinates must be valid numbers.'
                )
            raise
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        """Return coordinates as tuple (min_lon, min_lat, max_lon, max_lat)"""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
    
    def to_dict(self) -> dict:
        """Return coordinates as dict for SQL parameter binding"""
        return {
            "min_lon": self.min_lon,
            "min_lat": self.min_lat,
            "max_lon": self.max_lon,
            "max_lat": self.max_lat
        }


def parse_bbox(bbox_str: Optional[str]) -> Optional[BoundingBox]:
    """
    Utility function to parse optional bounding box parameter.
    
    Args:
        bbox_str: Optional bounding box string in format "minLon,minLat,maxLon,maxLat"
        
    Returns:
        BoundingBox if valid string provided, None if empty/None
        
    Raises:
        ValueError: If the format is invalid
    """
    if not bbox_str:
        return None
    return BoundingBox.from_string(bbox_str)


class GeoPoint(BaseModel):
    """Validated geographic point (longitude, latitude)"""
    lon: float
    lat: float
    
    @field_validator('lon')
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError(f'Longitude must be between -180 and 180, got {v}')
        return v
    
    @field_validator('lat')
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError(f'Latitude must be between -90 and 90, got {v}')
        return v

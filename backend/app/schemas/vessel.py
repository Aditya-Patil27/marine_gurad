from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class VesselTrackResponse(BaseModel):
    mmsi: int
    vessel_type: Optional[str]
    flag: Optional[str]
    timestamp: datetime
    is_dark: bool
    risk_score: float
    speed: Optional[float]
    course: Optional[float]
    lat: float
    lon: float
    
    class Config:
        from_attributes = True

class VesselFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict

class VesselGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: List[VesselFeature]

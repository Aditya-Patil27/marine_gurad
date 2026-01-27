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
    # New AIS fields
    heading: Optional[float] = None
    vessel_name: Optional[str] = None
    imo: Optional[str] = None
    callsign: Optional[str] = None
    nav_status: Optional[int] = None
    nav_status_description: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    draft: Optional[float] = None
    cargo: Optional[int] = None
    transceiver_class: Optional[str] = None

    class Config:
        from_attributes = True


class VesselFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict


class VesselGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: List[VesselFeature]

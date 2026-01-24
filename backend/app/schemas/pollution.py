from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import uuid

class PollutionEventResponse(BaseModel):
    id: uuid.UUID
    type: str
    severity: float
    detected_at: datetime
    image_source: Optional[str]
    confidence: Optional[float]
    
    class Config:
        from_attributes = True

class PollutionFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict

class PollutionGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: List[PollutionFeature]

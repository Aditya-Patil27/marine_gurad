from pydantic import BaseModel
from typing import Optional, List

class MPAResponse(BaseModel):
    id: int
    name: str
    designation: Optional[str]
    iucn_category: Optional[str]
    country: Optional[str]
    
    class Config:
        from_attributes = True

class MPAFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict

class MPAGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    features: List[MPAFeature]

from sqlmodel import SQLModel, Field, Column
from geoalchemy2 import Geometry
from datetime import datetime
from typing import Optional
from enum import Enum

class VesselType(str, Enum):
    FISHING = "FISHING"
    CARGO = "CARGO"
    TANKER = "TANKER"
    PASSENGER = "PASSENGER"
    OTHER = "OTHER"

class VesselTrack(SQLModel, table=True):
    __tablename__ = "vessel_tracks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    mmsi: int = Field(index=True, nullable=False)
    vessel_type: Optional[VesselType] = None
    flag: Optional[str] = Field(max_length=3)
    location: str = Field(sa_column=Column(Geometry('POINT', srid=4326), nullable=False))
    timestamp: datetime = Field(index=True, nullable=False)
    is_dark: bool = Field(default=False)
    risk_score: float = Field(default=0.0)
    speed: Optional[float] = None
    course: Optional[float] = None
    
    class Config:
        arbitrary_types_allowed = True

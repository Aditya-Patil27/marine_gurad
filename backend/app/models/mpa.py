from sqlmodel import SQLModel, Field, Column
from geoalchemy2 import Geometry
from typing import Optional

class MarineProtectedArea(SQLModel, table=True):
    __tablename__ = "marine_protected_areas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False)
    designation: Optional[str] = Field(max_length=100)
    boundary: str = Field(sa_column=Column(Geometry('POLYGON', srid=4326), nullable=False))
    iucn_category: Optional[str] = Field(max_length=10)
    country: Optional[str] = Field(max_length=100)
    
    class Config:
        arbitrary_types_allowed = True

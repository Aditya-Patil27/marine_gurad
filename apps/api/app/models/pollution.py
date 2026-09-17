from sqlmodel import SQLModel, Field, Column
from geoalchemy2 import Geometry
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import uuid as uuid_pkg

class PollutionType(str, Enum):
    OIL = "OIL"
    PLASTIC = "PLASTIC"
    ALGAE = "ALGAE"

class PollutionEvent(SQLModel, table=True):
    __tablename__ = "pollution_events"

    id: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        nullable=False
    )
    type: PollutionType = Field(nullable=False)
    severity: float = Field(nullable=False)
    detected_at: datetime = Field(index=True, nullable=False)
    zone: Any = Field(sa_column=Column(Geometry('POLYGON', srid=4326), nullable=False))
    image_source: Optional[str] = Field(max_length=500)
    confidence: Optional[float] = None

    class Config:
        arbitrary_types_allowed = True

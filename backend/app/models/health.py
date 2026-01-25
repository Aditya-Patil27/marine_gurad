from sqlmodel import SQLModel, Field
from datetime import date as date_type
from typing import Optional

class OceanHealthMetric(SQLModel, table=True):
    __tablename__ = "ocean_health_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    region_id: int = Field(index=True, nullable=False)
    date: date_type = Field(index=True, nullable=False)
    ohi_score: Optional[float] = None
    temperature: Optional[float] = None
    ph: Optional[float] = None
    salinity: Optional[float] = None
    forecasted_score: Optional[float] = None

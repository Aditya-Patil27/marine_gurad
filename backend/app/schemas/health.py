from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class OceanHealthResponse(BaseModel):
    region_id: int
    date: date
    ohi_score: Optional[float]
    temperature: Optional[float]
    ph: Optional[float]
    salinity: Optional[float]
    forecasted_score: Optional[float]
    
    class Config:
        from_attributes = True

class OHITimeSeries(BaseModel):
    dates: List[str]
    ohi_scores: List[float]
    temperatures: List[float]
    ph_values: List[float]
    forecasts: List[Optional[float]]

from sqlmodel import SQLModel, Field, Column
from geoalchemy2 import Geometry
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class VesselType(str, Enum):
    FISHING = "FISHING"
    CARGO = "CARGO"
    TANKER = "TANKER"
    PASSENGER = "PASSENGER"
    TUG = "TUG"
    PILOT = "PILOT"
    SAR = "SAR"  # Search and Rescue
    MILITARY = "MILITARY"
    SAILING = "SAILING"
    PLEASURE = "PLEASURE"
    HIGH_SPEED = "HIGH_SPEED"
    OTHER = "OTHER"


# AIS Vessel Type Code Mapping (ITU-R M.1371-5)
# Maps numeric AIS codes to VesselType enum
AIS_TYPE_CODE_MAP = {
    # Fishing
    30: VesselType.FISHING,
    # Towing/Tug
    31: VesselType.TUG,
    32: VesselType.TUG,
    52: VesselType.TUG,
    # Cargo (70-79)
    70: VesselType.CARGO,
    71: VesselType.CARGO,
    72: VesselType.CARGO,
    73: VesselType.CARGO,
    74: VesselType.CARGO,
    75: VesselType.CARGO,
    76: VesselType.CARGO,
    77: VesselType.CARGO,
    78: VesselType.CARGO,
    79: VesselType.CARGO,
    # Tanker (80-89)
    80: VesselType.TANKER,
    81: VesselType.TANKER,
    82: VesselType.TANKER,
    83: VesselType.TANKER,
    84: VesselType.TANKER,
    85: VesselType.TANKER,
    86: VesselType.TANKER,
    87: VesselType.TANKER,
    88: VesselType.TANKER,
    89: VesselType.TANKER,
    # Passenger (60-69)
    60: VesselType.PASSENGER,
    61: VesselType.PASSENGER,
    62: VesselType.PASSENGER,
    63: VesselType.PASSENGER,
    64: VesselType.PASSENGER,
    65: VesselType.PASSENGER,
    66: VesselType.PASSENGER,
    67: VesselType.PASSENGER,
    68: VesselType.PASSENGER,
    69: VesselType.PASSENGER,
    # Pilot
    50: VesselType.PILOT,
    90: VesselType.PILOT,  # Pilot vessel in some datasets
    # SAR
    51: VesselType.SAR,
    # Military
    35: VesselType.MILITARY,
    # Sailing
    36: VesselType.SAILING,
    # Pleasure Craft
    37: VesselType.PLEASURE,
    # High Speed Craft (40-49)
    40: VesselType.HIGH_SPEED,
    41: VesselType.HIGH_SPEED,
    42: VesselType.HIGH_SPEED,
    43: VesselType.HIGH_SPEED,
    44: VesselType.HIGH_SPEED,
    45: VesselType.HIGH_SPEED,
    46: VesselType.HIGH_SPEED,
    47: VesselType.HIGH_SPEED,
    48: VesselType.HIGH_SPEED,
    49: VesselType.HIGH_SPEED,
}


def get_vessel_type_from_code(code: int) -> VesselType:
    """Convert AIS numeric vessel type code to VesselType enum."""
    return AIS_TYPE_CODE_MAP.get(code, VesselType.OTHER)


# AIS Navigation Status Codes (ITU-R M.1371-5)
NAV_STATUS_MAP = {
    0: "Under way using engine",
    1: "At anchor",
    2: "Not under command",
    3: "Restricted manoeuvrability",
    4: "Constrained by draught",
    5: "Moored",
    6: "Aground",
    7: "Engaged in fishing",
    8: "Under way sailing",
    9: "Reserved for HSC",
    10: "Reserved for WIG",
    11: "Reserved",
    12: "Reserved",
    13: "Reserved",
    14: "AIS-SART active",
    15: "Not defined",
}


class VesselTrack(SQLModel, table=True):
    __tablename__ = "vessel_tracks"

    id: Optional[int] = Field(default=None, primary_key=True)
    mmsi: int = Field(index=True, nullable=False)
    vessel_type: Optional[VesselType] = None
    flag: Optional[str] = Field(default=None, max_length=3)
    location: Any = Field(sa_column=Column(Geometry('POINT', srid=4326), nullable=False))
    timestamp: datetime = Field(index=True, nullable=False)
    is_dark: bool = Field(default=False)
    risk_score: float = Field(default=0.0)
    speed: Optional[float] = None  # SOG - Speed Over Ground (knots)
    course: Optional[float] = None  # COG - Course Over Ground (degrees)

    # New fields from AIS dataset
    heading: Optional[float] = None  # True heading (degrees, 0-359, 511=not available)
    vessel_name: Optional[str] = Field(default=None, max_length=50)
    imo: Optional[str] = Field(default=None, max_length=20)  # IMO number (e.g., "IMO1234567")
    callsign: Optional[str] = Field(default=None, max_length=10)
    nav_status: Optional[int] = None  # Navigation status code (0-15)
    length: Optional[float] = None  # Vessel length (meters)
    width: Optional[float] = None  # Vessel width/beam (meters)
    draft: Optional[float] = None  # Vessel draught (meters)
    cargo: Optional[int] = None  # Cargo type code
    transceiver_class: Optional[str] = Field(default=None, max_length=1)  # "A" or "B"

    class Config:
        arbitrary_types_allowed = True

    @property
    def nav_status_description(self) -> str:
        """Get human-readable navigation status."""
        if self.nav_status is None:
            return "Unknown"
        return NAV_STATUS_MAP.get(self.nav_status, "Not defined")

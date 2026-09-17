"""
Hardcoded demo data for BlueGuard hackathon presentation
This file contains realistic sample data for vessels, pollution events, MPAs, and alerts
"""

from datetime import datetime, timedelta
import random

# Demo Vessel Data - Indian Ocean and Arabian Sea region
DEMO_VESSELS = [
    {
        "mmsi": 123456789,
        "vessel_type": "Cargo",
        "flag": "IN",
        "coordinates": [72.8777, 19.0760],  # Mumbai coast
        "timestamp": datetime.utcnow() - timedelta(minutes=5),
        "speed": 12.5,
        "course": 45.0,
        "is_dark": False,
        "risk_score": 0.25
    },
    {
        "mmsi": 234567890,
        "vessel_type": "Tanker",
        "flag": "SA",
        "coordinates": [69.3451, 21.5122],  # Gujarat coast
        "timestamp": datetime.utcnow() - timedelta(minutes=3),
        "speed": 8.3,
        "course": 180.0,
        "is_dark": False,
        "risk_score": 0.65
    },
    {
        "mmsi": 345678901,
        "vessel_type": "Fishing",
        "flag": "LK",
        "coordinates": [80.2707, 13.0827],  # Chennai coast
        "timestamp": datetime.utcnow() - timedelta(minutes=8),
        "speed": 4.2,
        "course": 270.0,
        "is_dark": True,
        "risk_score": 0.82
    },
    {
        "mmsi": 456789012,
        "vessel_type": "Container Ship",
        "flag": "SG",
        "coordinates": [77.5946, 12.9716],  # Bangalore region
        "timestamp": datetime.utcnow() - timedelta(minutes=2),
        "speed": 18.7,
        "course": 90.0,
        "is_dark": False,
        "risk_score": 0.15
    },
    {
        "mmsi": 567890123,
        "vessel_type": "Fishing",
        "flag": "IN",
        "coordinates": [73.8567, 18.5204],  # Mumbai offshore
        "timestamp": datetime.utcnow() - timedelta(minutes=12),
        "speed": 3.8,
        "course": 135.0,
        "is_dark": False,
        "risk_score": 0.45
    },
    {
        "mmsi": 678901234,
        "vessel_type": "Tanker",
        "flag": "AE",
        "coordinates": [68.9685, 22.3072],  # Gulf of Kutch
        "timestamp": datetime.utcnow() - timedelta(minutes=7),
        "speed": 10.1,
        "course": 315.0,
        "is_dark": False,
        "risk_score": 0.72
    },
    {
        "mmsi": 789012345,
        "vessel_type": "Cargo",
        "flag": "CN",
        "coordinates": [75.7139, 11.2588],  # Kerala coast
        "timestamp": datetime.utcnow() - timedelta(minutes=4),
        "speed": 14.2,
        "course": 225.0,
        "is_dark": False,
        "risk_score": 0.35
    },
    {
        "mmsi": 890123456,
        "vessel_type": "Research Vessel",
        "flag": "IN",
        "coordinates": [79.8083, 11.9416],  # Tamil Nadu
        "timestamp": datetime.utcnow() - timedelta(minutes=10),
        "speed": 5.5,
        "course": 0.0,
        "is_dark": False,
        "risk_score": 0.10
    },
    {
        "mmsi": 901234567,
        "vessel_type": "Fishing",
        "flag": "MM",
        "coordinates": [85.3240, 20.9517],  # Odisha coast
        "timestamp": datetime.utcnow() - timedelta(minutes=6),
        "speed": 2.9,
        "course": 180.0,
        "is_dark": True,
        "risk_score": 0.88
    },
    {
        "mmsi": 112233445,
        "vessel_type": "Container Ship",
        "flag": "KR",
        "coordinates": [88.3639, 22.5726],  # Kolkata
        "timestamp": datetime.utcnow() - timedelta(minutes=15),
        "speed": 16.8,
        "course": 45.0,
        "is_dark": False,
        "risk_score": 0.20
    },
]

# Demo Pollution Events
DEMO_POLLUTION = [
    {
        "id": 1,
        "type": "OIL",
        "severity": 0.85,
        "detected_at": datetime.utcnow() - timedelta(hours=2),
        "confidence": 0.92,
        "image_source": "Sentinel-2",
        "bbox": [72.85, 18.90, 72.95, 19.10],  # Mumbai coast oil spill
    },
    {
        "id": 2,
        "type": "PLASTIC",
        "severity": 0.65,
        "detected_at": datetime.utcnow() - timedelta(hours=5),
        "confidence": 0.78,
        "image_source": "Sentinel-2",
        "bbox": [68.95, 22.25, 69.05, 22.35],  # Gulf of Kutch
    },
    {
        "id": 3,
        "type": "OIL",
        "severity": 0.75,
        "detected_at": datetime.utcnow() - timedelta(hours=12),
        "confidence": 0.88,
        "image_source": "Sentinel-2",
        "bbox": [79.80, 11.90, 79.90, 12.00],  # Tamil Nadu
    },
    {
        "id": 4,
        "type": "CHEMICAL",
        "severity": 0.55,
        "detected_at": datetime.utcnow() - timedelta(hours=8),
        "confidence": 0.72,
        "image_source": "Sentinel-2",
        "bbox": [80.25, 13.05, 80.35, 13.15],  # Chennai
    },
    {
        "id": 5,
        "type": "PLASTIC",
        "severity": 0.45,
        "detected_at": datetime.utcnow() - timedelta(hours=24),
        "confidence": 0.65,
        "image_source": "Sentinel-2",
        "bbox": [75.70, 11.20, 75.80, 11.30],  # Kerala
    },
]

# Demo Marine Protected Areas
DEMO_MPAS = [
    {
        "id": 1,
        "name": "Gulf of Mannar Marine National Park",
        "designation": "National Park",
        "iucn_category": "II",
        "country": "India",
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [78.8, 8.8],
                [79.5, 8.8],
                [79.5, 9.3],
                [78.8, 9.3],
                [78.8, 8.8]
            ]]
        }
    },
    {
        "id": 2,
        "name": "Marine National Park, Gulf of Kutch",
        "designation": "Marine National Park",
        "iucn_category": "II",
        "country": "India",
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [68.8, 22.2],
                [69.8, 22.2],
                [69.8, 22.8],
                [68.8, 22.8],
                [68.8, 22.2]
            ]]
        }
    },
    {
        "id": 3,
        "name": "Mahatma Gandhi Marine National Park",
        "designation": "National Park",
        "iucn_category": "II",
        "country": "India",
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [92.5, 11.5],
                [93.0, 11.5],
                [93.0, 12.0],
                [92.5, 12.0],
                [92.5, 11.5]
            ]]
        }
    },
    {
        "id": 4,
        "name": "Gahirmatha Marine Sanctuary",
        "designation": "Wildlife Sanctuary",
        "iucn_category": "IV",
        "country": "India",
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [86.7, 20.5],
                [87.2, 20.5],
                [87.2, 21.0],
                [86.7, 21.0],
                [86.7, 20.5]
            ]]
        }
    },
]

# Demo Alerts
DEMO_ALERTS = [
    {
        "id": 1,
        "type": "MPA_VIOLATION",
        "severity": "HIGH",
        "title": "Vessel Entering Protected Area",
        "description": "Fishing vessel MMSI 345678901 predicted to enter Gulf of Mannar MPA within 2 hours",
        "timestamp": datetime.utcnow() - timedelta(minutes=5),
        "mmsi": 345678901,
        "mpa_name": "Gulf of Mannar Marine National Park",
        "distance_km": 8.5,
        "risk_score": 0.82
    },
    {
        "id": 2,
        "type": "POLLUTION",
        "severity": "HIGH",
        "title": "Oil Spill Detected",
        "description": "Large oil spill detected off Mumbai coast, severity: 85%",
        "timestamp": datetime.utcnow() - timedelta(hours=2),
        "location": "Mumbai Coast",
        "pollution_type": "OIL",
        "confidence": 0.92
    },
    {
        "id": 3,
        "type": "IUU_FISHING",
        "severity": "MEDIUM",
        "title": "Dark Vessel Detected",
        "description": "Fishing vessel MMSI 901234567 operating with AIS transponder off",
        "timestamp": datetime.utcnow() - timedelta(minutes=15),
        "mmsi": 901234567,
        "vessel_type": "Fishing",
        "risk_score": 0.88
    },
    {
        "id": 4,
        "type": "MPA_VIOLATION",
        "severity": "HIGH",
        "title": "Tanker Near Protected Waters",
        "description": "Oil tanker MMSI 678901234 approaching Gulf of Kutch Marine Park",
        "timestamp": datetime.utcnow() - timedelta(minutes=30),
        "mmsi": 678901234,
        "mpa_name": "Marine National Park, Gulf of Kutch",
        "distance_km": 5.2,
        "risk_score": 0.72
    },
    {
        "id": 5,
        "type": "POLLUTION",
        "severity": "MEDIUM",
        "title": "Plastic Accumulation Zone",
        "description": "Significant plastic pollution detected in Gulf of Kutch",
        "timestamp": datetime.utcnow() - timedelta(hours=5),
        "location": "Gulf of Kutch",
        "pollution_type": "PLASTIC",
        "confidence": 0.78
    },
    {
        "id": 6,
        "type": "IUU_FISHING",
        "severity": "MEDIUM",
        "title": "Suspicious Vessel Activity",
        "description": "Vessel MMSI 234567890 showing irregular movement patterns",
        "timestamp": datetime.utcnow() - timedelta(hours=1),
        "mmsi": 234567890,
        "vessel_type": "Tanker",
        "risk_score": 0.65
    },
    {
        "id": 7,
        "type": "POLLUTION",
        "severity": "MEDIUM",
        "title": "Chemical Discharge Detected",
        "description": "Possible chemical discharge near Chennai port",
        "timestamp": datetime.utcnow() - timedelta(hours=8),
        "location": "Chennai Coast",
        "pollution_type": "CHEMICAL",
        "confidence": 0.72
    },
]

# Demo Statistics
DEMO_STATS = {
    "active_vessels": len(DEMO_VESSELS),
    "pollution_events_week": len(DEMO_POLLUTION),
    "high_risk_vessels": len([v for v in DEMO_VESSELS if v["risk_score"] > 0.7]),
    "mpas_monitored": len(DEMO_MPAS)
}

# Ocean Health Index Demo Data
DEMO_OHI_DATA = {
    "region_id": 1,
    "region_name": "Indian Ocean - Western Region",
    "current_score": 72.5,
    "historical_data": [
        {"date": (datetime.utcnow() - timedelta(days=30)).isoformat(), "score": 68.2},
        {"date": (datetime.utcnow() - timedelta(days=25)).isoformat(), "score": 69.1},
        {"date": (datetime.utcnow() - timedelta(days=20)).isoformat(), "score": 70.3},
        {"date": (datetime.utcnow() - timedelta(days=15)).isoformat(), "score": 71.0},
        {"date": (datetime.utcnow() - timedelta(days=10)).isoformat(), "score": 71.8},
        {"date": (datetime.utcnow() - timedelta(days=5)).isoformat(), "score": 72.5},
    ],
    "components": {
        "food_provision": 78.5,
        "biodiversity": 65.3,
        "clean_waters": 70.2,
        "carbon_storage": 82.1,
        "coastal_protection": 68.9,
        "tourism_recreation": 75.4,
        "livelihoods": 69.7,
        "sense_of_place": 73.8
    }
}

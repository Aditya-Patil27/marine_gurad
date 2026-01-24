#!/usr/bin/env python3
"""
Script to ingest AIS vessel data from Marine Cadastre or other sources
"""

import pandas as pd
import requests
from datetime import datetime
from app.database import SessionLocal
from app.models.vessel import VesselTrack, VesselType
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

def fetch_ais_data():
    """Fetch AIS data from Marine Cadastre or sample CSV"""
    
    # Sample data structure
    # In production, this would fetch from AISHub, MarineCadastre, or Global Fishing Watch
    
    sample_data = pd.DataFrame({
        'MMSI': [367123456, 367234567, 367345678],
        'LAT': [37.7749, 37.8044, 37.7849],
        'LON': [-122.4194, -122.2711, -122.4094],
        'BaseDateTime': [datetime.utcnow()] * 3,
        'VesselType': ['FISHING', 'CARGO', 'FISHING'],
        'Flag': ['USA', 'CHN', 'USA'],
        'Speed': [12.5, 18.2, 8.3],
        'Course': [245.0, 180.0, 90.0]
    })
    
    return sample_data

def store_ais_records(df: pd.DataFrame):
    """Store AIS records in database"""
    
    db = SessionLocal()
    inserted = 0
    
    try:
        for _, row in df.iterrows():
            try:
                # Create point geometry
                point = Point(row['LON'], row['LAT'])
                wkb_element = from_shape(point, srid=4326)
                
                # Create vessel track
                vessel_track = VesselTrack(
                    mmsi=int(row['MMSI']),
                    vessel_type=row['VesselType'],
                    flag=row['Flag'],
                    location=wkb_element,
                    timestamp=row['BaseDateTime'],
                    speed=row['Speed'],
                    course=row['Course'],
                    is_dark=False,
                    risk_score=0.0
                )
                
                db.add(vessel_track)
                inserted += 1
                
            except Exception as e:
                print(f"Error inserting record: {e}")
                continue
        
        db.commit()
        print(f"Inserted {inserted} AIS records")
        
    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Main execution"""
    print("Fetching AIS data...")
    df = fetch_ais_data()
    
    print(f"Retrieved {len(df)} AIS records")
    store_ais_records(df)
    
    print("AIS data ingestion complete")

if __name__ == "__main__":
    main()

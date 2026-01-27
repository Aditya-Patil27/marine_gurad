#!/usr/bin/env python3
"""
Script to ingest AIS vessel data from CSV files (Marine Cadastre format)
"""

import pandas as pd
import os
from datetime import datetime
from pathlib import Path
from app.database import SessionLocal
from app.models.vessel import VesselTrack, VesselType, get_vessel_type_from_code
from geoalchemy2.shape import from_shape
from shapely.geometry import Point


def load_ais_csv(file_path: str) -> pd.DataFrame:
    """Load AIS data from a CSV file."""
    print(f"Loading AIS data from: {file_path}")

    # Read CSV with appropriate dtypes
    df = pd.read_csv(file_path, dtype={
        'MMSI': int,
        'LAT': float,
        'LON': float,
        'SOG': float,
        'COG': float,
        'Heading': float,
        'VesselName': str,
        'IMO': str,
        'CallSign': str,
        'VesselType': float,  # Can have NaN
        'Status': float,  # Can have NaN
        'Length': float,
        'Width': float,
        'Draft': float,
        'Cargo': float,
        'TransceiverClass': str
    }, na_values=['', 'NA', 'N/A'])

    # Parse datetime
    df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'], format='ISO8601', utc=True)

    print(f"Loaded {len(df)} records")
    return df


def clean_ais_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate AIS data."""
    original_count = len(df)

    # Remove records with invalid coordinates
    df = df[(df['LAT'] >= -90) & (df['LAT'] <= 90)]
    df = df[(df['LON'] >= -180) & (df['LON'] <= 180)]

    # Remove records with missing MMSI
    df = df[df['MMSI'].notna()]

    # Filter out invalid heading values (511 = not available in AIS spec)
    # Keep the value but it will be handled in storage

    cleaned_count = len(df)
    if original_count != cleaned_count:
        print(f"Cleaned {original_count - cleaned_count} invalid records")

    return df


def store_ais_records(df: pd.DataFrame, batch_size: int = 1000):
    """Store AIS records in database with batch processing."""

    db = SessionLocal()
    inserted = 0
    errors = 0

    try:
        batch = []

        for idx, row in df.iterrows():
            try:
                # Create point geometry
                point = Point(row['LON'], row['LAT'])
                wkb_element = from_shape(point, srid=4326)

                # Convert vessel type code to enum
                vessel_type_code = row.get('VesselType')
                vessel_type = None
                if pd.notna(vessel_type_code):
                    vessel_type = get_vessel_type_from_code(int(vessel_type_code))

                # Handle heading (511 = not available in AIS spec)
                heading = row.get('Heading')
                if pd.notna(heading) and heading == 511.0:
                    heading = None

                # Handle nav status
                nav_status = row.get('Status')
                if pd.notna(nav_status):
                    nav_status = int(nav_status)
                else:
                    nav_status = None

                # Handle cargo
                cargo = row.get('Cargo')
                if pd.notna(cargo):
                    cargo = int(cargo)
                else:
                    cargo = None

                # Create vessel track record
                vessel_track = VesselTrack(
                    mmsi=int(row['MMSI']),
                    vessel_type=vessel_type,
                    flag=None,  # Not available in this CSV format
                    location=wkb_element,
                    timestamp=row['BaseDateTime'].to_pydatetime(),
                    speed=row.get('SOG') if pd.notna(row.get('SOG')) else None,
                    course=row.get('COG') if pd.notna(row.get('COG')) else None,
                    heading=heading if pd.notna(heading) else None,
                    vessel_name=row.get('VesselName') if pd.notna(row.get('VesselName')) else None,
                    imo=row.get('IMO') if pd.notna(row.get('IMO')) else None,
                    callsign=row.get('CallSign') if pd.notna(row.get('CallSign')) else None,
                    nav_status=nav_status,
                    length=row.get('Length') if pd.notna(row.get('Length')) else None,
                    width=row.get('Width') if pd.notna(row.get('Width')) else None,
                    draft=row.get('Draft') if pd.notna(row.get('Draft')) else None,
                    cargo=cargo,
                    transceiver_class=row.get('TransceiverClass') if pd.notna(row.get('TransceiverClass')) else None,
                    is_dark=False,  # Will be calculated by separate process
                    risk_score=0.0  # Will be calculated by ML model
                )

                batch.append(vessel_track)

                # Commit in batches for better performance
                if len(batch) >= batch_size:
                    db.add_all(batch)
                    db.commit()
                    inserted += len(batch)
                    print(f"Inserted {inserted} records...")
                    batch = []

            except Exception as e:
                errors += 1
                if errors <= 10:  # Only print first 10 errors
                    print(f"Error processing record {idx}: {e}")
                continue

        # Insert remaining records
        if batch:
            db.add_all(batch)
            db.commit()
            inserted += len(batch)

        print(f"Successfully inserted {inserted} AIS records ({errors} errors)")

    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main execution"""
    # Default CSV path (can be overridden via command line)
    default_csv = Path(__file__).parent.parent / "AIS_2024_01_01.csv"

    import sys
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = str(default_csv)

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print("Usage: python ingest_ais.py [path_to_csv]")
        sys.exit(1)

    print("Starting AIS data ingestion...")
    print(f"CSV file: {csv_path}")

    # Load and process data
    df = load_ais_csv(csv_path)
    df = clean_ais_data(df)

    # Store in database
    store_ais_records(df)

    print("AIS data ingestion complete")


if __name__ == "__main__":
    main()

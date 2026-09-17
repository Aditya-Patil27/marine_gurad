#!/usr/bin/env python3
"""
Script to load Marine Protected Areas from WDPA shapefile into PostGIS
"""

import sys
from pathlib import Path

# Allow running as `python scripts/<name>.py` from apps/api/ (makes `app` importable)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shapely.geometry import shape
from sqlmodel import select
from geoalchemy2.shape import from_shape
from app.database import SessionLocal
from app.models.mpa import MarineProtectedArea

def load_sample_mpas(db=None):
    """Load or update sample MPA data (in production, would load from WDPA shapefile)"""

    owns_session = db is None
    db = db or SessionLocal()

    # Sample MPAs for Indian Ocean region (Gulf of Mannar and Gulf of Kutch)
    sample_mpas = [
        {
            "name": "Gulf of Mannar Marine National Park",
            "designation": "Marine National Park",
            "iucn_category": "II",
            "country": "India",
            # Indicative outline offshore of the island chain; replace with WDPA before real use
            "coordinates": [
                [(79.29, 9.15), (79.08, 9.1), (78.86, 9.05), (78.61, 8.96), (78.41, 8.83), (78.26, 8.68),
                 (78.3, 8.6), (78.46, 8.72), (78.68, 8.86), (78.92, 8.96), (79.12, 9.01), (79.32, 9.07),
                 (79.29, 9.15)]
            ]
        },
        {
            "name": "Gulf of Kutch Marine National Park",
            "designation": "Marine National Park",
            "iucn_category": "II",
            "country": "India",
            "coordinates": [
                [(68.5, 22.2), (70.0, 22.2), (70.0, 23.0), (68.5, 23.0), (68.5, 22.2)]
            ]
        },
        {
            "name": "Malvan Marine Sanctuary",
            "designation": "Marine Sanctuary",
            "iucn_category": "IV",
            "country": "India",
            "coordinates": [
                [(73.4, 15.9), (73.5, 15.9), (73.5, 16.1), (73.4, 16.1), (73.4, 15.9)]
            ]
        },
        {
            "name": "Pigeon Island National Park",
            "designation": "National Park",
            "iucn_category": "II",
            "country": "Sri Lanka",
            "coordinates": [
                [(81.2, 8.7), (81.3, 8.7), (81.3, 8.8), (81.2, 8.8), (81.2, 8.7)]
            ]
        },
        {
            "name": "Bar Reef Marine Sanctuary",
            "designation": "Marine Sanctuary",
            "iucn_category": "IV",
            "country": "Sri Lanka",
            "coordinates": [
                [(79.62, 8.3), (79.76, 8.3), (79.76, 8.5), (79.62, 8.5), (79.62, 8.3)]
            ]
        }
    ]

    inserted = 0

    try:
        for mpa_data in sample_mpas:
            from shapely.geometry import Polygon

            polygon = Polygon(mpa_data['coordinates'][0])
            wkb_element = from_shape(polygon, srid=4326)

            mpa = db.exec(select(MarineProtectedArea).where(MarineProtectedArea.name == mpa_data['name'])).first()
            if mpa is None:
                mpa = MarineProtectedArea(name=mpa_data['name'])
                db.add(mpa)
                inserted += 1
            mpa.designation = mpa_data['designation']
            mpa.iucn_category = mpa_data['iucn_category']
            mpa.country = mpa_data['country']
            mpa.boundary = wkb_element

        db.commit()
        print(f"Loaded {len(sample_mpas)} Marine Protected Areas ({inserted} new, the rest updated)")

    except Exception as e:
        print(f"Error loading MPAs: {e}")
        db.rollback()
    finally:
        if owns_session:
            db.close()

def load_from_shapefile(shapefile_path: str):
    """Load MPAs from WDPA shapefile (for production use)"""
    import fiona  # Only needed for shapefiles; keeps sample loading free of GDAL

    db = SessionLocal()
    inserted = 0
    
    try:
        with fiona.open(shapefile_path) as source:
            for feature in source:
                try:
                    geom = shape(feature['geometry'])
                    wkb_element = from_shape(geom, srid=4326)
                    
                    mpa = MarineProtectedArea(
                        name=feature['properties'].get('NAME', 'Unknown'),
                        designation=feature['properties'].get('DESIG', ''),
                        iucn_category=feature['properties'].get('IUCN_CAT', ''),
                        country=feature['properties'].get('COUNTRY', ''),
                        boundary=wkb_element
                    )
                    
                    db.add(mpa)
                    inserted += 1
                    
                    if inserted % 100 == 0:
                        db.commit()
                        print(f"Loaded {inserted} MPAs...")
                        
                except Exception as e:
                    print(f"Error loading feature: {e}")
                    continue
        
        db.commit()
        print(f"Total MPAs loaded: {inserted}")
        
    except Exception as e:
        print(f"Error reading shapefile: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Main execution"""
    import sys
    
    if len(sys.argv) > 1:
        # Load from shapefile
        shapefile_path = sys.argv[1]
        print(f"Loading MPAs from {shapefile_path}...")
        load_from_shapefile(shapefile_path)
    else:
        # Load sample data
        print("Loading sample MPA data...")
        load_sample_mpas()

if __name__ == "__main__":
    main()

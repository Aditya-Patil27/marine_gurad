#!/usr/bin/env python3
"""
Script to load Marine Protected Areas from WDPA shapefile into PostGIS
"""

import fiona
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
from app.database import SessionLocal
from app.models.mpa import MarineProtectedArea

def load_sample_mpas():
    """Load sample MPA data (in production, would load from WDPA shapefile)"""

    db = SessionLocal()

    # Sample MPAs for Indian Ocean region (Gulf of Mannar and Gulf of Kutch)
    sample_mpas = [
        {
            "name": "Gulf of Mannar Marine National Park",
            "designation": "Marine National Park",
            "iucn_category": "II",
            "country": "India",
            "coordinates": [
                [(78.8, 8.7), (79.3, 8.7), (79.3, 9.3), (78.8, 9.3), (78.8, 8.7)]
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
                [(79.7, 8.3), (79.9, 8.3), (79.9, 8.5), (79.7, 8.5), (79.7, 8.3)]
            ]
        }
    ]

    inserted = 0

    try:
        for mpa_data in sample_mpas:
            from shapely.geometry import Polygon

            polygon = Polygon(mpa_data['coordinates'][0])
            wkb_element = from_shape(polygon, srid=4326)

            mpa = MarineProtectedArea(
                name=mpa_data['name'],
                designation=mpa_data['designation'],
                iucn_category=mpa_data['iucn_category'],
                country=mpa_data['country'],
                boundary=wkb_element
            )

            db.add(mpa)
            inserted += 1

        db.commit()
        print(f"Loaded {inserted} Marine Protected Areas in Indian Ocean region")

    except Exception as e:
        print(f"Error loading MPAs: {e}")
        db.rollback()
    finally:
        db.close()

def load_from_shapefile(shapefile_path: str):
    """Load MPAs from WDPA shapefile (for production use)"""
    
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

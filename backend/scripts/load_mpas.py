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
    
    # Sample MPAs (hardcoded for MVP)
    sample_mpas = [
        {
            "name": "Monterey Bay National Marine Sanctuary",
            "designation": "National Marine Sanctuary",
            "iucn_category": "IV",
            "country": "USA",
            "coordinates": [
                [(-122.5, 36.5), (-121.5, 36.5), (-121.5, 37.5), (-122.5, 37.5), (-122.5, 36.5)]
            ]
        },
        {
            "name": "Channel Islands National Marine Sanctuary",
            "designation": "National Marine Sanctuary",
            "iucn_category": "II",
            "country": "USA",
            "coordinates": [
                [(-120.5, 33.5), (-119.0, 33.5), (-119.0, 34.5), (-120.5, 34.5), (-120.5, 33.5)]
            ]
        },
        {
            "name": "Papahānaumokuākea Marine National Monument",
            "designation": "National Monument",
            "iucn_category": "Ia",
            "country": "USA",
            "coordinates": [
                [(-179.0, 23.0), (-160.0, 23.0), (-160.0, 28.0), (-179.0, 28.0), (-179.0, 23.0)]
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
        print(f"Loaded {inserted} Marine Protected Areas")
        
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

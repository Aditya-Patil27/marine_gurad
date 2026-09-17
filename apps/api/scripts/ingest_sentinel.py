#!/usr/bin/env python3
"""
Script to ingest Sentinel satellite imagery from Copernicus
This is a mock implementation for MVP
"""

import sys
from pathlib import Path

# Allow running as `python scripts/<name>.py` from apps/api/ (makes `app` importable)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import httpx
from datetime import datetime
from app.database import SessionLocal
from app.services.pollution_detector import PollutionDetector
from app.models.pollution import PollutionEvent, PollutionType
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
import uuid

async def fetch_sentinel_image():
    """Mock Copernicus OData API response"""

    # In production, this would call the actual Copernicus API
    # For MVP, we'll use a sample image URL with metadata

    # Indian Ocean region around Gulf of Mannar (focus area)
    sample_images = [
        {
            "url": "https://example.com/sentinel/oil_spill_sample.jpg",
            "bounds": [78.0, 8.0, 79.5, 9.5],  # [min_lon, min_lat, max_lon, max_lat] Gulf of Mannar
            "width": 1024,
            "height": 1024
        },
        {
            "url": "https://example.com/sentinel/plastic_debris.jpg",
            "bounds": [68.0, 20.0, 70.0, 23.0],  # Gulf of Kutch
            "width": 1024,
            "height": 1024
        },
    ]

    return sample_images[0]

async def process_and_store_detection(image_data: dict):
    """Process image and store pollution detections"""

    detector = PollutionDetector()
    db = SessionLocal()

    try:
        # Detect pollution with geographic metadata
        metadata = {
            "bounds": image_data["bounds"],
            "width": image_data["width"],
            "height": image_data["height"]
        }
        detections = await detector.detect(image_data["url"], metadata)

        for detection in detections:
            # Use geographic bounding box if available
            if "geo_bbox" in detection:
                geo_bbox = detection["geo_bbox"]
                # Create polygon from geographic bounding box
                polygon = Polygon([
                    (geo_bbox[0], geo_bbox[1]),  # min_lon, min_lat
                    (geo_bbox[2], geo_bbox[1]),  # max_lon, min_lat
                    (geo_bbox[2], geo_bbox[3]),  # max_lon, max_lat
                    (geo_bbox[0], geo_bbox[3]),  # min_lon, max_lat
                    (geo_bbox[0], geo_bbox[1])   # close polygon
                ])
            else:
                # Fallback: use center of image bounds with small polygon
                bounds = image_data["bounds"]
                center_lon = (bounds[0] + bounds[2]) / 2
                center_lat = (bounds[1] + bounds[3]) / 2
                offset = 0.01  # ~1km
                polygon = Polygon([
                    (center_lon - offset, center_lat - offset),
                    (center_lon + offset, center_lat - offset),
                    (center_lon + offset, center_lat + offset),
                    (center_lon - offset, center_lat + offset),
                    (center_lon - offset, center_lat - offset)
                ])

            wkb_element = from_shape(polygon, srid=4326)

            try:
                pollution_type = PollutionType(detection['type'])
            except ValueError:
                continue  # Skip classes the model can't map to a pollution type

            # Create pollution event
            event = PollutionEvent(
                id=uuid.uuid4(),
                type=pollution_type,
                severity=detection['confidence'],
                detected_at=datetime.utcnow(),
                zone=wkb_element,
                image_source=image_data["url"],
                confidence=detection['confidence']
            )

            db.add(event)

        db.commit()
        print(f"Stored {len(detections)} pollution detections")

    except Exception as e:
        print(f"Error processing image: {e}")
        db.rollback()
    finally:
        db.close()

async def main():
    """Main ingestion loop"""
    print("Starting Sentinel data ingestion...")

    while True:
        try:
            image_data = await fetch_sentinel_image()
            await process_and_store_detection(image_data)

            # Wait before next fetch (e.g., every 6 hours)
            await asyncio.sleep(21600)

        except KeyboardInterrupt:
            print("Stopping ingestion...")
            break
        except Exception as e:
            print(f"Error in ingestion loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())

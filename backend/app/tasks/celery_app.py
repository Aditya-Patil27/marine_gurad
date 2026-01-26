from celery import Celery
from app.config import settings
import asyncio

celery_app = Celery(
    "blueguard",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="process_satellite_image")
def process_satellite_image(image_url: str, metadata: dict = None):
    """Background task to process satellite imagery"""
    from app.services.pollution_detector import PollutionDetector
    from app.database import SessionLocal
    from app.models.pollution import PollutionEvent, PollutionType
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon
    from datetime import datetime
    import uuid

    detector = PollutionDetector()

    # Run async detection in sync context using asyncio.run()
    detections = asyncio.run(detector.detect(image_url, metadata))

    # Store detections in database
    db = SessionLocal()
    try:
        for detection in detections:
            # Use geographic bounding box if available
            if "geo_bbox" in detection and metadata:
                geo_bbox = detection["geo_bbox"]
                polygon = Polygon([
                    (geo_bbox[0], geo_bbox[1]),
                    (geo_bbox[2], geo_bbox[1]),
                    (geo_bbox[2], geo_bbox[3]),
                    (geo_bbox[0], geo_bbox[3]),
                    (geo_bbox[0], geo_bbox[1])
                ])
            elif metadata and "bounds" in metadata:
                # Fallback: use center of image bounds
                bounds = metadata["bounds"]
                center_lon = (bounds[0] + bounds[2]) / 2
                center_lat = (bounds[1] + bounds[3]) / 2
                offset = 0.01
                polygon = Polygon([
                    (center_lon - offset, center_lat - offset),
                    (center_lon + offset, center_lat - offset),
                    (center_lon + offset, center_lat + offset),
                    (center_lon - offset, center_lat + offset),
                    (center_lon - offset, center_lat - offset)
                ])
            else:
                # Default fallback
                polygon = Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)])

            wkb_element = from_shape(polygon, srid=4326)

            event = PollutionEvent(
                id=uuid.uuid4(),
                type=PollutionType(detection['type']),
                severity=detection['confidence'],
                detected_at=datetime.utcnow(),
                zone=wkb_element,
                image_source=image_url,
                confidence=detection['confidence']
            )

            db.add(event)

        db.commit()
        print(f"Processed {len(detections)} detections from {image_url}")
        return {"status": "completed", "detections": len(detections)}

    except Exception as e:
        db.rollback()
        print(f"Error processing image: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()

@celery_app.task(name="calculate_vessel_risk")
def calculate_vessel_risk(mmsi: int):
    """Background task to calculate vessel IUU risk score"""
    # Would analyze vessel behavior patterns
    print(f"Calculating risk for vessel: {mmsi}")
    return {"mmsi": mmsi, "risk_score": 0.5}

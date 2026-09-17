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
    # Configure worker concurrency for ML tasks
    worker_prefetch_multiplier=1,  # One task at a time for GPU tasks
    task_acks_late=True,  # Acknowledge after completion
)

@celery_app.task(name="process_satellite_image", bind=True, max_retries=3)
def process_satellite_image(self, image_url: str, metadata: dict = None):
    """
    Background Celery task to process satellite imagery for pollution detection.
    
    This task runs entirely within the Celery worker, keeping deep learning
    inference off the main FastAPI thread. Uses synchronous HTTP and model
    inference to avoid event loop issues in Celery.
    
    Args:
        image_url: URL of the satellite image to process
        metadata: Optional dict with geographic bounds and image dimensions
                 Format: {"bounds": [min_lon, min_lat, max_lon, max_lat]}
    
    Returns:
        Dict with status and detection count
    """
    from app.services.pollution_detector import PollutionDetector
    from app.database import SessionLocal
    from app.models.pollution import PollutionEvent, PollutionType
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon
    from datetime import datetime
    import uuid

    detector = PollutionDetector()
    if detector.model is None:
        return {"status": "failed", "error": "Pollution detection model is not loaded"}

    # Use synchronous detection method for Celery compatibility
    # This avoids asyncio.run() which can cause issues with Celery's event loop
    try:
        detections = detector.detect_sync(image_url, metadata)
    except Exception as e:
        print(f"Detection failed, retrying: {e}")
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds

    # Store detections in database
    db = SessionLocal()
    try:
        for detection in detections:
            try:
                pollution_type = PollutionType(detection['type'])
            except ValueError:
                continue  # Skip classes the model can't map to a pollution type

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
                type=pollution_type,
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


@celery_app.task(name="batch_process_satellite_images", bind=True)
def batch_process_satellite_images(self, image_urls: list, metadata_list: list = None):
    """
    Process multiple satellite images in batch.
    
    This task processes images sequentially to avoid overwhelming GPU memory.
    For parallel processing across multiple workers, dispatch individual
    process_satellite_image tasks instead.
    
    Args:
        image_urls: List of image URLs to process
        metadata_list: Optional list of metadata dicts (one per image)
    
    Returns:
        Dict with overall status and per-image results
    """
    results = []
    metadata_list = metadata_list or [None] * len(image_urls)
    
    for url, metadata in zip(image_urls, metadata_list):
        try:
            result = process_satellite_image(url, metadata)
            results.append({"url": url, **result})
        except Exception as e:
            results.append({"url": url, "status": "failed", "error": str(e)})
    
    successful = sum(1 for r in results if r.get("status") == "completed")
    return {
        "status": "completed",
        "total": len(image_urls),
        "successful": successful,
        "failed": len(image_urls) - successful,
        "results": results
    }


@celery_app.task(name="calculate_vessel_risk")
def calculate_vessel_risk(mmsi: int):
    """Background task to calculate vessel IUU risk score"""
    # Would analyze vessel behavior patterns
    print(f"Calculating risk for vessel: {mmsi}")
    return {"mmsi": mmsi, "risk_score": 0.5}

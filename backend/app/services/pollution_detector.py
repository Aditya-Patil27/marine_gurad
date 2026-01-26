import torch
from ultralytics import YOLO
from PIL import Image
import httpx
from io import BytesIO
from typing import List, Dict
import numpy as np
from app.config import settings
import os

class PollutionDetector:
    """Singleton service for pollution detection using YOLOv8"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """Load YOLOv8 model"""
        try:
            if os.path.exists(settings.YOLO_MODEL_PATH):
                self.model = YOLO(settings.YOLO_MODEL_PATH)
                self.model.to(self.device)
                print(f"Loaded pollution detection model on {self.device}")
            else:
                # Use pretrained model as fallback
                print("Custom model not found, using YOLOv8n pretrained")
                self.model = YOLO('yolov8n.pt')
                self.model.to(self.device)
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None
    
    async def detect(self, image_url: str, metadata: dict = None) -> List[Dict]:
        """
        Detect pollution in satellite image

        Args:
            image_url: URL to satellite image
            metadata: Optional metadata containing geographic bounds of the image
                     Expected format: {"bounds": [min_lon, min_lat, max_lon, max_lat],
                                      "width": image_width_px, "height": image_height_px}

        Returns:
            List of detection results with bounding boxes, confidence, and geographic coordinates
        """
        if self.model is None:
            return []

        try:
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))

            # Get image dimensions
            img_width, img_height = image.size

            # Run inference
            results = self.model(image, conf=settings.POLLUTION_CONFIDENCE_THRESHOLD)

            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])

                    detection = {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": confidence,
                        "class": class_id,
                        "type": self._get_pollution_type(class_id)
                    }

                    # Convert pixel coordinates to geographic if metadata provided
                    if metadata and "bounds" in metadata:
                        geo_bbox = self._pixel_to_geo(
                            [x1, y1, x2, y2],
                            img_width,
                            img_height,
                            metadata["bounds"]
                        )
                        detection["geo_bbox"] = geo_bbox

                    detections.append(detection)

            return detections

        except Exception as e:
            print(f"Error in pollution detection: {e}")
            return []

    def _pixel_to_geo(self, bbox_px: List[float], img_width: int, img_height: int,
                      bounds: List[float]) -> List[float]:
        """
        Convert pixel bounding box to geographic coordinates

        Args:
            bbox_px: [x1, y1, x2, y2] in pixels
            img_width: Image width in pixels
            img_height: Image height in pixels
            bounds: [min_lon, min_lat, max_lon, max_lat] of the image

        Returns:
            [min_lon, min_lat, max_lon, max_lat] of the detection
        """
        min_lon, min_lat, max_lon, max_lat = bounds
        x1, y1, x2, y2 = bbox_px

        # Calculate degrees per pixel
        lon_per_px = (max_lon - min_lon) / img_width
        lat_per_px = (max_lat - min_lat) / img_height

        # Convert pixel coords to geographic coords
        # Note: y increases downward in image coordinates but upward in geographic
        geo_min_lon = min_lon + (x1 * lon_per_px)
        geo_max_lon = min_lon + (x2 * lon_per_px)
        geo_max_lat = max_lat - (y1 * lat_per_px)
        geo_min_lat = max_lat - (y2 * lat_per_px)

        return [geo_min_lon, geo_min_lat, geo_max_lon, geo_max_lat]
    
    def _get_pollution_type(self, class_id: int) -> str:
        """Map class ID to pollution type"""
        mapping = {
            0: "OIL",
            1: "PLASTIC",
            2: "ALGAE"
        }
        return mapping.get(class_id, "UNKNOWN")

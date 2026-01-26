import torch
from ultralytics import YOLO
from PIL import Image
import httpx
from io import BytesIO
from typing import List, Dict, Optional
import numpy as np
from app.config import settings
import os
import requests

from app.services.model_registry import get_model_registry, StorageBackend


class PollutionDetector:
    """
    Singleton service for pollution detection using YOLOv8.
    
    IMPORTANT: This detector is designed to be used within Celery workers
    to avoid blocking the main FastAPI event loop. The synchronous `detect_sync`
    method should be used in Celery tasks, while `detect` can be used for
    direct async calls if needed.
    
    Model Loading:
    - Supports local files, Supabase Storage, S3, and HTTP URLs
    - Uses the model registry for versioning and caching
    - Falls back to pretrained YOLOv8n if custom model not available
    """
    
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
        """
        Load YOLOv8 model using the model registry.
        
        Attempts to load in this order:
        1. From model registry (supports remote storage)
        2. From local filesystem path
        3. Pretrained YOLOv8n as fallback
        """
        try:
            model_path = None
            
            # Try loading from model registry first
            if settings.MODEL_STORAGE_BACKEND != "local" and settings.YOLO_MODEL_REMOTE_PATH:
                registry = get_model_registry()
                
                # Register model if not already registered
                if not registry.get_model_metadata("pollution_yolo", settings.YOLO_MODEL_VERSION):
                    backend = StorageBackend(settings.MODEL_STORAGE_BACKEND)
                    registry.register_model(
                        name="pollution_yolo",
                        version=settings.YOLO_MODEL_VERSION,
                        backend=backend,
                        path=settings.YOLO_MODEL_REMOTE_PATH,
                        description="YOLOv8 pollution detection model"
                    )
                
                # Get model (downloads if needed)
                model_path = registry.get_model("pollution_yolo", settings.YOLO_MODEL_VERSION)
                
                if model_path:
                    print(f"Loading YOLO model from registry: {model_path}")
            
            # Fallback to local path
            if not model_path and os.path.exists(settings.YOLO_MODEL_PATH):
                model_path = settings.YOLO_MODEL_PATH
                print(f"Loading YOLO model from local path: {model_path}")
            
            if model_path:
                self.model = YOLO(model_path)
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
    
    def reload_model(self, version: Optional[str] = None, force_download: bool = False):
        """
        Reload the model, optionally with a different version.
        
        Args:
            version: Specific model version to load, or None for latest
            force_download: Re-download even if cached
        """
        try:
            registry = get_model_registry()
            model_path = registry.get_model(
                "pollution_yolo",
                version=version,
                force_download=force_download
            )
            
            if model_path:
                self.model = YOLO(model_path)
                self.model.to(self.device)
                print(f"Reloaded YOLO model v{version or 'latest'} on {self.device}")
            else:
                print("Failed to reload model")
                
        except Exception as e:
            print(f"Error reloading model: {e}")
    
    def detect_sync(self, image_url: str, metadata: dict = None) -> List[Dict]:
        """
        Synchronous detection method for use in Celery workers.
        
        This method uses synchronous HTTP requests to avoid event loop issues
        when called from Celery tasks. Use this instead of `detect` in background tasks.

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
            # Use synchronous requests for Celery compatibility
            response = requests.get(image_url, timeout=30.0)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))

            return self._run_inference(image, image_url, metadata)

        except Exception as e:
            print(f"Error in pollution detection (sync): {e}")
            return []

    async def detect(self, image_url: str, metadata: dict = None) -> List[Dict]:
        """
        Asynchronous detection method.
        
        WARNING: This method should NOT be called from Celery tasks as it uses
        async HTTP. Use `detect_sync` for Celery workers instead.

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
            # Download image asynchronously
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))

            return self._run_inference(image, image_url, metadata)

        except Exception as e:
            print(f"Error in pollution detection: {e}")
            return []

    def _run_inference(self, image: Image.Image, image_url: str, metadata: Optional[dict]) -> List[Dict]:
        """
        Run YOLO inference on the image.
        
        This is the core inference logic shared between sync and async methods.
        Kept as a separate method to avoid code duplication.
        """
        # Get image dimensions
        img_width, img_height = image.size

        # Run inference (this is CPU/GPU bound, not I/O bound)
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

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
    
    async def detect(self, image_url: str) -> List[Dict]:
        """
        Detect pollution in satellite image
        
        Args:
            image_url: URL to satellite image
            
        Returns:
            List of detection results with bounding boxes and confidence
        """
        if self.model is None:
            return []
        
        try:
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            
            # Run inference
            results = self.model(image, conf=settings.POLLUTION_CONFIDENCE_THRESHOLD)
            
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": confidence,
                        "class": class_id,
                        "type": self._get_pollution_type(class_id)
                    })
            
            return detections
            
        except Exception as e:
            print(f"Error in pollution detection: {e}")
            return []
    
    def _get_pollution_type(self, class_id: int) -> str:
        """Map class ID to pollution type"""
        mapping = {
            0: "OIL",
            1: "PLASTIC",
            2: "ALGAE"
        }
        return mapping.get(class_id, "UNKNOWN")

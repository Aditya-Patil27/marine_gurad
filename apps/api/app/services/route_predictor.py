import torch
import torch.nn as nn
import numpy as np
from typing import List, Tuple, Optional, Union
from shapely.geometry import LineString, Point
from app.config import settings
import os

from app.services.model_registry import get_model_registry, StorageBackend


class VesselLSTM(nn.Module):
    """LSTM model for vessel trajectory prediction"""
    
    def __init__(self, input_size=2, hidden_size=64, num_layers=2, output_size=2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


class RoutePredictor:
    """
    Service for predicting vessel trajectories using LSTM.
    
    Model Loading:
    - Supports local files, Supabase Storage, S3, and HTTP URLs
    - Uses the model registry for versioning and caching
    - Falls back to linear extrapolation if weights are not available
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
        self.weights_loaded = False
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """
        Load LSTM model using the model registry.
        
        Attempts to load in this order:
        1. From model registry (supports remote storage)
        2. From local filesystem path
        3. No weights: predictions use linear extrapolation
        """
        try:
            self.model = VesselLSTM()
            model_path = None
            
            # Try loading from model registry first
            if settings.MODEL_STORAGE_BACKEND != "local" and settings.LSTM_MODEL_REMOTE_PATH:
                registry = get_model_registry()
                
                # Register model if not already registered
                if not registry.get_model_metadata("route_lstm", settings.LSTM_MODEL_VERSION):
                    backend = StorageBackend(settings.MODEL_STORAGE_BACKEND)
                    registry.register_model(
                        name="route_lstm",
                        version=settings.LSTM_MODEL_VERSION,
                        backend=backend,
                        path=settings.LSTM_MODEL_REMOTE_PATH,
                        description="LSTM vessel trajectory prediction model"
                    )
                
                # Get model (downloads if needed)
                model_path = registry.get_model("route_lstm", settings.LSTM_MODEL_VERSION)
                
                if model_path:
                    print(f"Loading LSTM model from registry: {model_path}")
            
            # Fallback to local path
            if not model_path and os.path.exists(settings.LSTM_MODEL_PATH):
                model_path = settings.LSTM_MODEL_PATH
                print(f"Loading LSTM model from local path: {model_path}")
            
            if model_path:
                # weights_only avoids executing arbitrary pickled code from downloaded files
                self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
                self.weights_loaded = True
                print(f"Loaded route prediction model on {self.device}")
            else:
                print("LSTM model weights not found, using linear extrapolation")
            
            self.model.to(self.device)
            self.model.eval()
            
        except Exception as e:
            print(f"Error loading LSTM model: {e}")
            self.model = None
            self.weights_loaded = False
    
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
                "route_lstm",
                version=version,
                force_download=force_download
            )
            
            if model_path:
                self.model = VesselLSTM()
                self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
                self.model.to(self.device)
                self.model.eval()
                self.weights_loaded = True
                print(f"Reloaded LSTM model v{version or 'latest'} on {self.device}")
            else:
                print("Failed to reload model")
                
        except Exception as e:
            print(f"Error reloading model: {e}")
    
    def predict_trajectory(
        self,
        positions: List[Tuple[float, float]],
        steps: int = 6
    ) -> Union[LineString, Point]:
        """
        Predict future vessel positions
        
        Args:
            positions: List of (lon, lat) tuples (last 10 positions)
            steps: Number of future steps to predict
            
        Returns:
            LineString of predicted trajectory, or a Point when only one position is known
        """
        # An LSTM with random weights produces meaningless tracks, so only use it when trained
        if self.model is None or not self.weights_loaded or len(positions) < 3:
            # Return simple linear extrapolation as fallback
            return self._linear_extrapolation(positions, steps)
        
        try:
            # Normalize positions
            positions_array = np.array(positions)
            mean = positions_array.mean(axis=0)
            std = positions_array.std(axis=0) + 1e-6
            normalized = (positions_array - mean) / std
            
            # Prepare input tensor
            x = torch.FloatTensor(normalized).unsqueeze(0).to(self.device)
            
            # Predict future positions
            predicted_positions = list(positions)
            
            with torch.no_grad():
                for _ in range(steps):
                    pred = self.model(x)
                    pred_np = pred.cpu().numpy()[0]
                    
                    # Denormalize
                    pred_denorm = pred_np * std + mean
                    predicted_positions.append(tuple(pred_denorm))
                    
                    # Update input for next prediction
                    new_input = torch.FloatTensor((pred_np - mean) / std).unsqueeze(0).unsqueeze(0).to(self.device)
                    x = torch.cat([x[:, 1:, :], new_input], dim=1)
            
            return LineString(predicted_positions)
            
        except Exception as e:
            print(f"Error in trajectory prediction: {e}")
            return self._linear_extrapolation(positions, steps)
    
    def _linear_extrapolation(
        self,
        positions: List[Tuple[float, float]],
        steps: int
    ) -> Union[LineString, Point]:
        """Simple linear extrapolation fallback"""
        if len(positions) < 2:
            # A LineString needs two coordinates; with one fix we can't extrapolate
            return Point(positions[0])
        
        # Calculate velocity from last two positions
        p1 = np.array(positions[-2])
        p2 = np.array(positions[-1])
        velocity = p2 - p1
        
        # Extrapolate
        predicted = list(positions)
        for i in range(1, steps + 1):
            next_pos = p2 + velocity * i
            predicted.append(tuple(next_pos))
        
        return LineString(predicted)

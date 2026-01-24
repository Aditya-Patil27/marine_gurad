import torch
import torch.nn as nn
import numpy as np
from typing import List, Tuple
from shapely.geometry import LineString, Point
from app.config import settings
import os

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
    """Service for predicting vessel trajectories using LSTM"""
    
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
        """Load LSTM model"""
        try:
            self.model = VesselLSTM()
            
            if os.path.exists(settings.LSTM_MODEL_PATH):
                self.model.load_state_dict(torch.load(settings.LSTM_MODEL_PATH, map_location=self.device))
                print(f"Loaded route prediction model on {self.device}")
            else:
                print("LSTM model weights not found, using untrained model")
            
            self.model.to(self.device)
            self.model.eval()
            
        except Exception as e:
            print(f"Error loading LSTM model: {e}")
            self.model = None
    
    def predict_trajectory(
        self,
        positions: List[Tuple[float, float]],
        steps: int = 6
    ) -> LineString:
        """
        Predict future vessel positions
        
        Args:
            positions: List of (lon, lat) tuples (last 10 positions)
            steps: Number of future steps to predict
            
        Returns:
            LineString of predicted trajectory
        """
        if self.model is None or len(positions) < 3:
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
                    new_input = torch.FloatTensor((pred_np - mean) / std).unsqueeze(0).unsqueeze(0)
                    x = torch.cat([x[:, 1:, :], new_input], dim=1)
            
            return LineString(predicted_positions)
            
        except Exception as e:
            print(f"Error in trajectory prediction: {e}")
            return self._linear_extrapolation(positions, steps)
    
    def _linear_extrapolation(
        self,
        positions: List[Tuple[float, float]],
        steps: int
    ) -> LineString:
        """Simple linear extrapolation fallback"""
        if len(positions) < 2:
            return LineString(positions)
        
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

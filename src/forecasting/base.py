"""Base class for forecast models."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import structlog
from src.utils.logger import logger

logger = structlog.get_logger()


class BaseForecastModel(ABC):
    """Abstract base class for all forecast models."""
    
    def __init__(self, model_name: str):
        """
        Initialize base forecast model.
        
        Args:
            model_name: Name of the model
        """
        self.model_name = model_name
        self.model = None
        self.is_trained = False
    
    @abstractmethod
    def train(self, data: pd.DataFrame, target_col: str = "demand", 
              date_col: str = "date", group_col: str = "sku_id") -> Dict[str, float]:
        """
        Train the model.
        
        Args:
            data: Training data DataFrame
            target_col: Name of target column
            date_col: Name of date column
            group_col: Name of grouping column (e.g., SKU)
            
        Returns:
            Dictionary with training metrics
        """
        pass
    
    @abstractmethod
    def predict(self, horizon: int, data: Optional[pd.DataFrame] = None) -> np.ndarray:
        """
        Generate forecasts.
        
        Args:
            horizon: Number of periods to forecast
            data: Optional data for prediction (if None, uses training data)
            
        Returns:
            Array of forecasted values
        """
        pass
    
    def evaluate(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model performance.
        
        Args:
            actual: Actual values
            predicted: Predicted values
            
        Returns:
            Dictionary with evaluation metrics
        """
        # Remove zeros from actual for MAPE calculation
        mask = actual != 0
        if mask.sum() == 0:
            return {
                "mape": np.inf,
                "mae": np.inf,
                "rmse": np.inf,
                "bias": 0.0,
                "mase": np.inf,
            }
        
        actual_filtered = actual[mask]
        predicted_filtered = predicted[mask]
        
        # MAPE
        mape = np.mean(np.abs((actual_filtered - predicted_filtered) / actual_filtered)) * 100
        
        # MAE
        mae = np.mean(np.abs(actual - predicted))
        
        # RMSE
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        
        # Bias
        bias = np.mean(predicted - actual)
        
        # MASE (Mean Absolute Scaled Error)
        # Using naive forecast as baseline
        if len(actual) > 1:
            naive_forecast = np.abs(np.diff(actual))
            if naive_forecast.sum() > 0:
                mase = mae / np.mean(naive_forecast)
            else:
                mase = np.inf
        else:
            mase = np.inf
        
        return {
            "mape": float(mape),
            "mae": float(mae),
            "rmse": float(rmse),
            "bias": float(bias),
            "mase": float(mase),
        }
    
    def save(self, filepath: str):
        """Save model to file."""
        import pickle
        with open(filepath, "wb") as f:
            pickle.dump(self.model, f)
        logger.info("Model saved", model=self.model_name, path=filepath)
    
    def load(self, filepath: str):
        """Load model from file."""
        import pickle
        with open(filepath, "rb") as f:
            self.model = pickle.load(f)
        self.is_trained = True
        logger.info("Model loaded", model=self.model_name, path=filepath)


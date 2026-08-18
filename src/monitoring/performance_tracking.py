"""Performance tracking and metrics collection."""

from typing import Dict, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import structlog
from src.utils.logger import logger
from src.database.models import Forecast, SalesHistory, ModelRegistry

logger = structlog.get_logger()


class PerformanceTracker:
    """Track model performance metrics."""
    
    def __init__(self, db_session: Session):
        """
        Initialize performance tracker.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def calculate_forecast_accuracy(self, sku_id: str, days_back: int = 90) -> Dict:
        """
        Calculate forecast accuracy for a SKU.
        
        Args:
            sku_id: SKU identifier
            days_back: Number of days to look back
            
        Returns:
            Dictionary with accuracy metrics
        """
        cutoff_date = datetime.now().date() - timedelta(days=days_back)
        
        # Get forecasts and actuals
        forecasts = self.db.query(Forecast).filter(
            Forecast.sku_id == sku_id,
            Forecast.forecast_date >= cutoff_date
        ).all()
        
        if len(forecasts) == 0:
            return {"mape": None, "mae": None, "rmse": None, "count": 0}
        
        errors = []
        actuals = []
        predictions = []
        
        for forecast in forecasts:
            actual = self.db.query(SalesHistory).filter(
                SalesHistory.sku_id == sku_id,
                SalesHistory.date == forecast.forecast_date
            ).first()
            
            if actual:
                error = abs(forecast.predicted_units - actual.units_sold)
                errors.append(error)
                actuals.append(actual.units_sold)
                predictions.append(forecast.predicted_units)
        
        if len(errors) == 0:
            return {"mape": None, "mae": None, "rmse": None, "count": 0}
        
        import numpy as np
        
        # Calculate metrics
        mae = np.mean(errors)
        rmse = np.sqrt(np.mean([e**2 for e in errors]))
        
        # MAPE (only for non-zero actuals)
        non_zero_actuals = [a for a in actuals if a > 0]
        if len(non_zero_actuals) > 0:
            mape_values = [abs(p - a) / a for p, a in zip(predictions, actuals) if a > 0]
            mape = np.mean(mape_values) * 100
        else:
            mape = None
        
        return {
            "mape": float(mape) if mape is not None else None,
            "mae": float(mae),
            "rmse": float(rmse),
            "count": len(errors),
        }
    
    def get_system_metrics(self) -> Dict:
        """
        Get system-wide performance metrics.
        
        Returns:
            Dictionary with system metrics
        """
        from src.database.models import SKUMaster, Inventory
        
        total_skus = self.db.query(SKUMaster).count()
        total_forecasts = self.db.query(Forecast).count()
        
        # Get recent forecasts for accuracy calculation
        recent_forecasts = self.db.query(Forecast).filter(
            Forecast.forecast_date >= datetime.now().date() - timedelta(days=30)
        ).all()
        
        # Calculate average accuracy (simplified)
        accuracy_scores = []
        for forecast in recent_forecasts[:100]:  # Sample for performance
            actual = self.db.query(SalesHistory).filter(
                SalesHistory.sku_id == forecast.sku_id,
                SalesHistory.date == forecast.forecast_date
            ).first()
            
            if actual and actual.units_sold > 0:
                error = abs(forecast.predicted_units - actual.units_sold)
                accuracy = 1 - (error / actual.units_sold)
                accuracy_scores.append(max(0, accuracy))
        
        avg_accuracy = np.mean(accuracy_scores) * 100 if accuracy_scores else None
        
        return {
            "total_skus": total_skus,
            "total_forecasts": total_forecasts,
            "avg_forecast_accuracy": avg_accuracy,
            "timestamp": datetime.utcnow().isoformat(),
        }


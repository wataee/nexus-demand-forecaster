"""Drift detection for model performance monitoring."""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import structlog
from src.utils.logger import logger
from src.database.models import Forecast, SalesHistory

logger = structlog.get_logger()


class DriftDetector:
    """Detect data drift and model performance degradation."""
    
    def __init__(self, db_session: Session):
        """
        Initialize drift detector.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def detect_forecast_drift(self, sku_id: str, threshold: float = 0.3) -> Dict:
        """
        Detect forecast drift by comparing predictions vs actuals.
        
        Args:
            sku_id: SKU identifier
            threshold: MAPE threshold for drift detection
            
        Returns:
            Dictionary with drift detection results
        """
        # Get recent forecasts and actuals
        forecasts = self.db.query(Forecast).filter(
            Forecast.sku_id == sku_id
        ).order_by(Forecast.forecast_date.desc()).limit(6).all()
        
        if len(forecasts) < 3:
            return {"drift_detected": False, "reason": "Insufficient data"}
        
        # Get corresponding actual sales
        drift_scores = []
        for forecast in forecasts:
            actual = self.db.query(SalesHistory).filter(
                SalesHistory.sku_id == sku_id,
                SalesHistory.date == forecast.forecast_date
            ).first()
            
            if actual:
                error = abs(forecast.predicted_units - actual.units_sold)
                if actual.units_sold > 0:
                    mape = (error / actual.units_sold) * 100
                    drift_scores.append(mape)
        
        if len(drift_scores) == 0:
            return {"drift_detected": False, "reason": "No actuals available"}
        
        avg_mape = np.mean(drift_scores)
        drift_detected = avg_mape > (threshold * 100)
        
        return {
            "drift_detected": drift_detected,
            "avg_mape": avg_mape,
            "threshold": threshold * 100,
            "sku_id": sku_id,
        }
    
    def check_all_skus(self, threshold: float = 0.3) -> Dict[str, Dict]:
        """
        Check drift for all SKUs.
        
        Args:
            threshold: MAPE threshold for drift detection
            
        Returns:
            Dictionary mapping SKU ID to drift results
        """
        from src.database.models import SKUMaster
        
        skus = self.db.query(SKUMaster).all()
        results = {}
        
        for sku in skus:
            try:
                drift_result = self.detect_forecast_drift(sku.sku_id, threshold)
                results[sku.sku_id] = drift_result
            except Exception as e:
                logger.error("Drift detection failed", sku_id=sku.sku_id, error=str(e))
                results[sku.sku_id] = {"drift_detected": False, "error": str(e)}
        
        drift_count = sum(1 for r in results.values() if r.get("drift_detected", False))
        logger.info("Drift detection complete", total_skus=len(results), drift_detected=drift_count)
        
        return results


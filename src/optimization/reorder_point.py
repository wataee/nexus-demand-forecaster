"""Reorder Point (ROP) calculation module."""

import numpy as np
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import structlog
from src.utils.logger import logger
from src.database.models import Forecast
from src.optimization.safety_stock import SafetyStockCalculator

logger = structlog.get_logger()


class ReorderPointCalculator:
    """Calculate reorder points for SKUs."""
    
    def __init__(self, db_session: Session):
        """
        Initialize reorder point calculator.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.safety_stock_calc = SafetyStockCalculator(db_session)
    
    def get_forecast_during_lead_time(self, sku_id: str, lead_time_months: float) -> float:
        """
        Get forecasted demand during lead time period.
        
        Args:
            sku_id: SKU identifier
            lead_time_months: Lead time in months
            
        Returns:
            Forecasted demand during lead time
        """
        # Get recent forecasts
        forecasts = self.db.query(Forecast).filter(
            Forecast.sku_id == sku_id
        ).order_by(Forecast.forecast_date.desc()).limit(int(np.ceil(lead_time_months))).all()
        
        if len(forecasts) == 0:
            # Fallback: use historical average
            from src.database.models import SalesHistory
            sales = self.db.query(SalesHistory).filter(
                SalesHistory.sku_id == sku_id
            ).order_by(SalesHistory.date.desc()).limit(12).all()
            
            if len(sales) > 0:
                avg_demand = np.mean([s.units_sold for s in sales])
                return avg_demand * lead_time_months
            return 0.0
        
        # Sum forecasted demand for lead time period
        total_forecast = sum([f.predicted_units for f in forecasts])
        
        # If we have fewer forecasts than lead time, extrapolate
        if len(forecasts) < lead_time_months:
            avg_forecast = total_forecast / len(forecasts) if len(forecasts) > 0 else 0
            remaining_periods = lead_time_months - len(forecasts)
            total_forecast += avg_forecast * remaining_periods
        
        return total_forecast
    
    def calculate(self, sku_id: str) -> float:
        """
        Calculate reorder point for a SKU.
        
        Formula: ROP = forecast_during_lead_time + safety_stock
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Reorder point quantity
        """
        # Get lead time
        lead_time = self.safety_stock_calc.get_lead_time(sku_id)
        
        # Get forecast during lead time
        forecast_demand = self.get_forecast_during_lead_time(sku_id, lead_time)
        
        # Get safety stock
        safety_stock = self.safety_stock_calc.calculate(sku_id)
        
        # Calculate ROP
        rop = forecast_demand + safety_stock
        
        logger.info(
            "Reorder point calculated",
            sku_id=sku_id,
            rop=rop,
            forecast_demand=forecast_demand,
            safety_stock=safety_stock,
            lead_time=lead_time,
        )
        
        return max(0.0, rop)


"""Safety stock calculation module."""

import numpy as np
from typing import Optional
from sqlalchemy.orm import Session
import structlog
from src.utils.logger import logger
from src.database.models import SalesHistory, PurchaseOrder, Segmentation
from src.config import settings

logger = structlog.get_logger()


class SafetyStockCalculator:
    """Calculate safety stock levels for SKUs with ABC-specific service levels."""
    
    def __init__(self, db_session: Session):
        """
        Initialize safety stock calculator.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.config = settings.optimization_config
        
        # ABC-specific service levels and Z-scores
        self.service_levels = self.config.get("service_levels", {
            "a": 0.95,
            "b": 0.90,
            "c": 0.85,
        })
        self.z_scores = self.config.get("z_scores", {
            "a": 1.645,  # 95% service level
            "b": 1.282,  # 90% service level
            "c": 1.036,  # 85% service level
        })
        self.safety_stock_months = self.config.get("safety_stock_months", {
            "a": 2.5,  # 2-3 months for A-items
            "b": 1.5,  # 1-2 months for B-items
            "c": 1.0,  # 1 month for C-items
        })
    
    def get_abc_class(self, sku_id: str) -> str:
        """
        Get ABC classification for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            ABC class ('A', 'B', or 'C')
        """
        seg = self.db.query(Segmentation).filter(Segmentation.sku_id == sku_id).first()
        if seg:
            return seg.abc_class
        return "C"  # Default to C
    
    def get_z_score(self, sku_id: str) -> float:
        """
        Get Z-score based on ABC classification.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Z-score for service level
        """
        abc_class = self.get_abc_class(sku_id).lower()
        return self.z_scores.get(abc_class, self.z_scores["c"])
    
    def calculate_demand_std(self, sku_id: str, periods: int = 12) -> float:
        """
        Calculate standard deviation of demand.
        
        Args:
            sku_id: SKU identifier
            periods: Number of periods to consider
            
        Returns:
            Standard deviation of demand
        """
        # Get recent sales history
        sales = self.db.query(SalesHistory).filter(
            SalesHistory.sku_id == sku_id
        ).order_by(SalesHistory.date.desc()).limit(periods).all()
        
        if len(sales) < 2:
            return 0.0
        
        demand_values = [s.units_sold for s in reversed(sales)]  # Reverse to get chronological order
        return float(np.std(demand_values))
    
    def get_lead_time(self, sku_id: str) -> float:
        """
        Get average lead time for a SKU in periods (months).
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Average lead time in periods
        """
        # Get purchase orders for this SKU
        pos = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.sku_id == sku_id,
            PurchaseOrder.lead_time_days.isnot(None)
        ).all()
        
        if len(pos) == 0:
            return 1.0  # Default to 1 month
        
        # Calculate average lead time in days, then convert to months
        avg_lead_time_days = np.mean([po.lead_time_days for po in pos if po.lead_time_days])
        lead_time_months = avg_lead_time_days / 30.0  # Approximate
        
        return max(0.5, lead_time_months)  # Minimum 0.5 months
    
    def calculate(self, sku_id: str) -> float:
        """
        Calculate safety stock for a SKU using ABC-specific service levels.
        
        Formula: safety_stock = Z * demand_std * sqrt(lead_time_in_periods)
        Alternative: safety_stock = avg_demand * safety_stock_months (for policy-based)
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Safety stock quantity
        """
        abc_class = self.get_abc_class(sku_id).lower()
        z_score = self.get_z_score(sku_id)
        
        demand_std = self.calculate_demand_std(sku_id)
        lead_time = self.get_lead_time(sku_id)
        
        # Method 1: Statistical safety stock
        statistical_safety_stock = z_score * demand_std * np.sqrt(lead_time)
        
        # Method 2: Policy-based safety stock (months of demand)
        # Get average monthly demand
        sales = self.db.query(SalesHistory).filter(
            SalesHistory.sku_id == sku_id
        ).order_by(SalesHistory.date.desc()).limit(12).all()
        
        if len(sales) > 0:
            avg_monthly_demand = np.mean([s.units_sold for s in sales])
            policy_months = self.safety_stock_months.get(abc_class, 1.0)
            policy_safety_stock = avg_monthly_demand * policy_months
        else:
            policy_safety_stock = 0.0
        
        # Use the higher of the two methods (more conservative)
        safety_stock = max(statistical_safety_stock, policy_safety_stock)
        
        logger.info(
            "Safety stock calculated",
            sku_id=sku_id,
            abc_class=abc_class.upper(),
            safety_stock=safety_stock,
            statistical=statistical_safety_stock,
            policy_based=policy_safety_stock,
            demand_std=demand_std,
            lead_time=lead_time,
            z_score=z_score,
        )
        
        return max(0.0, safety_stock)


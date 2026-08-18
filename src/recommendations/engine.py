"""Order recommendation engine."""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import structlog
from src.utils.logger import logger
from src.database.models import (
    OrderRecommendation,
    Forecast,
    Segmentation,
    ModelRegistry,
)
from src.optimization.order_quantity import OrderQuantityOptimizer

logger = structlog.get_logger()


class OrderRecommendationEngine:
    """Generate order recommendations with confidence and explanations."""
    
    def __init__(self, db_session: Session):
        """
        Initialize order recommendation engine.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.optimizer = OrderQuantityOptimizer(db_session)
    
    def calculate_confidence(self, sku_id: str) -> float:
        """
        Calculate confidence level for a recommendation based on forecast accuracy.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Confidence level (0-1)
        """
        # Get model performance metrics
        model_reg = self.db.query(ModelRegistry).filter(
            ModelRegistry.sku_id == sku_id,
            ModelRegistry.is_active == True
        ).first()
        
        if model_reg and model_reg.validation_mape:
            # Convert MAPE to confidence (lower MAPE = higher confidence)
            # MAPE of 0% = 1.0 confidence, MAPE of 50% = 0.5 confidence
            mape = model_reg.validation_mape / 100.0  # Convert to decimal
            confidence = max(0.0, min(1.0, 1.0 - mape))
        else:
            # Default confidence if no model metrics
            confidence = 0.5
        
        return confidence
    
    def generate_explanation(self, sku_id: str, order_metrics: Dict[str, float]) -> str:
        """
        Generate human-readable explanation for recommendation.
        
        Args:
            sku_id: SKU identifier
            order_metrics: Dictionary with order quantity metrics
            
        Returns:
            Explanation string
        """
        explanations = []
        
        # Check lead time
        lead_time = self.optimizer.rop_calculator.safety_stock_calc.get_lead_time(sku_id)
        if lead_time > 3:
            explanations.append(f"Lead time is {lead_time:.1f} months (high)")
        
        # Check inventory level
        current_inv = order_metrics.get("current_inventory", 0)
        rop = order_metrics.get("reorder_point", 0)
        
        if current_inv < rop * 0.5:
            explanations.append("Current inventory is below 50% of reorder point")
        elif current_inv < rop:
            explanations.append("Current inventory is below reorder point")
        
        # Check safety stock
        safety_stock = order_metrics.get("safety_stock", 0)
        if safety_stock > rop * 0.3:
            explanations.append("Safety stock has been increased due to demand variability")
        
        # Check in-transit
        in_transit = order_metrics.get("in_transit", 0)
        if in_transit > 0:
            explanations.append(f"{in_transit:.0f} units are in transit")
        
        if len(explanations) == 0:
            explanations.append("Order recommended to maintain optimal inventory levels")
        
        return ". ".join(explanations) + "."
    
    def get_priority(self, sku_id: str) -> int:
        """
        Get priority ranking based on ABC classification.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Priority integer (1=highest, 3=lowest)
        """
        seg = self.db.query(Segmentation).filter(Segmentation.sku_id == sku_id).first()
        
        if seg:
            abc_class = seg.abc_class
            if abc_class == "A":
                return 1
            elif abc_class == "B":
                return 2
            else:
                return 3
        
        return 3  # Default to lowest priority
    
    def generate_recommendation(self, sku_id: str) -> Dict:
        """
        Generate order recommendation for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Dictionary with recommendation details
        """
        # Calculate order quantity
        order_metrics = self.optimizer.calculate_order_quantity(sku_id)
        order_qty = order_metrics["order_quantity"]
        
        # Skip if no order needed
        if order_qty <= 0:
            return None
        
        # Calculate confidence
        confidence = self.calculate_confidence(sku_id)
        
        # Generate explanation
        explanation = self.generate_explanation(sku_id, order_metrics)
        
        # Get priority
        priority = self.get_priority(sku_id)
        
        recommendation = {
            "sku_id": sku_id,
            "recommended_qty": order_qty,
            "confidence_level": confidence,
            "explanation": explanation,
            "priority": priority,
            "reorder_point": order_metrics["reorder_point"],
            "safety_stock": order_metrics["safety_stock"],
            "current_inventory": order_metrics["current_inventory"],
            "in_transit": order_metrics["in_transit"],
        }
        
        return recommendation
    
    def store_recommendation(self, recommendation: Dict) -> OrderRecommendation:
        """
        Store recommendation in database.
        
        Args:
            recommendation: Recommendation dictionary
            
        Returns:
            OrderRecommendation database object
        """
        # Check if recommendation exists
        existing = self.db.query(OrderRecommendation).filter(
            OrderRecommendation.sku_id == recommendation["sku_id"],
            OrderRecommendation.status == "PENDING"
        ).first()
        
        if existing:
            # Update existing
            existing.recommended_qty = recommendation["recommended_qty"]
            existing.confidence_level = recommendation["confidence_level"]
            existing.explanation = recommendation["explanation"]
            existing.priority = recommendation["priority"]
            existing.reorder_point = recommendation["reorder_point"]
            existing.safety_stock = recommendation["safety_stock"]
            existing.current_inventory = recommendation["current_inventory"]
            existing.in_transit_qty = recommendation["in_transit"]
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing
        else:
            # Create new
            rec = OrderRecommendation(
                sku_id=recommendation["sku_id"],
                recommended_qty=recommendation["recommended_qty"],
                confidence_level=recommendation["confidence_level"],
                explanation=recommendation["explanation"],
                priority=recommendation["priority"],
                reorder_point=recommendation["reorder_point"],
                safety_stock=recommendation["safety_stock"],
                current_inventory=recommendation["current_inventory"],
                in_transit_qty=recommendation["in_transit"],
                status="PENDING",
            )
            self.db.add(rec)
            self.db.commit()
            return rec
    
    def generate_all_recommendations(self, sku_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Generate recommendations for all SKUs or specified SKUs.
        
        Args:
            sku_ids: Optional list of SKU IDs (if None, processes all)
            
        Returns:
            List of recommendation dictionaries
        """
        logger.info("Generating order recommendations", sku_count=len(sku_ids) if sku_ids else "all")
        
        if sku_ids is None:
            # Get all SKUs with forecasts
            forecasts = self.db.query(Forecast).distinct(Forecast.sku_id).all()
            sku_ids = [f.sku_id for f in forecasts]
        
        recommendations = []
        for sku_id in sku_ids:
            try:
                rec = self.generate_recommendation(sku_id)
                if rec:
                    self.store_recommendation(rec)
                    recommendations.append(rec)
            except Exception as e:
                logger.error("Recommendation generation failed", sku_id=sku_id, error=str(e))
        
        # Sort by priority and confidence
        recommendations.sort(key=lambda x: (x["priority"], -x["confidence_level"]))
        
        logger.info("Recommendations generated", count=len(recommendations))
        
        return recommendations


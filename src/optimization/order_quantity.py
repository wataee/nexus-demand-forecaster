"""Order quantity optimization module."""

import numpy as np
from typing import Optional, Dict
from sqlalchemy.orm import Session
import structlog
from src.utils.logger import logger
from src.database.models import Inventory, PurchaseOrder
from src.optimization.reorder_point import ReorderPointCalculator
from src.config import settings

logger = structlog.get_logger()


class OrderQuantityOptimizer:
    """Optimize order quantities based on inventory levels and ROP."""
    
    def __init__(self, db_session: Session):
        """
        Initialize order quantity optimizer.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.rop_calculator = ReorderPointCalculator(db_session)
        self.config = settings.optimization_config
        
        self.min_order_quantity = self.config.get("min_order_quantity", 1)
    
    def get_current_inventory(self, sku_id: str) -> float:
        """
        Get current on-hand inventory for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Current inventory level
        """
        inventory = self.db.query(Inventory).filter(
            Inventory.sku_id == sku_id
        ).first()
        
        if inventory:
            return float(inventory.stock_level)
        return 0.0
    
    def get_in_transit_quantity(self, sku_id: str) -> float:
        """
        Get in-transit inventory quantity for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            In-transit quantity
        """
        # Get pending and in-transit purchase orders
        pos = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.sku_id == sku_id,
            PurchaseOrder.status.in_(["PENDING", "IN_TRANSIT"])
        ).all()
        
        total_in_transit = sum([po.quantity_ordered for po in pos])
        return float(total_in_transit)
    
    def calculate_order_quantity(self, sku_id: str) -> Dict[str, float]:
        """
        Calculate recommended order quantity for a SKU.
        
        Formula: order_qty = max(0, ROP - current_inventory - in_transit)
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Dictionary with order quantity and related metrics
        """
        # Get ROP
        rop = self.rop_calculator.calculate(sku_id)
        
        # Get current inventory
        current_inventory = self.get_current_inventory(sku_id)
        
        # Get in-transit quantity
        in_transit = self.get_in_transit_quantity(sku_id)
        
        # Calculate order quantity
        order_qty = max(0.0, rop - current_inventory - in_transit)
        
        # Apply minimum order quantity
        if order_qty > 0 and order_qty < self.min_order_quantity:
            order_qty = self.min_order_quantity
        
        # Get safety stock for reference
        safety_stock = self.rop_calculator.safety_stock_calc.calculate(sku_id)
        
        result = {
            "order_quantity": order_qty,
            "reorder_point": rop,
            "current_inventory": current_inventory,
            "in_transit": in_transit,
            "safety_stock": safety_stock,
        }
        
        logger.info(
            "Order quantity calculated",
            sku_id=sku_id,
            order_qty=order_qty,
            rop=rop,
            current_inv=current_inventory,
            in_transit=in_transit,
        )
        
        return result
    
    def optimize_all(self, sku_ids: Optional[list] = None) -> Dict[str, Dict[str, float]]:
        """
        Calculate order quantities for multiple SKUs.
        
        Args:
            sku_ids: Optional list of SKU IDs (if None, processes all)
            
        Returns:
            Dictionary mapping SKU ID to order quantity metrics
        """
        if sku_ids is None:
            # Get all SKUs with inventory
            inventories = self.db.query(Inventory).all()
            sku_ids = [inv.sku_id for inv in inventories]
        
        results = {}
        for sku_id in sku_ids:
            try:
                results[sku_id] = self.calculate_order_quantity(sku_id)
            except Exception as e:
                logger.error("Order quantity calculation failed", sku_id=sku_id, error=str(e))
                results[sku_id] = {
                    "order_quantity": 0.0,
                    "reorder_point": 0.0,
                    "current_inventory": 0.0,
                    "in_transit": 0.0,
                    "safety_stock": 0.0,
                }
        
        return results


"""ERP integration endpoints for TOTVS, SAP, or custom ERP systems."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import structlog
from src.database.connection import get_db
from src.database.models import OrderRecommendation, PurchaseOrder
from src.api.schemas import OrderRecommendationResponse
from src.utils.logger import logger

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/erp", tags=["ERP Integration"])


@router.post("/export-recommendations", response_model=List[OrderRecommendationResponse])
async def export_recommendations_to_erp(
    format: str = "json",  # json, csv, xml
    status: str = "PENDING",
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    """
    Export order recommendations for ERP import.
    
    Supports multiple formats for TOTVS, SAP, or custom ERP integration.
    Initially read-only extraction, later supports write-back.
    
    Args:
        format: Export format (json, csv, xml)
        status: Filter by recommendation status
        limit: Maximum number of recommendations to export
        db: Database session
        
    Returns:
        List of recommendations in requested format
    """
    recommendations = db.query(OrderRecommendation).filter(
        OrderRecommendation.status == status
    ).limit(limit).all()
    
    if format == "csv":
        # Return CSV format
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "sku_id", "recommended_qty", "confidence_level", "priority",
            "reorder_point", "safety_stock", "current_inventory"
        ])
        writer.writeheader()
        
        for rec in recommendations:
            writer.writerow({
                "sku_id": rec.sku_id,
                "recommended_qty": rec.recommended_qty,
                "confidence_level": rec.confidence_level,
                "priority": rec.priority,
                "reorder_point": rec.reorder_point,
                "safety_stock": rec.safety_stock,
                "current_inventory": rec.current_inventory,
            })
        
        return {"format": "csv", "data": output.getvalue()}
    
    elif format == "xml":
        # Return XML format (simplified)
        xml_data = "<recommendations>\n"
        for rec in recommendations:
            xml_data += f'  <recommendation sku_id="{rec.sku_id}" qty="{rec.recommended_qty}"/>\n'
        xml_data += "</recommendations>"
        return {"format": "xml", "data": xml_data}
    
    else:  # json (default)
        return recommendations


@router.post("/import-purchase-orders")
async def import_purchase_orders_from_erp(
    orders: List[dict],
    db: Session = Depends(get_db),
):
    """
    Import purchase orders from ERP system.
    
    This endpoint allows ERP systems to push PO data back to the system.
    Supports TOTVS, SAP, or custom ERP formats.
    
    Args:
        orders: List of purchase order dictionaries
        db: Database session
        
    Returns:
        Import results
    """
    imported_count = 0
    errors = []
    
    for order_data in orders:
        try:
            po = PurchaseOrder(
                sku_id=order_data["sku_id"],
                supplier_id=order_data.get("supplier_id"),
                order_date=date.fromisoformat(order_data["order_date"]) if isinstance(order_data["order_date"], str) else order_data["order_date"],
                quantity_ordered=float(order_data["quantity_ordered"]),
                status=order_data.get("status", "PENDING"),
            )
            db.add(po)
            imported_count += 1
        except Exception as e:
            errors.append({"order": order_data, "error": str(e)})
    
    db.commit()
    
    logger.info("PO import complete", imported=imported_count, errors=len(errors))
    
    return {
        "imported": imported_count,
        "errors": errors,
    }


@router.get("/inventory-snapshot")
async def get_inventory_snapshot_for_erp(
    warehouse: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get inventory snapshot for ERP synchronization.
    
    Provides read-only inventory data for ERP systems.
    
    Args:
        warehouse: Optional warehouse filter
        db: Database session
        
    Returns:
        Inventory snapshot data
    """
    from src.database.models import Inventory
    
    query = db.query(Inventory)
    if warehouse:
        query = query.filter(Inventory.warehouse == warehouse)
    
    inventory = query.all()
    
    return {
        "snapshot_date": date.today().isoformat(),
        "warehouse": warehouse,
        "records": [
            {
                "sku_id": inv.sku_id,
                "stock_level": inv.stock_level,
                "warehouse": inv.warehouse,
                "safety_stock": inv.safety_stock,
            }
            for inv in inventory
        ],
    }


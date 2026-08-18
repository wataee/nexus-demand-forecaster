"""Data storage module for loading data into PostgreSQL."""

import pandas as pd
from typing import Dict, Optional
from sqlalchemy.orm import Session
import structlog
from src.utils.logger import logger
from src.database.models import (
    SKUMaster,
    SalesHistory,
    Inventory,
    PurchaseOrder,
    Supplier,
    CustomerType,
    LifecycleStatus,
)

logger = structlog.get_logger()


class DataStorage:
    """Handle data storage to PostgreSQL database."""
    
    def __init__(self, db_session: Session):
        """
        Initialize data storage.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def store_sku_master(self, df: pd.DataFrame, replace: bool = False) -> int:
        """
        Store SKU master data.
        
        Args:
            df: DataFrame with SKU master data
            replace: If True, replace existing data
            
        Returns:
            Number of records stored
        """
        logger.info("Storing SKU master data", rows=len(df))
        
        if replace:
            self.db.query(SKUMaster).delete()
        
        stored_count = 0
        for _, row in df.iterrows():
            sku = SKUMaster(
                sku_id=row["sku_id"],
                category=row.get("category"),
                family=row.get("family"),
                unit_cost=float(row["unit_cost"]),
                lifecycle_status=LifecycleStatus(row.get("lifecycle_status", "ACTIVE")),
                criticality=row.get("criticality"),
                description=row.get("description"),
            )
            
            # Check if SKU already exists
            existing = self.db.query(SKUMaster).filter(SKUMaster.sku_id == sku.sku_id).first()
            if existing:
                if replace:
                    self.db.delete(existing)
                    self.db.add(sku)
                    stored_count += 1
            else:
                self.db.add(sku)
                stored_count += 1
        
        self.db.commit()
        logger.info("SKU master data stored", count=stored_count)
        
        return stored_count
    
    def store_sales_history(self, df: pd.DataFrame, replace: bool = False) -> int:
        """
        Store sales history data.
        
        Args:
            df: DataFrame with sales history data
            replace: If True, replace existing data
            
        Returns:
            Number of records stored
        """
        logger.info("Storing sales history data", rows=len(df))
        
        if replace:
            self.db.query(SalesHistory).delete()
        
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        
        stored_count = 0
        batch_size = 1000
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            records = []
            
            for _, row in batch.iterrows():
                record = SalesHistory(
                    sku_id=row["sku_id"],
                    date=row["date"].date(),
                    units_sold=float(row.get("units_sold", row.get("demand", 0))),
                    price=float(row["price"]) if "price" in row and pd.notna(row["price"]) else None,
                    customer_type=CustomerType(row["customer_type"]) if "customer_type" in row and pd.notna(row["customer_type"]) else None,
                )
                records.append(record)
            
            self.db.bulk_save_objects(records)
            stored_count += len(records)
            
            if (i // batch_size + 1) % 10 == 0:
                self.db.commit()
                logger.info("Sales history batch committed", batch=i // batch_size + 1)
        
        self.db.commit()
        logger.info("Sales history data stored", count=stored_count)
        
        return stored_count
    
    def store_inventory(self, df: pd.DataFrame, replace: bool = False) -> int:
        """
        Store inventory data.
        
        Args:
            df: DataFrame with inventory data
            replace: If True, replace existing data
            
        Returns:
            Number of records stored
        """
        logger.info("Storing inventory data", rows=len(df))
        
        if replace:
            self.db.query(Inventory).delete()
        
        stored_count = 0
        for _, row in df.iterrows():
            inventory = Inventory(
                sku_id=row["sku_id"],
                stock_level=float(row["stock_level"]),
                warehouse=row.get("warehouse"),
                safety_stock=float(row["safety_stock"]) if "safety_stock" in row and pd.notna(row["safety_stock"]) else None,
            )
            
            # Check if inventory record exists
            existing = self.db.query(Inventory).filter(
                Inventory.sku_id == inventory.sku_id,
                Inventory.warehouse == inventory.warehouse
            ).first()
            
            if existing:
                if replace:
                    existing.stock_level = inventory.stock_level
                    existing.safety_stock = inventory.safety_stock
                    stored_count += 1
            else:
                self.db.add(inventory)
                stored_count += 1
        
        self.db.commit()
        logger.info("Inventory data stored", count=stored_count)
        
        return stored_count
    
    def store_purchase_orders(self, df: pd.DataFrame, replace: bool = False) -> int:
        """
        Store purchase orders data.
        
        Args:
            df: DataFrame with purchase orders data
            replace: If True, replace existing data
            
        Returns:
            Number of records stored
        """
        logger.info("Storing purchase orders data", rows=len(df))
        
        if replace:
            self.db.query(PurchaseOrder).delete()
        
        df = df.copy()
        if "order_date" in df.columns:
            df["order_date"] = pd.to_datetime(df["order_date"])
        if "expected_arrival_date" in df.columns:
            df["expected_arrival_date"] = pd.to_datetime(df["expected_arrival_date"])
        
        stored_count = 0
        for _, row in df.iterrows():
            po = PurchaseOrder(
                sku_id=row["sku_id"],
                supplier_id=row.get("supplier_id") if "supplier_id" in row and pd.notna(row.get("supplier_id")) else None,
                order_date=row["order_date"].date(),
                expected_arrival_date=row["expected_arrival_date"].date() if "expected_arrival_date" in row and pd.notna(row["expected_arrival_date"]) else None,
                lead_time_days=int(row["lead_time_days"]) if "lead_time_days" in row and pd.notna(row["lead_time_days"]) else None,
                quantity_ordered=float(row["quantity_ordered"]),
                supplier=row.get("supplier"),  # Legacy field
                status=row.get("status", "PENDING"),
            )
            self.db.add(po)
            stored_count += 1
        
        self.db.commit()
        logger.info("Purchase orders data stored", count=stored_count)
        
        return stored_count
    
    def store_suppliers(self, df: pd.DataFrame, replace: bool = False) -> int:
        """
        Store supplier master data.
        
        Args:
            df: DataFrame with supplier data
            replace: If True, replace existing data
            
        Returns:
            Number of records stored
        """
        logger.info("Storing supplier data", rows=len(df))
        
        if replace:
            self.db.query(Supplier).delete()
        
        stored_count = 0
        for _, row in df.iterrows():
            supplier = Supplier(
                supplier_id=row["supplier_id"],
                supplier_name=row["supplier_name"],
                country=row["country"],
                supplier_type=row.get("supplier_type", "STANDARD"),
                base_lead_time_days=int(row["base_lead_time_days"]),
                lead_time_std_days=int(row.get("lead_time_std_days", 0)) if pd.notna(row.get("lead_time_std_days")) else None,
                on_time_percentage=float(row["on_time_percentage"]) if pd.notna(row.get("on_time_percentage")) else None,
                min_order_quantity=float(row["min_order_quantity"]) if pd.notna(row.get("min_order_quantity")) else None,
                is_strategic=bool(row.get("is_strategic", False)),
            )
            
            existing = self.db.query(Supplier).filter(Supplier.supplier_id == supplier.supplier_id).first()
            if existing:
                if replace:
                    self.db.delete(existing)
                    self.db.add(supplier)
                    stored_count += 1
            else:
                self.db.add(supplier)
                stored_count += 1
        
        self.db.commit()
        logger.info("Supplier data stored", count=stored_count)
        
        return stored_count
    
    def store_all(self, data: Dict[str, pd.DataFrame], replace: bool = False) -> Dict[str, int]:
        """
        Store all data types.
        
        Args:
            data: Dictionary mapping data type to DataFrame
            replace: If True, replace existing data
            
        Returns:
            Dictionary mapping data type to number of records stored
        """
        results = {}
        
        if "sku_master" in data:
            results["sku_master"] = self.store_sku_master(data["sku_master"], replace=replace)
        
        if "suppliers" in data:
            results["suppliers"] = self.store_suppliers(data["suppliers"], replace=replace)
        
        if "sales_history" in data:
            results["sales_history"] = self.store_sales_history(data["sales_history"], replace=replace)
        
        if "inventory" in data:
            results["inventory"] = self.store_inventory(data["inventory"], replace=replace)
        
        if "purchase_orders" in data:
            results["purchase_orders"] = self.store_purchase_orders(data["purchase_orders"], replace=replace)
        
        return results


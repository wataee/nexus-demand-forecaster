"""ABC/XYZ segmentation implementation."""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
import structlog
from src.utils.logger import logger
from src.database.models import (
    SKUMaster,
    SalesHistory,
    Segmentation,
    SegmentationGroup,
)
from src.config import settings

logger = structlog.get_logger()


class ABCXYZSegmentation:
    """ABC/XYZ segmentation service."""
    
    def __init__(self, db_session: Session):
        """
        Initialize segmentation service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.config = settings.segmentation_config
        
        # ABC percentiles
        self.abc_percentiles = self.config.get("abc_percentiles", {
            "a": 0.20,
            "b": 0.30,
            "c": 0.50,
        })
        
        # XYZ CV thresholds
        self.xyz_thresholds = self.config.get("xyz_cv_thresholds", {
            "x": 0.5,
            "y": 1.0,
            "z": None,  # > 1.0
        })
    
    def calculate_annual_revenue(self, sku_id: str) -> float:
        """
        Calculate annual revenue for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Annual revenue value
        """
        # Get sales history for the SKU
        sales = self.db.query(SalesHistory).filter(SalesHistory.sku_id == sku_id).all()
        
        if not sales:
            return 0.0
        
        # Calculate revenue (units * price) for last 12 months
        # For simplicity, we'll use all available data and annualize
        total_revenue = 0.0
        
        for sale in sales:
            if sale.price:
                revenue = sale.units_sold * sale.price
            else:
                # If no price, use unit cost from SKU master
                sku = self.db.query(SKUMaster).filter(SKUMaster.sku_id == sku_id).first()
                if sku:
                    revenue = sale.units_sold * sku.unit_cost
                else:
                    revenue = 0.0
            
            total_revenue += revenue
        
        # Annualize based on date range
        if len(sales) > 0:
            dates = [sale.date for sale in sales]
            date_range_days = (max(dates) - min(dates)).days
            if date_range_days > 0:
                annualization_factor = 365.0 / date_range_days
                total_revenue = total_revenue * annualization_factor
        
        return total_revenue
    
    def calculate_coefficient_of_variation(self, sku_id: str) -> float:
        """
        Calculate coefficient of variation (CV) for demand variability.
        
        CV = std_dev / mean
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Coefficient of variation
        """
        # Get sales history
        sales = self.db.query(SalesHistory).filter(SalesHistory.sku_id == sku_id).all()
        
        if not sales or len(sales) < 2:
            return 1.0  # High variability if insufficient data
        
        units = [sale.units_sold for sale in sales]
        mean_demand = np.mean(units)
        
        if mean_demand == 0:
            return 1.0
        
        std_demand = np.std(units)
        cv = std_demand / mean_demand
        
        return cv
    
    def classify_abc(self, annual_revenue: float, revenue_percentiles: Dict[str, float]) -> str:
        """
        Classify SKU into A, B, or C based on annual revenue.
        
        Args:
            annual_revenue: Annual revenue value
            revenue_percentiles: Dictionary with percentile thresholds
            
        Returns:
            ABC classification ('A', 'B', or 'C')
        """
        # This will be called after calculating percentiles for all SKUs
        # For now, return placeholder - actual classification happens in segment_all
        return "C"
    
    def classify_xyz(self, cv: float) -> str:
        """
        Classify SKU into X, Y, or Z based on coefficient of variation.
        
        Args:
            cv: Coefficient of variation
            
        Returns:
            XYZ classification ('X', 'Y', or 'Z')
        """
        if cv < self.xyz_thresholds["x"]:
            return "X"
        elif cv < self.xyz_thresholds.get("y", 1.0):
            return "Y"
        else:
            return "Z"
    
    def get_segment_group(self, abc_class: str, xyz_class: str) -> SegmentationGroup:
        """
        Get segmentation group from ABC and XYZ classes.
        
        Args:
            abc_class: ABC classification ('A', 'B', or 'C')
            xyz_class: XYZ classification ('X', 'Y', or 'Z')
            
        Returns:
            SegmentationGroup enum value
        """
        segment_str = f"{abc_class}{xyz_class}"
        return SegmentationGroup(segment_str)
    
    def segment_sku(self, sku_id: str) -> Dict[str, any]:
        """
        Segment a single SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            Dictionary with segmentation results
        """
        annual_revenue = self.calculate_annual_revenue(sku_id)
        cv = self.calculate_coefficient_of_variation(sku_id)
        
        xyz_class = self.classify_xyz(cv)
        
        return {
            "sku_id": sku_id,
            "annual_revenue": annual_revenue,
            "coefficient_of_variation": cv,
            "xyz_class": xyz_class,
        }
    
    def segment_all(self) -> pd.DataFrame:
        """
        Segment all SKUs and return results as DataFrame.
        
        Returns:
            DataFrame with segmentation results
        """
        logger.info("Starting ABC/XYZ segmentation for all SKUs")
        
        # Get all SKUs
        skus = self.db.query(SKUMaster).all()
        logger.info("Found SKUs", count=len(skus))
        
        # Calculate metrics for all SKUs
        segmentation_data = []
        for sku in skus:
            result = self.segment_sku(sku.sku_id)
            segmentation_data.append(result)
        
        df = pd.DataFrame(segmentation_data)
        
        # Classify ABC based on revenue percentiles
        if len(df) > 0:
            # Calculate percentiles
            revenue_sorted = df["annual_revenue"].sort_values(ascending=False)
            total_skus = len(revenue_sorted)
            
            a_threshold_idx = int(total_skus * self.abc_percentiles["a"])
            b_threshold_idx = int(total_skus * (self.abc_percentiles["a"] + self.abc_percentiles["b"]))
            
            if a_threshold_idx > 0:
                a_threshold = revenue_sorted.iloc[a_threshold_idx - 1]
            else:
                a_threshold = revenue_sorted.iloc[0] if len(revenue_sorted) > 0 else 0
            
            if b_threshold_idx > 0:
                b_threshold = revenue_sorted.iloc[b_threshold_idx - 1]
            else:
                b_threshold = revenue_sorted.iloc[0] if len(revenue_sorted) > 0 else 0
            
            # Classify ABC
            def classify_abc(revenue):
                if revenue >= a_threshold:
                    return "A"
                elif revenue >= b_threshold:
                    return "B"
                else:
                    return "C"
            
            df["abc_class"] = df["annual_revenue"].apply(classify_abc)
            
            # Get segment group
            df["segment_group"] = df.apply(
                lambda row: self.get_segment_group(row["abc_class"], row["xyz_class"]).value,
                axis=1
            )
        
        logger.info("Segmentation complete", total_skus=len(df))
        logger.info("Segmentation distribution", distribution=df["segment_group"].value_counts().to_dict())
        
        return df
    
    def store_segmentation(self, segmentation_df: pd.DataFrame, replace: bool = False) -> int:
        """
        Store segmentation results in database.
        
        Args:
            segmentation_df: DataFrame with segmentation results
            replace: If True, replace existing segmentation
            
        Returns:
            Number of records stored
        """
        logger.info("Storing segmentation results", rows=len(segmentation_df))
        
        if replace:
            self.db.query(Segmentation).delete()
        
        stored_count = 0
        for _, row in segmentation_df.iterrows():
            # Check if segmentation exists
            existing = self.db.query(Segmentation).filter(
                Segmentation.sku_id == row["sku_id"]
            ).first()
            
            if existing:
                if replace:
                    existing.abc_class = row["abc_class"]
                    existing.xyz_class = row["xyz_class"]
                    existing.segment_group = SegmentationGroup(row["segment_group"])
                    existing.annual_revenue = row["annual_revenue"]
                    existing.coefficient_of_variation = row["coefficient_of_variation"]
                    stored_count += 1
            else:
                segmentation = Segmentation(
                    sku_id=row["sku_id"],
                    abc_class=row["abc_class"],
                    xyz_class=row["xyz_class"],
                    segment_group=SegmentationGroup(row["segment_group"]),
                    annual_revenue=row["annual_revenue"],
                    coefficient_of_variation=row["coefficient_of_variation"],
                )
                self.db.add(segmentation)
                stored_count += 1
        
        self.db.commit()
        logger.info("Segmentation results stored", count=stored_count)
        
        return stored_count
    
    def run_segmentation(self, replace: bool = False) -> pd.DataFrame:
        """
        Run complete segmentation process and store results.
        
        Args:
            replace: If True, replace existing segmentation
            
        Returns:
            DataFrame with segmentation results
        """
        segmentation_df = self.segment_all()
        self.store_segmentation(segmentation_df, replace=replace)
        
        return segmentation_df


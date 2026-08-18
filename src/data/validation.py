"""Data validation and quality checks."""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import structlog
from src.utils.logger import logger

logger = structlog.get_logger()


class DataValidator:
    """Perform data quality checks and validation."""
    
    def __init__(self):
        """Initialize data validator."""
        self.validation_results = {}
    
    def validate_schema(self, df: pd.DataFrame, required_columns: List[str], data_type: str) -> Tuple[bool, List[str]]:
        """
        Validate that DataFrame has required columns.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            data_type: Type of data being validated (for logging)
            
        Returns:
            Tuple of (is_valid, missing_columns)
        """
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(
                "Schema validation failed",
                data_type=data_type,
                missing_columns=missing_columns
            )
            return False, missing_columns
        
        logger.info("Schema validation passed", data_type=data_type)
        return True, []
    
    def check_missing_values(self, df: pd.DataFrame, data_type: str) -> Dict[str, int]:
        """
        Check for missing values in DataFrame.
        
        Args:
            df: DataFrame to check
            data_type: Type of data being validated
            
        Returns:
            Dictionary mapping column names to missing value counts
        """
        missing_counts = df.isnull().sum().to_dict()
        missing_counts = {k: int(v) for k, v in missing_counts.items() if v > 0}
        
        if missing_counts:
            logger.warning(
                "Missing values detected",
                data_type=data_type,
                missing_counts=missing_counts
            )
        else:
            logger.info("No missing values detected", data_type=data_type)
        
        return missing_counts
    
    def detect_outliers(self, df: pd.DataFrame, column: str, threshold: float = 10.0, data_type: str = "") -> pd.DataFrame:
        """
        Detect outliers using IQR method or threshold multiplier.
        
        Args:
            df: DataFrame to check
            column: Column name to check for outliers
            threshold: Multiplier threshold (e.g., 10x average)
            data_type: Type of data being validated
            
        Returns:
            DataFrame with outlier rows
        """
        if column not in df.columns:
            return pd.DataFrame()
        
        values = df[column].dropna()
        if len(values) == 0:
            return pd.DataFrame()
        
        mean_val = values.mean()
        std_val = values.std()
        
        if std_val == 0:
            return pd.DataFrame()
        
        # Outliers are values > threshold * mean
        outlier_mask = df[column] > (threshold * mean_val)
        outliers = df[outlier_mask]
        
        if len(outliers) > 0:
            logger.warning(
                "Outliers detected",
                data_type=data_type,
                column=column,
                count=len(outliers),
                threshold=threshold
            )
        
        return outliers
    
    def check_duplicates(self, df: pd.DataFrame, subset: Optional[List[str]] = None, data_type: str = "") -> int:
        """
        Check for duplicate rows.
        
        Args:
            df: DataFrame to check
            subset: Columns to check for duplicates (defaults to all columns)
            data_type: Type of data being validated
            
        Returns:
            Number of duplicate rows
        """
        duplicates = df.duplicated(subset=subset)
        duplicate_count = duplicates.sum()
        
        if duplicate_count > 0:
            logger.warning(
                "Duplicates detected",
                data_type=data_type,
                count=duplicate_count
            )
        else:
            logger.info("No duplicates detected", data_type=data_type)
        
        return int(duplicate_count)
    
    def validate_sales_history(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Validate sales history data.
        
        Args:
            df: Sales history DataFrame
            
        Returns:
            Validation results dictionary
        """
        results = {
            "valid": True,
            "issues": []
        }
        
        # Schema validation
        required_cols = ["sku_id", "date", "units_sold"]
        is_valid, missing = self.validate_schema(df, required_cols, "sales_history")
        if not is_valid:
            results["valid"] = False
            results["issues"].append(f"Missing columns: {missing}")
        
        # Check for negative sales (should be handled as returns/promos)
        if "units_sold" in df.columns:
            negative_sales = (df["units_sold"] < 0).sum()
            if negative_sales > 0:
                results["issues"].append(f"Negative sales detected: {negative_sales} records")
                logger.info("Negative sales found (returns/promos)", count=int(negative_sales))
        
        # Outlier detection
        if "units_sold" in df.columns:
            outliers = self.detect_outliers(df, "units_sold", threshold=10.0, data_type="sales_history")
            if len(outliers) > 0:
                results["issues"].append(f"Outliers detected: {len(outliers)} records")
        
        # Missing values
        missing_vals = self.check_missing_values(df, "sales_history")
        if missing_vals:
            results["issues"].append(f"Missing values: {missing_vals}")
        
        # Duplicates
        duplicate_count = self.check_duplicates(df, subset=["sku_id", "date"], data_type="sales_history")
        if duplicate_count > 0:
            results["issues"].append(f"Duplicates: {duplicate_count} records")
        
        return results
    
    def validate_inventory(self, df: pd.DataFrame) -> Dict[str, any]:
        """Validate inventory data."""
        results = {
            "valid": True,
            "issues": []
        }
        
        required_cols = ["sku_id", "stock_level"]
        is_valid, missing = self.validate_schema(df, required_cols, "inventory")
        if not is_valid:
            results["valid"] = False
            results["issues"].append(f"Missing columns: {missing}")
        
        # Check for negative inventory
        if "stock_level" in df.columns:
            negative_inv = (df["stock_level"] < 0).sum()
            if negative_inv > 0:
                results["issues"].append(f"Negative inventory: {negative_inv} records")
        
        missing_vals = self.check_missing_values(df, "inventory")
        if missing_vals:
            results["issues"].append(f"Missing values: {missing_vals}")
        
        return results
    
    def validate_purchase_orders(self, df: pd.DataFrame) -> Dict[str, any]:
        """Validate purchase orders data."""
        results = {
            "valid": True,
            "issues": []
        }
        
        required_cols = ["sku_id", "order_date", "quantity_ordered"]
        is_valid, missing = self.validate_schema(df, required_cols, "purchase_orders")
        if not is_valid:
            results["valid"] = False
            results["issues"].append(f"Missing columns: {missing}")
        
        # Check lead time anomalies
        if "lead_time_days" in df.columns:
            # Lead times should be reasonable (1-365 days)
            anomalous_lt = ((df["lead_time_days"] < 1) | (df["lead_time_days"] > 365)).sum()
            if anomalous_lt > 0:
                results["issues"].append(f"Anomalous lead times: {anomalous_lt} records")
        
        missing_vals = self.check_missing_values(df, "purchase_orders")
        if missing_vals:
            results["issues"].append(f"Missing values: {missing_vals}")
        
        return results
    
    def validate_sku_master(self, df: pd.DataFrame) -> Dict[str, any]:
        """Validate SKU master data."""
        results = {
            "valid": True,
            "issues": []
        }
        
        required_cols = ["sku_id", "unit_cost"]
        is_valid, missing = self.validate_schema(df, required_cols, "sku_master")
        if not is_valid:
            results["valid"] = False
            results["issues"].append(f"Missing columns: {missing}")
        
        # Check for duplicate SKUs
        duplicate_count = self.check_duplicates(df, subset=["sku_id"], data_type="sku_master")
        if duplicate_count > 0:
            results["valid"] = False
            results["issues"].append(f"Duplicate SKUs: {duplicate_count} records")
        
        missing_vals = self.check_missing_values(df, "sku_master")
        if missing_vals:
            results["issues"].append(f"Missing values: {missing_vals}")
        
        return results
    
    def validate_all(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, any]]:
        """
        Validate all data types.
        
        Args:
            data: Dictionary mapping data type to DataFrame
            
        Returns:
            Dictionary mapping data type to validation results
        """
        validation_results = {}
        
        if "sales_history" in data:
            validation_results["sales_history"] = self.validate_sales_history(data["sales_history"])
        
        if "inventory" in data:
            validation_results["inventory"] = self.validate_inventory(data["inventory"])
        
        if "purchase_orders" in data:
            validation_results["purchase_orders"] = self.validate_purchase_orders(data["purchase_orders"])
        
        if "sku_master" in data:
            validation_results["sku_master"] = self.validate_sku_master(data["sku_master"])
        
        return validation_results


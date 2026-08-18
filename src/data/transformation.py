"""Data transformation and feature engineering."""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import structlog
from src.utils.logger import logger
from src.config import settings

logger = structlog.get_logger()


class DataTransformer:
    """Transform and engineer features from raw data."""
    
    def __init__(self, frequency: str = "monthly"):
        """
        Initialize data transformer.
        
        Args:
            frequency: Time series frequency ('monthly' or 'weekly')
        """
        self.frequency = frequency
        self.freq_map = {
            "monthly": "M",
            "weekly": "W",
        }
    
    def align_time_series(self, df: pd.DataFrame, date_col: str = "date", 
                         value_col: str = "units_sold", group_col: str = "sku_id") -> pd.DataFrame:
        """
        Align time series data to consistent frequency.
        
        Args:
            df: DataFrame with time series data
            date_col: Name of date column
            value_col: Name of value column to aggregate
            group_col: Column to group by (e.g., SKU)
            
        Returns:
            DataFrame with aligned time series
        """
        logger.info("Aligning time series", frequency=self.frequency)
        
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Set date as index for resampling
        df_indexed = df.set_index(date_col)
        
        # Group by SKU and resample
        freq = self.freq_map.get(self.frequency, "M")
        
        aligned_data = []
        for sku_id, group in df.groupby(group_col):
            group_indexed = group.set_index(date_col)
            resampled = group_indexed[value_col].resample(freq).sum().reset_index()
            resampled[group_col] = sku_id
            aligned_data.append(resampled)
        
        result = pd.concat(aligned_data, ignore_index=True)
        result = result.rename(columns={date_col: "date", value_col: "demand"})
        
        logger.info("Time series aligned", rows=len(result), skus=result[group_col].nunique())
        
        return result
    
    def fill_missing_dates(self, df: pd.DataFrame, date_col: str = "date", 
                          group_col: str = "sku_id", value_col: str = "demand") -> pd.DataFrame:
        """
        Fill missing dates with zero values.
        
        Args:
            df: DataFrame with time series data
            date_col: Name of date column
            group_col: Column to group by
            value_col: Column to fill with zeros
            
        Returns:
            DataFrame with all dates filled
        """
        logger.info("Filling missing dates")
        
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Get date range for each SKU
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        
        freq = self.freq_map.get(self.frequency, "M")
        all_dates = pd.date_range(min_date, max_date, freq=freq)
        
        filled_data = []
        for sku_id, group in df.groupby(group_col):
            # Create complete date range for this SKU
            sku_dates = pd.DataFrame({date_col: all_dates})
            sku_dates[group_col] = sku_id
            
            # Merge with existing data
            merged = sku_dates.merge(group, on=[date_col, group_col], how="left")
            merged[value_col] = merged[value_col].fillna(0)
            
            filled_data.append(merged)
        
        result = pd.concat(filled_data, ignore_index=True)
        
        logger.info("Missing dates filled", rows=len(result))
        
        return result
    
    def create_lag_features(self, df: pd.DataFrame, value_col: str = "demand", 
                           lags: List[int] = [1, 3, 6, 12], group_col: str = "sku_id") -> pd.DataFrame:
        """
        Create lag features for time series.
        
        Args:
            df: DataFrame with time series data
            value_col: Column to create lags from
            lags: List of lag periods
            group_col: Column to group by
            
        Returns:
            DataFrame with lag features added
        """
        logger.info("Creating lag features", lags=lags)
        
        df = df.copy()
        df = df.sort_values([group_col, "date"])
        
        for lag in lags:
            df[f"lag_{lag}"] = df.groupby(group_col)[value_col].shift(lag)
        
        logger.info("Lag features created")
        
        return df
    
    def create_rolling_features(self, df: pd.DataFrame, value_col: str = "demand",
                                windows: List[int] = [3, 6, 12], group_col: str = "sku_id") -> pd.DataFrame:
        """
        Create rolling statistics features.
        
        Args:
            df: DataFrame with time series data
            value_col: Column to calculate rolling stats on
            windows: List of window sizes
            group_col: Column to group by
            
        Returns:
            DataFrame with rolling features added
        """
        logger.info("Creating rolling features", windows=windows)
        
        df = df.copy()
        df = df.sort_values([group_col, "date"])
        
        for window in windows:
            grouped = df.groupby(group_col)[value_col]
            
            # Rolling mean
            df[f"rolling_mean_{window}"] = grouped.transform(lambda x: x.rolling(window=window, min_periods=1).mean())
            
            # Rolling std
            df[f"rolling_std_{window}"] = grouped.transform(lambda x: x.rolling(window=window, min_periods=1).std())
            
            # Rolling max
            df[f"rolling_max_{window}"] = grouped.transform(lambda x: x.rolling(window=window, min_periods=1).max())
            
            # Rolling min
            df[f"rolling_min_{window}"] = grouped.transform(lambda x: x.rolling(window=window, min_periods=1).min())
        
        logger.info("Rolling features created")
        
        return df
    
    def create_seasonality_features(self, df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
        """
        Create seasonality features from date.
        
        Args:
            df: DataFrame with date column
            date_col: Name of date column
            
        Returns:
            DataFrame with seasonality features added
        """
        logger.info("Creating seasonality features")
        
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Month (1-12)
        df["month"] = df[date_col].dt.month
        
        # Quarter (1-4)
        df["quarter"] = df[date_col].dt.quarter
        
        # Year
        df["year"] = df[date_col].dt.year
        
        # Day of week (for weekly data)
        df["day_of_week"] = df[date_col].dt.dayofweek
        
        # Is holiday month (simplified - can be enhanced)
        df["is_holiday_month"] = df["month"].isin([11, 12]).astype(int)
        
        logger.info("Seasonality features created")
        
        return df
    
    def normalize_categorical(self, df: pd.DataFrame, categorical_cols: List[str]) -> pd.DataFrame:
        """
        Normalize categorical fields (one-hot encoding or label encoding).
        
        Args:
            df: DataFrame with categorical columns
            categorical_cols: List of categorical column names
            
        Returns:
            DataFrame with normalized categorical features
        """
        logger.info("Normalizing categorical features", columns=categorical_cols)
        
        df = df.copy()
        
        for col in categorical_cols:
            if col in df.columns:
                # One-hot encoding for low cardinality, label encoding for high
                unique_count = df[col].nunique()
                if unique_count <= 10:
                    # One-hot encode
                    dummies = pd.get_dummies(df[col], prefix=col)
                    df = pd.concat([df, dummies], axis=1)
                else:
                    # Label encode
                    df[f"{col}_encoded"] = pd.Categorical(df[col]).codes
        
        logger.info("Categorical features normalized")
        
        return df
    
    def transform_sales_history(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform sales history data with all feature engineering.
        
        Args:
            sales_df: Raw sales history DataFrame
            
        Returns:
            Transformed DataFrame with features
        """
        logger.info("Transforming sales history data")
        
        # Align time series
        df = self.align_time_series(sales_df, date_col="date", value_col="units_sold", group_col="sku_id")
        
        # Fill missing dates
        df = self.fill_missing_dates(df, date_col="date", group_col="sku_id", value_col="demand")
        
        # Create lag features
        df = self.create_lag_features(df, value_col="demand", lags=[1, 3, 6, 12], group_col="sku_id")
        
        # Create rolling features
        df = self.create_rolling_features(df, value_col="demand", windows=[3, 6, 12], group_col="sku_id")
        
        # Create seasonality features
        df = self.create_seasonality_features(df, date_col="date")
        
        logger.info("Sales history transformation complete", rows=len(df))
        
        return df
    
    def transform_all(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Transform all data types.
        
        Args:
            data: Dictionary mapping data type to DataFrame
            
        Returns:
            Dictionary mapping data type to transformed DataFrame
        """
        transformed = {}
        
        if "sales_history" in data:
            transformed["sales_history"] = self.transform_sales_history(data["sales_history"])
        
        # Other data types can be added here as needed
        if "inventory" in data:
            transformed["inventory"] = data["inventory"].copy()
        
        if "purchase_orders" in data:
            transformed["purchase_orders"] = data["purchase_orders"].copy()
        
        if "sku_master" in data:
            transformed["sku_master"] = data["sku_master"].copy()
        
        return transformed


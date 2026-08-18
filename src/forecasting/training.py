"""Model training pipeline with auto-selection."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from pathlib import Path
import structlog
from src.utils.logger import logger
from src.database.models import SalesHistory, Segmentation, SegmentationGroup
from src.forecasting.models import (
    ARIMAModel,
    ProphetModel,
    MovingAverageModel,
    XGBoostModel,
    LightGBMModel,
    CrostonModel,
    SBAModel,
)
from src.forecasting.registry import ModelRegistry
from src.config import settings

logger = structlog.get_logger()


class ModelTrainer:
    """Train and select models for SKUs."""
    
    def __init__(self, db_session: Session):
        """
        Initialize model trainer.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.registry = ModelRegistry(db_session)
        self.config = settings.forecasting_config
        
        # Model mapping by segment
        self.segment_model_map = {
            "AX": [ProphetModel, ARIMAModel],
            "BX": [ARIMAModel, ProphetModel],
            "AY": [XGBoostModel, LightGBMModel],
            "BY": [LightGBMModel, XGBoostModel],
            "AZ": [CrostonModel, SBAModel],
            "BZ": [SBAModel, CrostonModel],
            "CX": [MovingAverageModel],
            "CY": [MovingAverageModel, XGBoostModel],
            "CZ": [CrostonModel, SBAModel],
        }
    
    def get_models_for_segment(self, segment: str) -> List:
        """
        Get list of models to try for a segment.
        
        Args:
            segment: Segmentation group (e.g., "AX", "BY")
            
        Returns:
            List of model classes
        """
        return self.segment_model_map.get(segment, [MovingAverageModel])
    
    def prepare_training_data(self, sku_id: str) -> Optional[pd.DataFrame]:
        """
        Prepare training data for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            DataFrame with training data or None
        """
        # Get sales history
        sales = self.db.query(SalesHistory).filter(
            SalesHistory.sku_id == sku_id
        ).order_by(SalesHistory.date).all()
        
        if len(sales) < 12:  # Minimum data requirement
            return None
        
        # Convert to DataFrame
        data = pd.DataFrame([{
            "sku_id": s.sku_id,
            "date": s.date,
            "demand": s.units_sold,
        } for s in sales])
        
        return data
    
    def cross_validate(self, model_class, data: pd.DataFrame, 
                      n_splits: int = 5, test_size: float = 0.2) -> Dict[str, float]:
        """
        Perform cross-validation for a model.
        
        Args:
            model_class: Model class to evaluate
            data: Training data
            n_splits: Number of CV splits
            test_size: Proportion of data for testing
            
        Returns:
            Dictionary with average metrics
        """
        metrics_list = []
        
        # Simple time series cross-validation
        total_len = len(data)
        test_len = int(total_len * test_size)
        
        if total_len < test_len * 2:
            # Not enough data for CV, use simple train/test split
            train_size = int(total_len * (1 - test_size))
            train_data = data.iloc[:train_size]
            test_data = data.iloc[train_size:]
            
            model = model_class()
            model.train(train_data, target_col="demand", date_col="date", group_col="sku_id")
            
            if model.is_trained:
                # Generate predictions
                horizon = len(test_data)
                predictions = model.predict(horizon, test_data)
                actual = test_data["demand"].values
                
                metrics = model.evaluate(actual, predictions)
                return metrics
            else:
                return {"mape": np.inf, "mae": np.inf, "rmse": np.inf, "bias": 0.0, "mase": np.inf}
        
        # Multiple splits
        for i in range(n_splits):
            split_start = int(i * test_len)
            split_end = min(split_start + test_len, total_len)
            
            if split_end - split_start < 3:
                continue
            
            train_data = data.iloc[:split_start] if split_start > 0 else data.iloc[:split_end]
            test_data = data.iloc[split_start:split_end]
            
            if len(train_data) < 12 or len(test_data) < 1:
                continue
            
            try:
                model = model_class()
                model.train(train_data, target_col="demand", date_col="date", group_col="sku_id")
                
                if model.is_trained:
                    horizon = len(test_data)
                    predictions = model.predict(horizon, test_data)
                    actual = test_data["demand"].values
                    
                    metrics = model.evaluate(actual, predictions)
                    metrics_list.append(metrics)
            except Exception as e:
                logger.warning("CV split failed", error=str(e), split=i)
                continue
        
        if len(metrics_list) == 0:
            return {"mape": np.inf, "mae": np.inf, "rmse": np.inf, "bias": 0.0, "mase": np.inf}
        
        # Average metrics
        avg_metrics = {
            "mape": np.mean([m["mape"] for m in metrics_list]),
            "mae": np.mean([m["mae"] for m in metrics_list]),
            "rmse": np.mean([m["rmse"] for m in metrics_list]),
            "bias": np.mean([m["bias"] for m in metrics_list]),
            "mase": np.mean([m["mase"] for m in metrics_list]),
        }
        
        return avg_metrics
    
    def select_best_model(self, sku_id: str, segment: str, 
                         data: pd.DataFrame) -> Tuple[object, Dict[str, float]]:
        """
        Select best model for a SKU based on cross-validation.
        
        Args:
            sku_id: SKU identifier
            segment: Segmentation group
            data: Training data
            
        Returns:
            Tuple of (best_model_instance, best_metrics)
        """
        model_classes = self.get_models_for_segment(segment)
        
        best_model = None
        best_metrics = {"mape": np.inf}
        best_model_class = None
        
        for model_class in model_classes:
            try:
                logger.info("Evaluating model", sku_id=sku_id, model=model_class.__name__)
                metrics = self.cross_validate(model_class, data)
                
                # Select based on MAPE (lower is better)
                if metrics["mape"] < best_metrics["mape"]:
                    best_metrics = metrics
                    best_model_class = model_class
            except Exception as e:
                logger.warning("Model evaluation failed", model=model_class.__name__, error=str(e))
                continue
        
        if best_model_class is None:
            # Fallback to Moving Average
            best_model_class = MovingAverageModel
        
        # Train final model on all data
        best_model = best_model_class()
        best_model.train(data, target_col="demand", date_col="date", group_col="sku_id")
        
        return best_model, best_metrics
    
    def train_sku(self, sku_id: str, segment: Optional[str] = None) -> bool:
        """
        Train model for a single SKU.
        
        Args:
            sku_id: SKU identifier
            segment: Optional segmentation group (if None, will look up)
            
        Returns:
            True if training successful, False otherwise
        """
        logger.info("Training model for SKU", sku_id=sku_id)
        
        # Get segmentation if not provided
        if segment is None:
            seg = self.db.query(Segmentation).filter(Segmentation.sku_id == sku_id).first()
            if seg:
                segment = seg.segment_group.value
            else:
                segment = "CX"  # Default
        
        # Prepare data
        data = self.prepare_training_data(sku_id)
        if data is None:
            logger.warning("Insufficient data for training", sku_id=sku_id)
            return False
        
        # Select and train best model
        try:
            model, metrics = self.select_best_model(sku_id, segment, data)
            
            if not model.is_trained:
                logger.warning("Model training failed", sku_id=sku_id)
                return False
            
            # Save model
            model_dir = Path(settings.model.storage_path)
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"{sku_id}_{model.model_name}.pkl"
            
            # Save the entire model object (not just model.model)
            import pickle
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
            
            # Register model
            model_version = f"{model.model_name}_v1"
            self.registry.register_model(
                sku_id=sku_id,
                model_type=model.model_name,
                model_version=model_version,
                model_path=str(model_path),
                metrics=metrics,
            )
            
            logger.info("Model trained successfully", sku_id=sku_id, model=model.model_name, mape=metrics["mape"])
            return True
        
        except Exception as e:
            logger.error("Training failed", sku_id=sku_id, error=str(e))
            return False
    
    def train_all(self, sku_ids: Optional[List[str]] = None, 
                 segment_filter: Optional[str] = None) -> Dict[str, bool]:
        """
        Train models for all SKUs or specified SKUs.
        
        Args:
            sku_ids: Optional list of SKU IDs to train (if None, trains all)
            segment_filter: Optional segment filter (e.g., "AX", "BY")
            
        Returns:
            Dictionary mapping SKU ID to training success status
        """
        logger.info("Starting batch training", sku_count=len(sku_ids) if sku_ids else "all")
        
        # Get SKUs to train
        if sku_ids is None:
            if segment_filter:
                segs = self.db.query(Segmentation).filter(
                    Segmentation.segment_group == SegmentationGroup(segment_filter)
                ).all()
                sku_ids = [s.sku_id for s in segs]
            else:
                skus = self.db.query(Segmentation).all()
                sku_ids = [s.sku_id for s in skus]
        
        results = {}
        for sku_id in sku_ids:
            success = self.train_sku(sku_id)
            results[sku_id] = success
        
        success_count = sum(results.values())
        logger.info("Batch training complete", total=len(results), successful=success_count)
        
        return results


"""Prefect workflow for forecast generation."""

from prefect import flow, task
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog
from src.utils.logger import logger
from src.database.connection import SessionLocal
from src.segmentation import ABCXYZSegmentation
from src.forecasting.training import ModelTrainer
from src.database.models import Forecast, SalesHistory
from datetime import datetime, timedelta
from pathlib import Path
import pickle

logger = structlog.get_logger()


@task
def run_segmentation(replace: bool = False):
    """Task: Run ABC/XYZ segmentation."""
    logger.info("Starting segmentation")
    db = SessionLocal()
    try:
        segmentation = ABCXYZSegmentation(db)
        results = segmentation.run_segmentation(replace=replace)
        logger.info("Segmentation complete", skus=len(results))
        return results
    finally:
        db.close()


@task
def train_models(sku_ids: Optional[List[str]] = None, segment_filter: Optional[str] = None):
    """Task: Train models for SKUs."""
    logger.info("Starting model training", sku_count=len(sku_ids) if sku_ids else "all")
    db = SessionLocal()
    try:
        trainer = ModelTrainer(db)
        results = trainer.train_all(sku_ids=sku_ids, segment_filter=segment_filter)
        success_count = sum(results.values())
        logger.info("Model training complete", total=len(results), successful=success_count)
        return results
    finally:
        db.close()


@task
def generate_forecasts(sku_ids: Optional[List[str]] = None):
    """Task: Generate forecasts for SKUs."""
    logger.info("Starting forecast generation", sku_count=len(sku_ids) if sku_ids else "all")
    db = SessionLocal()
    try:
        from src.config import settings
        from src.database.models import ModelRegistry
        
        # Get active models
        if sku_ids:
            models = db.query(ModelRegistry).filter(
                ModelRegistry.sku_id.in_(sku_ids),
                ModelRegistry.is_active == True
            ).all()
        else:
            models = db.query(ModelRegistry).filter(ModelRegistry.is_active == True).all()
        
        forecast_horizon = settings.model.forecast_horizon_months
        
        forecasts_created = 0
        for model_reg in models:
            try:
                # Load model
                model_path = Path(model_reg.model_path)
                if not model_path.exists():
                    logger.warning("Model file not found", sku_id=model_reg.sku_id, path=str(model_path))
                    continue
                
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                
                # Get training data for prediction
                sales = db.query(SalesHistory).filter(
                    SalesHistory.sku_id == model_reg.sku_id
                ).order_by(SalesHistory.date.desc()).limit(24).all()
                
                if len(sales) < 12:
                    continue
                
                # Generate forecast
                predictions = model.predict(forecast_horizon)
                
                # Store forecasts
                forecast_date = datetime.now().date()
                for i, pred in enumerate(predictions):
                    forecast = Forecast(
                        sku_id=model_reg.sku_id,
                        forecast_date=forecast_date + timedelta(days=30 * (i + 1)),
                        predicted_units=float(pred),
                        confidence_level=0.8,  # Default confidence
                        model_type=model_reg.model_type,
                        model_version=model_reg.model_version,
                    )
                    db.add(forecast)
                    forecasts_created += 1
                
            except Exception as e:
                logger.error("Forecast generation failed", sku_id=model_reg.sku_id, error=str(e))
                continue
        
        db.commit()
        logger.info("Forecast generation complete", forecasts_created=forecasts_created)
        return forecasts_created
    
    finally:
        db.close()


@flow(name="forecast-pipeline")
def forecast_pipeline_flow(sku_ids: Optional[List[str]] = None, retrain: bool = False):
    """
    Complete forecast generation pipeline.
    
    Args:
        sku_ids: Optional list of SKU IDs to process
        retrain: Whether to retrain models
    """
    logger.info("Starting forecast pipeline")
    
    # Run segmentation if needed
    if retrain:
        run_segmentation(replace=True)
    
    # Train models if needed
    if retrain:
        train_models(sku_ids=sku_ids)
    
    # Generate forecasts
    forecasts_created = generate_forecasts(sku_ids=sku_ids)
    
    logger.info("Forecast pipeline complete", forecasts_created=forecasts_created)
    
    return forecasts_created


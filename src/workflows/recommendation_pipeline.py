"""Prefect workflow for recommendation generation."""

from prefect import flow, task
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog
from src.utils.logger import logger
from src.database.connection import SessionLocal
from src.recommendations import OrderRecommendationEngine

logger = structlog.get_logger()


@task
def generate_recommendations(sku_ids: Optional[List[str]] = None):
    """Task: Generate order recommendations."""
    logger.info("Starting recommendation generation", sku_count=len(sku_ids) if sku_ids else "all")
    db = SessionLocal()
    try:
        engine = OrderRecommendationEngine(db)
        recommendations = engine.generate_all_recommendations(sku_ids=sku_ids)
        logger.info("Recommendation generation complete", count=len(recommendations))
        return recommendations
    finally:
        db.close()


@flow(name="recommendation-pipeline")
def recommendation_pipeline_flow(sku_ids: Optional[List[str]] = None):
    """
    Complete recommendation generation pipeline.
    
    Args:
        sku_ids: Optional list of SKU IDs to process
    """
    logger.info("Starting recommendation pipeline")
    
    recommendations = generate_recommendations(sku_ids=sku_ids)
    
    logger.info("Recommendation pipeline complete", count=len(recommendations))
    
    return recommendations


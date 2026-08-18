"""Prefect workflow for data ingestion pipeline."""

from prefect import flow, task
from pathlib import Path
from sqlalchemy.orm import Session
import structlog
from src.utils.logger import logger
from src.database.connection import SessionLocal
from src.data import DataIngestion, DataValidator, DataTransformer, DataStorage

logger = structlog.get_logger()


@task
def ingest_data(data_dir: Path):
    """Task: Ingest data from files."""
    logger.info("Starting data ingestion", data_dir=str(data_dir))
    ingestion = DataIngestion(data_dir)
    data = ingestion.load_all_data()
    logger.info("Data ingestion complete", data_types=list(data.keys()))
    return data


@task
def validate_data(data: dict):
    """Task: Validate data quality."""
    logger.info("Starting data validation")
    validator = DataValidator()
    validation_results = validator.validate_all(data)
    
    # Log validation results
    for data_type, results in validation_results.items():
        if not results.get("valid", True):
            logger.warning("Validation issues", data_type=data_type, issues=results.get("issues", []))
        else:
            logger.info("Validation passed", data_type=data_type)
    
    return validation_results


@task
def transform_data(data: dict):
    """Task: Transform and engineer features."""
    logger.info("Starting data transformation")
    transformer = DataTransformer(frequency="monthly")
    transformed_data = transformer.transform_all(data)
    logger.info("Data transformation complete")
    return transformed_data


@task
def store_data(data: dict, replace: bool = False):
    """Task: Store data in database."""
    logger.info("Starting data storage", replace=replace)
    db = SessionLocal()
    try:
        storage = DataStorage(db)
        results = storage.store_all(data, replace=replace)
        logger.info("Data storage complete", results=results)
        return results
    finally:
        db.close()


@flow(name="data-ingestion-pipeline")
def data_ingestion_flow(data_dir: Path = Path("./data/raw"), replace: bool = False):
    """
    Complete data ingestion pipeline workflow.
    
    Args:
        data_dir: Directory containing raw data files
        replace: Whether to replace existing data
    """
    logger.info("Starting data ingestion pipeline")
    
    # Ingest
    data = ingest_data(data_dir)
    
    # Validate
    validation_results = validate_data(data)
    
    # Transform
    transformed_data = transform_data(data)
    
    # Store
    storage_results = store_data(transformed_data, replace=replace)
    
    logger.info("Data ingestion pipeline complete")
    
    return {
        "validation": validation_results,
        "storage": storage_results,
    }


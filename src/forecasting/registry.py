"""Model registry for tracking trained models."""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import structlog
from src.utils.logger import logger
from src.database.models import ModelRegistry as ModelRegistryDB

logger = structlog.get_logger()


class ModelRegistry:
    """Registry for managing trained models."""
    
    def __init__(self, db_session: Session):
        """
        Initialize model registry.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def register_model(self, sku_id: str, model_type: str, model_version: str,
                      model_path: str, metrics: Dict[str, float], 
                      metadata: Optional[Dict] = None, is_active: bool = True):
        """
        Register a trained model.
        
        Args:
            sku_id: SKU identifier
            model_type: Type of model (e.g., 'arima', 'prophet')
            model_version: Model version string
            model_path: Path to saved model file
            metrics: Dictionary with validation metrics
            metadata: Optional metadata dictionary
            is_active: Whether this model is active
        """
        import json
        
        # Deactivate previous models for this SKU
        if is_active:
            self.db.query(ModelRegistryDB).filter(
                ModelRegistryDB.sku_id == sku_id,
                ModelRegistryDB.is_active == True
            ).update({"is_active": False})
        
        registry_entry = ModelRegistryDB(
            sku_id=sku_id,
            model_type=model_type,
            model_version=model_version,
            model_path=model_path,
            training_date=datetime.utcnow(),
            validation_mape=metrics.get("mape"),
            validation_mae=metrics.get("mae"),
            validation_rmse=metrics.get("rmse"),
            validation_bias=metrics.get("bias"),
            validation_mase=metrics.get("mase"),
            is_active=is_active,
            model_metadata=json.dumps(metadata) if metadata else None,
        )
        
        self.db.add(registry_entry)
        self.db.commit()
        
        logger.info("Model registered", sku_id=sku_id, model_type=model_type, version=model_version)
    
    def get_active_model(self, sku_id: str) -> Optional[ModelRegistryDB]:
        """
        Get active model for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            ModelRegistryDB entry or None
        """
        return self.db.query(ModelRegistryDB).filter(
            ModelRegistryDB.sku_id == sku_id,
            ModelRegistryDB.is_active == True
        ).first()
    
    def get_all_models(self, sku_id: str) -> List[ModelRegistryDB]:
        """
        Get all models for a SKU.
        
        Args:
            sku_id: SKU identifier
            
        Returns:
            List of ModelRegistryDB entries
        """
        return self.db.query(ModelRegistryDB).filter(
            ModelRegistryDB.sku_id == sku_id
        ).order_by(ModelRegistryDB.training_date.desc()).all()


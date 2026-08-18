"""Configuration management for the demand forecasting system."""

import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/demand_forecasting")
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "demand_forecasting")
    user: str = os.getenv("DB_USER", "user")
    password: str = os.getenv("DB_PASSWORD", "password")
    
    class Config:
        env_prefix = "DB_"


class APISettings(BaseSettings):
    """API configuration settings."""
    
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    reload: bool = os.getenv("API_RELOAD", "true").lower() == "true"
    version: str = "v1"
    docs_enabled: bool = True
    
    class Config:
        env_prefix = "API_"


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    class Config:
        env_prefix = "SECRET_"


class ModelSettings(BaseSettings):
    """Model configuration settings."""
    
    storage_path: str = os.getenv("MODEL_STORAGE_PATH", "./models")
    forecast_horizon_months: int = int(os.getenv("FORECAST_HORIZON_MONTHS", "12"))
    service_level: float = float(os.getenv("SERVICE_LEVEL", "0.95"))
    
    class Config:
        env_prefix = "MODEL_"


class Settings:
    """Main settings class aggregating all configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent / "config.yaml"
        self._yaml_config = self._load_yaml_config()
        
        self.database = DatabaseSettings()
        self.api = APISettings()
        self.security = SecuritySettings()
        self.model = ModelSettings()
        
        # Ensure model storage directory exists
        Path(self.model.storage_path).mkdir(parents=True, exist_ok=True)
    
    def _load_yaml_config(self) -> dict:
        """Load YAML configuration file."""
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    @property
    def segmentation_config(self) -> dict:
        """Get segmentation configuration from YAML."""
        return self._yaml_config.get("segmentation", {})
    
    @property
    def forecasting_config(self) -> dict:
        """Get forecasting configuration from YAML."""
        return self._yaml_config.get("forecasting", {})
    
    @property
    def optimization_config(self) -> dict:
        """Get optimization configuration from YAML."""
        return self._yaml_config.get("optimization", {})
    
    @property
    def monitoring_config(self) -> dict:
        """Get monitoring configuration from YAML."""
        return self._yaml_config.get("monitoring", {})


# Global settings instance
settings = Settings()


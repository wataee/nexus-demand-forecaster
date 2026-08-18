"""Logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Optional
import structlog
from src.config import settings


def setup_logging(log_level: Optional[str] = None, log_format: Optional[str] = None):
    """Configure structured logging for the application."""
    
    log_level = log_level or settings._yaml_config.get("logging", {}).get("level", "INFO")
    log_format = log_format or settings._yaml_config.get("logging", {}).get("format", "json")
    
    # Create logs directory if it doesn't exist
    log_file = settings._yaml_config.get("logging", {}).get("file", "logs/app.log")
    log_path = Path(log_file).parent
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    logging.getLogger().addHandler(file_handler)
    
    return structlog.get_logger()


# Initialize logger
logger = setup_logging()


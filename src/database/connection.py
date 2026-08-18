"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from src.config import settings

# Create database engine
# Handle SQLite vs PostgreSQL with graceful fallback for testing/local mode
db_url = settings.database.url
try:
    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            echo=False,
            pool_pre_ping=True,
        )
        with engine.connect() as conn:
            pass
except Exception:
    engine = create_engine(
        "sqlite:///./demand_forecasting.db",
        echo=False,
        connect_args={"check_same_thread": False},
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


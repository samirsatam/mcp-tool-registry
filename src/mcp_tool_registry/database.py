"""Database configuration and session management."""

import json
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

# Database configuration
DATABASE_URL = "sqlite:///./mcp_registry.db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_schema(schema: dict) -> str:
    """Serialize schema dict to JSON string."""
    return json.dumps(schema, indent=2)


def deserialize_schema(schema_str: str) -> dict:
    """Deserialize JSON string to schema dict."""
    return json.loads(schema_str)

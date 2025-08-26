"""
Database connection and session management.
Handles SQLAlchemy engine creation, session management, and connection pooling.
"""

from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging
from typing import Generator

from config import get_database_settings

# Configure logging
logger = logging.getLogger(__name__)

# Database settings
db_settings = get_database_settings()

# Create SQLAlchemy engine with production-grade configuration
engine = create_engine(
    db_settings.database_url,
    # Connection pool settings
    poolclass=QueuePool,
    pool_size=db_settings.pool_size,
    max_overflow=db_settings.max_overflow,
    pool_timeout=db_settings.pool_timeout,
    pool_recycle=db_settings.pool_recycle,
    pool_pre_ping=True,  # Validates connections before use
    # Performance settings
    echo=False,  # Set to True for SQL query logging in development
    future=True,  # Enable SQLAlchemy 2.0 style
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Prevent lazy loading issues
)

# Create Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


# Event listeners for connection management
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific optimizations on connection."""
    if "postgresql" in str(dbapi_connection):
        # Set PostgreSQL-specific optimizations
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '30s'")
            cursor.execute("SET lock_timeout = '10s'")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Provides a database session for FastAPI dependency injection.
    Automatically handles session cleanup and rollback on errors.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Use this for non-FastAPI database operations.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """Drop all database tables. Use with caution!"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")

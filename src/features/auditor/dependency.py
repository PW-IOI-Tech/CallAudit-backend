"""
Dependency Injection Module for Auditor Features

This module provides dependency injection functions for the auditor feature set.
It defines how FastAPI should provide dependencies like database sessions,
repositories, and services to route handlers (endpoints).

These functions are typically used with FastAPI's `Depends()` in route parameters.
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db  # your SessionLocal generator
from features.auditor.repository import AuditorRepository
from features.auditor.services import AuditorService


def get_auditor_repository(db: Session = Depends(get_db)) -> AuditorRepository:
    """
    Dependency function to create and provide an AuditorRepository instance.

    This function is used by FastAPI's dependency injection system to provide
    a configured AuditorRepository to endpoints or other dependencies that need it.
    It depends on an active database session.

    Args:
        db (Session): An active SQLAlchemy database session, provided by `get_db`.

    Returns:
        AuditorRepository: An instance of AuditorRepository initialized with
                          the provided database session.
    """
    return AuditorRepository(db)


def get_auditor_service(
    repo: AuditorRepository = Depends(get_auditor_repository),
) -> AuditorService:
    """
    Dependency function to create and provide an AuditorService instance.

    This function is used by FastAPI's dependency injection system to provide
    a configured AuditorService to endpoints. It depends on an AuditorRepository
    instance, which is automatically provided by `get_auditor_repository`.

    Args:
        repo (AuditorRepository): An AuditorRepository instance, provided by
                                 `get_auditor_repository`.

    Returns:
        AuditorService: An instance of AuditorService initialized with
                       the provided repository.
    """
    return AuditorService(repo)

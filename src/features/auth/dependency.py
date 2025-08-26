"""
Authentication Dependency Injection Module

This module provides dependency injection functions for authentication-related
components. It defines how FastAPI should provide dependencies like database sessions,
authentication repositories, and authentication services to route handlers.

These functions are typically used with FastAPI's `Depends()` in route parameters
for authentication endpoints.
"""

from features.auth.repository import AuthRepository
from features.auth.services import AuthService
from sqlalchemy.orm import Session
from database import get_db
from fastapi import Depends


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Dependency function to create and provide an AuthService instance.

    This function is used by FastAPI's dependency injection system to provide
    a configured AuthService to authentication endpoints. It depends on an
    active database session.

    Args:
        db (Session): An active SQLAlchemy database session, provided by `get_db`.

    Returns:

        AuthService: An instance of AuthService initialized with the provided
                    database session.
    """
    return AuthService(db)


def get_auth_repository(db: Session = Depends(get_db)) -> AuthRepository:
    """
    Dependency function to create and provide an AuthRepository instance.

    This function is used by FastAPI's dependency injection system to provide
    a configured AuthRepository to endpoints or other dependencies that need it.
    It depends on an active database session.

    Args:
        db (Session): An active SQLAlchemy database session, provided by `get_db`.

    Returns:

        AuthRepository: An instance of AuthRepository initialized with
                       the provided database session.
    """
    return AuthRepository(db)

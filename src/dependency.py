"""
Authentication and Authorization Module

This module provides authentication utilities for FastAPI applications, specifically
handling JWT token-based authentication for auditor and manager user roles.

The module implements a dependency injection pattern for user authentication,
extracting JWT tokens from HTTP cookies, validating them, and returning the
appropriate user objects based on their roles.

Key Features:
    - JWT token validation from HTTP cookies
    - Role-based user authentication (Auditor/Manager)
    - Database user verification
    - Comprehensive error handling and logging
    - Type hints for better code maintainability

Dependencies:
    - FastAPI: Web framework components
    - SQLAlchemy: Database ORM
    - python-jose: JWT token handling
    - Custom repositories for user data access

Example:
    ```python
    from fastapi import FastAPI, Depends
    from auth import get_current_user

    app = FastAPI()

    @app.get("/protected")
    async def protected_route(current_user = Depends(get_current_user)):
        return {"user": current_user.email, "role": current_user.role}
    ```

Author: Shoyeb Ansari
Version: 0.1.0
Created: 2025
"""

from fastapi import Request, HTTPException, Depends, status
from sqlalchemy.orm import Session
import logging
from config import get_jwt_settings
from database import get_db
from jose import jwt

from features.auditor.repository import AuditorRepository
from features.manager.repository import ManagerRepository
from models import Auditor, Manager

# Configure module-level logger for authentication operations
logger = logging.getLogger(__name__)


def get_current_user(req: Request, db: Session = Depends(get_db)) -> Auditor | Manager:
    """
    FastAPI dependency for authenticating and retrieving the current user.

    This function serves as a dependency injection for FastAPI routes that require
    user authentication. It extracts JWT tokens from HTTP cookies, validates them,
    and returns the corresponding user object from the database based on their role.

    The function supports two user types:
    - Auditor: Users with auditing privileges
    - Manager: Users with management privileges

    Authentication Flow:
    1. Extract JWT token from 'token' cookie
    2. Decode and validate the token using configured secret and algorithm
    3. Extract email and role from token payload
    4. Query database for user based on role
    5. Return user object if found, raise HTTPException otherwise

    Args:
        req (Request): FastAPI request object containing HTTP cookies and headers.
                      The 'token' cookie must contain a valid JWT token.
        db (Session, optional): SQLAlchemy database session for user queries.
                               Defaults to Depends(get_db) for dependency injection.

    Returns:

        Auditor | Manager: Returns either an Auditor or Manager object based on
                          the role specified in the JWT token. The returned object
                          contains all user information from the database.

    Raises:
        HTTPException: Raised in the following scenarios:
            - 401 UNAUTHORIZED: Missing token, invalid token payload, or invalid user role
            - 404 NOT_FOUND: User not found in database despite valid token
            - 500 INTERNAL_SERVER_ERROR: Unexpected errors during authentication process

    Security Considerations:
        - Tokens are expected to be httpOnly cookies for XSS protection
        - JWT tokens must be signed with the configured secret key
        - Token algorithm must match the configured algorithm
        - Database verification ensures token hasn't been compromised

    Example:
        ```python
        @app.get("/dashboard")
        async def dashboard(current_user: Auditor | Manager = Depends(get_current_user)):
            return {
                "message": f"Welcome {current_user.email}",
                "role": current_user.role,
                "permissions": current_user.permissions
            }
        ```

    Note:
        This function should be used as a FastAPI dependency. Direct calls are not
        recommended as they bypass the dependency injection system.
    """
    try:
        # Retrieve JWT configuration settings
        jwt_settings = get_jwt_settings()

        # Extract JWT token from HTTP cookies
        token = req.cookies.get("token", None)

        # Validate token presence
        if not token:
            logger.error("Authentication failed: Token not found in cookies")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing",
            )

        # Decode and validate JWT token
        try:
            payload = jwt.decode(
                token, jwt_settings.jwt_secret, algorithms=[jwt_settings.algorithm]
            )
        except jwt.JWTError as jwt_error:
            logger.error(f"JWT decoding failed: {str(jwt_error)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Extract user information from token payload
        email = payload.get("email")
        role = payload.get("role")

        # Validate required payload fields
        if email is None or role is None:
            logger.error(
                "Authentication failed: Email or role not found in token payload"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # Role-based user authentication and retrieval
        if role == "manager":
            # Handle manager authentication
            repo = ManagerRepository(db)
            manager = repo.get_manager(email=email)

            if manager is None:
                logger.error(
                    f"Manager authentication failed: Manager with email {email} not found in database"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Manager not found",
                )

            logger.info(f"Manager authentication successful: {email}")
            return manager

        elif role == "auditor":
            # Handle auditor authentication
            repo = AuditorRepository(db)
            auditor = repo.get_auditor(email=email)

            if auditor is None:
                logger.error(
                    f"Auditor authentication failed: Auditor with email {email} not found in database"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Auditor not found",
                )

            logger.info(f"Auditor authentication successful: {email}")
            return auditor
        else:
            # Handle invalid role
            logger.error(
                f"Authentication failed: Invalid role '{role}' for user {email}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user role: user must be either manager or auditor",
            )

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions without modification
        # This preserves the specific error codes and messages set above
        raise http_exc

    except Exception as e:
        # Handle unexpected errors with generic 500 response
        logger.error(
            f"Unexpected error during user authentication: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User verification failed due to internal server error",
        )

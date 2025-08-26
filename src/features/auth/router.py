"""
Authentication API Router Module

This module defines the FastAPI routes (endpoints) for authentication-related
functionalities. It handles user login, logout, and authentication status checking
for both managers and auditors. It delegates business logic to the AuthService.

All routes are prefixed with '/auth'.
"""

from fastapi import APIRouter, Form, HTTPException, Request, Response, Depends, status
import logging

from dependency import get_current_user
from features.auditor.schemas import BaseResponse, LoginSchema, User
from features.auth.dependency import get_auth_service
from features.auth.schemas import AuditorSchema, CheckAuthSchema, ManagerSchema
from features.auth.services import AuthService
from features.manager.dependency import get_manager_repository
from features.manager.repository import ManagerRepository
from features.manager.services import ManagerService
from models import Auditor, Manager

logger = logging.getLogger(__name__)

# Create API router with prefix and tags for documentation grouping
router = APIRouter(prefix="/auth", tags=["API endpoints for auth"])


@router.post(
    "/login",
    description="API endpoint for both manager and auditor login",
    response_model=LoginSchema,
    summary="User Login",
    responses={
        200: {"description": "Login successful"},
        400: {"description": "Bad request - missing form data"},
        401: {"description": "Unauthorized - invalid credentials"},
        403: {"description": "Forbidden - user account not active"},
        404: {"description": "Not found - user with email not found"},
        500: {"description": "Internal server error"},
    },
)
def login(
    response: Response,
    email: str = Form(..., description="User's email address"),
    password: str = Form(..., description="User's password"),
    role: str = Form(..., description="User's role ('manager' or 'auditor')"),
    service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user (manager or auditor) and set an authentication cookie.

    This endpoint validates user credentials and role, generates a JWT token upon
    successful authentication, and sets it as an HTTP-only cookie in the response.

    Args:
        response (Response): The FastAPI Response object to set the auth cookie.
        email (str): The email address provided by the user for login.
        password (str): The password provided by the user for login.
        role (str): The role of the user ('manager' or 'auditor').
        service (AuthService): The authentication service instance for business logic.

    Returns:

        LoginSchema: A schema object containing the login success status,
                     a message, and the user details (id, name, email, role).

    Raises:
        HTTPException:
            - 400 Bad Request: If required form data is missing.
            - 401 Unauthorized: If credentials are invalid.
            - 403 Forbidden: If user account is not active.
            - 404 Not Found: If user with given email doesn't exist.
            - 500 Internal Server Error: If JWT token generation fails.
    """
    return service.login(email, password, role, response)


@router.get(
    "/logout",
    description="API endpoint to log out the user",
    response_model=BaseResponse,
    summary="User Logout",
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Unauthorized - not authenticated"},
        500: {"description": "Internal server error"},
    },
)
def logout(
    request: Request,
    response: Response,
    user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Log out the currently authenticated user.

    This endpoint deletes the authentication cookie from the response,
    effectively logging out the user.

    Args:
        request (Request): The FastAPI Request object containing cookies.
        response (Response): The FastAPI Response object to delete the auth cookie.
        user: The authenticated user object obtained from JWT token validation.
        service (AuthService): The authentication service instance for business logic.

    Returns:

        BaseResponse: A schema object indicating successful logout.

    Raises:
        HTTPException:
            - 401 Unauthorized: If user is not authenticated.
            - 500 Internal Server Error: If logout process fails.
    """
    return service.logout(request, response)


@router.get(
    "/check-auth",
    description="API endpoint to verify authentication status and get user details",
    response_model=CheckAuthSchema,
    summary="Check Authentication Status",
    responses={
        200: {"description": "User is authenticated"},
        401: {"description": "Unauthorized - not authenticated or invalid user type"},
        500: {"description": "Internal server error"},
    },
)
def check_auth(
    repo: ManagerRepository = Depends(get_manager_repository),
    user=Depends(get_current_user),
):
    """
    Verify the authentication status of the current user and return user details.

    This endpoint checks if the user is properly authenticated via JWT token
    and returns the user's basic information along with their role.

    Args:
        user: The authenticated user object obtained from JWT token validation.
              Can be either an Auditor or Manager instance.

    Returns:

        LoginSchema: A schema object containing authentication status and user details
                     (id, name, email, role) if the user is authenticated.

    Raises:
        HTTPException:
            - 401 Unauthorized: If user is not authenticated or is not a valid
              auditor/manager.
            - 500 Internal Server Error: If an unexpected error occurs.
    """
    try:
        role = None
        if isinstance(user, Auditor):
            role = "auditor"

            manager = repo.get_manager(id=user.manager_id)

            return CheckAuthSchema(
                success=True,
                message="User is authenticated",
                user=AuditorSchema(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    role=role,
                    manager=manager.name,
                ),
            )
        elif isinstance(user, Manager):
            role = "manager"

            return CheckAuthSchema(
                success=True,
                message="User is authenticated",
                user=ManagerSchema(
                    id=user.id, name=user.name, email=user.email, role=role
                ),
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorised access, user is not auditor or manager.",
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(
            f"Internal server error occurred while checking authentication, error: {str(e)}"
        )
        raise HTTPException(
            detail="Internal server error occurred while checking authentication",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

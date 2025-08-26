"""
Authentication Service Module

This module contains the `AuthService` class, which provides a unified interface
for handling user authentication (login/logout) operations across different user roles
such as managers and auditors. It orchestrates the authentication flow by delegating
role-specific logic to their respective services.
"""

from sqlalchemy.orm import Session
from fastapi import Request, Response, HTTPException, status
from features.auditor.schemas import BaseResponse, LoginSchema
from features.manager.dependency import get_manager_service, get_manager_repository
from features.auditor.dependency import get_auditor_service, get_auditor_repository
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service class for handling user authentication operations.

    This service acts as a central authentication handler that routes login requests
    to the appropriate role-specific service (manager or auditor) and manages
    common authentication operations like logout.
    """

    def __init__(self, db: Session):
        """
        Initializes the AuthService with database session and role-specific services.

        Args:
            db (Session): An active SQLAlchemy database session used to initialize
                         role-specific repositories and services.
        """
        self.repo = db
        self.manager_service = get_manager_service(get_manager_repository(db))
        self.auditor_service = get_auditor_service(get_auditor_repository(db))

    def login(
        self, email: str, password: str, role: str, response: Response
    ) -> LoginSchema:
        """
        Authenticates a user based on their role and credentials.

        This method delegates the authentication process to the appropriate
        role-specific service (manager or auditor) based on the provided role.
        Upon successful authentication, it sets an authentication cookie in the response.

        Args:
            email (str): The email address of the user attempting to log in.
            password (str): The password provided by the user.
            role (str): The role of the user ('manager' or 'auditor').
            response (Response): The FastAPI Response object to set the auth cookie.

        Returns:

            LoginSchema: A schema object containing login success status, message,
                        and user details including ID, name, email, and role.

        Raises:
            HTTPException:
                - 404 Not Found: If user with given email doesn't exist (from role services).
                - 403 Forbidden: If user account is not active (from role services).
                - 401 Unauthorized: If password is incorrect (from role services).
                - 500 Internal Server Error: If JWT token generation fails or
                  if an invalid role is provided.
        """
        try:
            if role == "manager":
                return self.manager_service.login_manager(email, password, response)
            elif role == "auditor":
                return self.auditor_service.login_auditor(email, password, response)

            logger.error("Invalid user role provided: %s", role)
            raise HTTPException(
                detail="Invalid user role",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error occurred while logging in, error: {str(e)}")
            raise HTTPException(
                detail="Internal server error while logging in",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def logout(self, request: Request, response: Response) -> BaseResponse:
        """
        Logs out the current user by deleting the authentication cookie.

        This method checks for the presence of an authentication token in the request
        cookies and removes it by deleting the 'token' cookie from the response.

        Args:
            request (Request): The FastAPI Request object containing cookies.
            response (Response): The FastAPI Response object to delete the auth cookie.

        Returns:

            BaseResponse: A schema object indicating successful logout.

        Raises:
            HTTPException:
                - 401 Unauthorized: If no authentication token is found in cookies.
                - 500 Internal Server Error: If an unexpected error occurs during logout.
        """
        try:
            # Check if authentication token exists in cookies
            token = request.cookies.get("token")

            if not token:
                logger.error("Authentication token not found in cookies")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )

            # Delete the authentication cookie to log out the user
            response.delete_cookie("token")
            return BaseResponse(
                success=True,
                message="Successfully logged out",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to logout user, error: {str(e)}")
            raise HTTPException(
                detail="Failed to logout user",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

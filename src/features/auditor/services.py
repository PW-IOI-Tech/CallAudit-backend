"""
Auditor Service Module

This module contains the `AuditorService` class, which encapsulates the core business
logic related to auditors. It handles operations such as auditor login, retrieving
call data, dashboard analytics, approving leads, managing flagged audits, and
interacting with the `AuditorRepository` for data access.
"""

import logging
from passlib.context import CryptContext

from typing import Any, Dict
from fastapi import HTTPException, status, Response
from core.jwt_util import get_jwt_util
from features.auditor.repository import AuditorRepository
from config import get_jwt_settings
from features.auditor.schemas import (
    BaseResponse,
    CallStats,
    CallsResponseSchema,
    DashboardAnalysisResponse,
    LoginSchema,
    User,
)
from features.manager.dependency import get_manager_repository
from features.manager.schemas import FlaggedAuditsResponse
from models import Auditor

logger = logging.getLogger(__name__)


class AuditorService:
    """
    Service class for handling auditor-related business logic.

    This service acts as an intermediary between the API endpoints (likely in a router)
    and the `AuditorRepository`, processing data and orchestrating application flow
    for auditor functionalities.
    """

    def __init__(self, repo: AuditorRepository):
        """
        Initializes the AuditorService with a repository instance.

        Args:
            repo (AuditorRepository): An instance of the repository used for
                                      data access operations related to auditors.
        """
        self.repo = repo
        self.jwt_util = get_jwt_util()

    def login_auditor(
        self, email: str, password: str, response: Response
    ) -> LoginSchema:
        """
        Authenticates an auditor and sets an authentication cookie.

        This method verifies the auditor's credentials, checks if the account is active,
        generates a JWT token upon successful authentication, and sets it as an HTTP-only
        cookie in the response.

        Args:
            email (str): The email address provided by the auditor for login.
            password (str): The password provided by the auditor for login.
            response (Response): The FastAPI Response object to set the auth cookie.

        Returns:
            LoginSchema: A schema object containing the login success status,
                         a message, and the user details (id, name, email, role).

        Raises:
            HTTPException:
                - 404 Not Found: If no auditor exists with the given email.
                - 403 Forbidden: If the auditor account is not active.
                - 401 Unauthorized: If the provided password is incorrect.
                - 500 Internal Server Error: If JWT token generation fails or
                  an unexpected error occurs.
        """
        try:
            # Find if auditor exists
            auditor = self.repo.get_auditor(email=email)
            if not auditor:
                logger.error("No auditor found with given email")
                raise HTTPException(
                    detail=f"No auditor found with given email",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if not auditor.is_active:
                logger.error("Auditor is not active")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden request, auditor is not active",
                )

            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            is_password_correct = pwd_context.verify(password, auditor.password)

            # Compare password
            if (
                not is_password_correct
            ):  # TODO: Plain text comparison, consider hashing
                logger.error("Password not matched")
                raise HTTPException(
                    detail=f"Password not matched",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # Generate JWT
            token_payload = {
                "id": auditor.id,
                "name": auditor.name,
                "email": auditor.email,
                "role": "auditor",
            }

            token = self.jwt_util.create_jwt_token(token_payload)
            if not token:
                logger.error("Failed to generate JWT token")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate JWT token",
                )
            refresh_token = self.jwt_util.create_refresh_token({"id": auditor.id})
            if not refresh_token:
                logger.error("Failed to generate refresh token")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate refresh token",
                )
            # Set the JWT token in an HTTP-only cookie
            # Security Note: 'secure' should be True in production with HTTPS
            response.set_cookie(
                key="token",
                value=token,
                httponly=True,
                secure=False,  # Set True if HTTPS
                samesite="lax",  # or 'strict' or 'none'
                max_age=24
                * 60
                * 60,  # Convert minutes to seconds if needed by set_cookie
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=7 * 24 * 60 * 60,
            )

            return LoginSchema(
                success=True,
                message="Auditor logged in successfully.",
                user=User(
                    id=auditor.id,
                    name=auditor.name,
                    email=auditor.email,
                    role="auditor",
                ),
            )
        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to login for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while auditor login",
            )

    def add_new_auditor(self, auditor_data: Dict[str, any]) -> BaseResponse:
        try:

            is_auditor_created = self.repo.create_new_auditor(auditor_data)
            if not is_auditor_created:
                logger.error(f"Failed to create new auditor")
                raise HTTPException(
                    detail="Failed to create new auditor",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            logger.info("Auditor created successfully")
            return BaseResponse(success=True, message="Auditor created successfully.")

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error while creating new auditor, {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server error occurred while creating new auditor",
            )

    def get_calls(self, auditor: Auditor) -> CallsResponseSchema:
        """
        Retrieves calls assigned to a specific auditor along with call statistics.

        Fetches the list of calls and summary statistics (audited, unaudited, flagged)
        for the provided auditor object.

        Args:
            auditor (Auditor): The authenticated auditor object obtained from the request.

        Returns:
            CallsResponseSchema: A schema object containing the success status,
                                 a message, the list of calls, and call statistics.

        Raises:
            HTTPException:
                - 401 Unauthorized: If the provided user object is not an Auditor instance.
                - 500 Internal Server Error: If fetching calls or stats fails or
                  returns None/empty unexpectedly.
        """
        try:
            if not isinstance(auditor, Auditor):
                logger.error("Current user is not auditor")
                raise HTTPException(
                    detail="Unauthorised access, current user is not auditor.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            calls = self.repo.get_calls(auditor.id)
            call_stats = self.repo.get_call_stats(auditor.id)
            if calls is None or call_stats is None:  # Check explicitly for None
                logger.error("calls or call_stats is None")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while fetching call data.",
                )
            return CallsResponseSchema(
                success=True,
                message="Successfully retrieved calls for auditor",
                calls=calls,
                call_stats=CallStats(
                    audited=call_stats["audited"],
                    unaudited=call_stats["unaudited"],
                    flagged=call_stats["flagged"],
                ),
            )
        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to get calls for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while fetching calls",
            )

    def get_dashboard_data(self, auditor: Auditor) -> DashboardAnalysisResponse:
        """
        Retrieves dashboard analytics data for a specific auditor.

        Aggregates data for the auditor's dashboard, including total leads,
        audited calls, flagged calls, recent activity, and trends over the last 7 days.

        Args:
            auditor (Auditor): The authenticated auditor object obtained from the request.

        Returns:
            DashboardAnalysisResponse: A schema object containing dashboard metrics,
                                       latest calls, and historical data.

        Raises:
            HTTPException:
                - 401 Unauthorized: If the provided user object is not an Auditor instance.
                - 500 Internal Server Error: If fetching any of the dashboard data components fails.
        """
        try:
            if not isinstance(auditor, Auditor):
                logger.error("Current user is not auditor")
                raise HTTPException(
                    detail="Unauthorised access, current user is not auditor.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            call_stats = self.repo.get_call_stats(auditor.id)
            latest_calls = self.repo.get_latest_calls(auditor.id)
            last_7_days_data = self.repo.get_last_7_days_data(auditor.id)
            # Check if any required data is missing
            if call_stats is None or latest_calls is None or last_7_days_data is None:
                logger.error(
                    "One or more dashboard data components (call_stats, latest_calls, last_7_days_data) is None"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while fetching dashboard data",
                )
            return DashboardAnalysisResponse(
                success=True,
                message="Successfully retrieved dashboard data",  # Typo: should be "Successfully"
                total_assigned_leads=call_stats["audited"] + call_stats["unaudited"],
                total_audited_calls=call_stats["audited"],
                flagged_calls=call_stats["flagged"],
                latest_calls=latest_calls,
                last_7_days_data=last_7_days_data,
            )
        except HTTPException as http_exception:
            # Re-raise HTTP exceptions
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to get dashboard data for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while fetching dashboard data",  # More specific detail
            )

    def approve_lead(self, data: Dict[str, Any], auditor: Auditor) -> BaseResponse:
        """
        Approves a lead/audit based on provided data.

        Delegates the approval logic and database update to the repository layer.

        Args:
            data (Dict[str, Any]): The data payload containing information needed
                                   for the approval process (e.g., audit ID).
            auditor (Auditor): The authenticated auditor performing the approval.

        Returns:
            BaseResponse: A schema object indicating the success status and a message.

        Raises:
            HTTPException:
                - 500 Internal Server Error: If the approval process or database update fails.
        """
        try:
            logger.info("Approve lead api called")
            # Delegate the core logic to the repository
            self.repo.approve_lead_and_update_db(data, auditor.id)
            return BaseResponse(success=True, message="Successfully approved audit")
        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to approve leads, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while approving leads",
            )

    def unflag_flagged_audit(self, auditor: Auditor, audit_id: str) -> BaseResponse:
        """
        Removes the 'flagged' status from a specific audit.

        This action typically requires elevated permissions or specific checks.
        It retrieves a manager repository instance to perform the unflagging operation.

        Args:
            auditor (Auditor): The authenticated auditor requesting the unflag action.
                               Authorization check is performed.
            audit_id (str): The unique identifier of the audit to be unflagged.

        Returns:
            BaseResponse: A schema object indicating success and a confirmation message.

        Raises:
            HTTPException:
                - 401 Unauthorized: If the user is not an Auditor instance.
                - 500 Internal Server Error: If the unflagging process fails in the manager repository.
        """
        try:
            if not isinstance(auditor, Auditor):
                logger.error("User is not auditor")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorised access, user is not auditor.",  # Typo: should be "Unauthorized"
                )
            # Obtain manager repository instance to perform the unflag operation
            repo_manager = get_manager_repository(self.repo.db)
            is_unflagged = repo_manager.unflag_audit(audit_id)
            if not is_unflagged:
                logger.error("Failed to unflag audit")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while unflagging audit",
                )
            return BaseResponse(
                success=True,
                message=f"Successfully unflagged given audit with id: {audit_id}",
            )
        except HTTPException as e:
            # Re-raise specific HTTP exceptions from manager repo or auth check
            raise e
        except Exception as e:
            logger.error(f"Failed to unflag audit, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while unflagging audit",
            )

    def get_flagged_audits(self, auditor: Auditor) -> FlaggedAuditsResponse:
        """
        Retrieves the list of audits flagged by a specific auditor.

        Fetches the latest flagged audits associated with the provided auditor.

        Args:
            auditor (Auditor): The authenticated auditor whose flagged audits are requested.

        Returns:
            FlaggedAuditsResponse: A schema object containing the success status,
                                   a message, and the list of flagged audits.

        Raises:
            HTTPException:
                - 401 Unauthorized: If the user is not an Auditor instance.
                - 500 Internal Server Error: If fetching flagged audits fails.
        """
        try:
            if not isinstance(auditor, Auditor):
                logger.error("User is not auditor")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized access, user is not auditor.",
                )
            logger.info(
                f"API endpoint called for getting flagged audits for auditor with id: {auditor.id}"
            )
            # Retrieve the list of flagged audits from the repository
            flagged_audits = self.repo.get_all_latest_flagged_audit(auditor.id)

            # Handle case where no flagged audits exist (empty list is valid)
            if flagged_audits == []:
                return FlaggedAuditsResponse(
                    success=True,
                    message="Successfully retrieved the flagged audits",
                    flagged_audits=flagged_audits,
                )

            # Handle case where retrieval failed (repo returned None or False-equivalent)
            if not flagged_audits:
                logger.error("Failed to get flagged audits")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while fetching flagged audits.",
                )

            # Return successful response with the list of audits
            return FlaggedAuditsResponse(
                success=True,
                message="Successfully retrieved the flagged audits",
                flagged_audits=flagged_audits,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to get flagged audits for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting flagged audits.",
            )

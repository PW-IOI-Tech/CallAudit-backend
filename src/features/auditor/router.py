"""
Auditor API Router Module

This module defines the FastAPI routes (endpoints) specifically for auditor-related
functionalities. It handles HTTP requests, delegates business logic to the
AuditorService, and returns appropriate responses.

All routes are prefixed with '/auditor'.
"""

from typing import Optional
from fastapi import APIRouter, Form, Depends, Response
from database import get_db
from sqlalchemy.orm import Session
import logging

from dependency import get_current_user
from features.auditor.schemas import (
    BaseResponse,
    CallsResponseSchema,
    DashboardAnalysisResponse,
)
from features.auditor.dependency import get_auditor_service
from features.auditor.services import AuditorService
from features.manager.schemas import FlaggedAuditsResponse
from models import Auditor

logger = logging.getLogger(__name__)

# Create API router with prefix and tags for documentation grouping
router = APIRouter(prefix="/auditor", tags=["API Endpoints for auditor"])


@router.get(
    "/",
    description="API endpoint to get auditor's dashboard data",
    response_model=DashboardAnalysisResponse,
    summary="Get Auditor Dashboard Data",
    responses={
        200: {"description": "Dashboard data retrieved successfully"},
        401: {"description": "Unauthorized access"},
        500: {"description": "Internal server error"},
    },
)
def get_dashboard_data(
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    """
    Retrieve dashboard analytics for the authenticated auditor.

    This endpoint provides key metrics and analytics including:
    - Total assigned leads
    - Audited calls count
    - Flagged calls count
    - Recent activity
    - Historical audit trends

    Args:
        auditor (Auditor): The authenticated auditor object obtained from JWT token.
        service (AuditorService): The auditor service instance for business logic.

    Returns:

        DashboardAnalysisResponse: Contains dashboard metrics and analytics data.

    Raises:
        HTTPException:
            - 401: If user is not authenticated or not an auditor.
            - 500: If there's an internal server error during data retrieval.
    """
    return service.get_dashboard_data(auditor)


@router.get(
    "/calls",
    description="API endpoint to get all the calls belongs to the current auditor",
    response_model=CallsResponseSchema,
    summary="Get Auditor's Calls",
    responses={
        200: {"description": "Calls data retrieved successfully"},
        401: {"description": "Unauthorized access"},
        500: {"description": "Internal server error"},
    },
)
def get_calls(
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    """
    Retrieve all calls assigned to the authenticated auditor.

    This endpoint fetches a list of all calls assigned to the auditor along with
    call statistics (audited, unaudited, flagged counts) and detailed call information
    including AI analysis data.

    Args:
        auditor (Auditor): The authenticated auditor object obtained from JWT token.
        service (AuditorService): The auditor service instance for business logic.

    Returns:

        CallsResponseSchema: Contains list of calls and call statistics.

    Raises:
        HTTPException:
            - 401: If user is not authenticated or not an auditor.
            - 500: If there's an internal server error during data retrieval.
    """
    return service.get_calls(auditor)


@router.post(
    "/approve-audit",
    description="API endpoint to approve lead",
    response_model=BaseResponse,
    summary="Approve Audit",
    responses={
        200: {"description": "Audit approved successfully"},
        400: {"description": "Bad request - missing required parameters"},
        401: {"description": "Unauthorized access"},
        404: {"description": "Call not found for the auditor"},
        500: {"description": "Internal server error"},
    },
)
def approve_lead(
    call_id: str = Form(..., description="ID of the call to be approved"),
    comments: Optional[str] = Form(None, description="Optional comments for the audit"),
    flag: Optional[str] = Form(
        "normal", description="Whether to flag this audit, 'concern' or 'fatal'."
    ),
    flag_reasons: Optional[str] = Form(
        None, description="Reasons for flagging (if applicable)"
    ),
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    """
    Approve an audit for a specific call.

    This endpoint allows an auditor to approve an audit by providing feedback,
    flagging options, and comments. It updates both the Call and AuditReport records
    in the database.

    Args:
        call_id (str): The unique identifier of the call being approved.
        comments (Optional[str]): Optional textual comments from the auditor.
        is_flag (Optional[bool]): Whether this audit should be flagged.
        flag_reasons (Optional[str]): Reasons for flagging if is_flag is True.
        auditor (Auditor): The authenticated auditor performing the approval.
        service (AuditorService): The auditor service instance for business logic.

    Returns:

        BaseResponse: Confirmation of successful audit approval.

    Raises:
        HTTPException:
            - 400: If required call_id is missing.
            - 401: If user is not authenticated or not an auditor.
            - 404: If the specified call is not found for this auditor.
            - 500: If there's an internal server error during the approval process.
    """
    return service.approve_lead(
        {
            "call_id": call_id,
            "comments": comments,
            "flag": flag,
            "flag_reasons": flag_reasons,
        },
        auditor,
    )


@router.get(
    "/unflag",
    description="API endpoint to unflag any flagged audit report",
    response_model=BaseResponse,
    summary="Unflag Audit Report",
    responses={
        200: {"description": "Audit unflagged successfully"},
        401: {"description": "Unauthorized access"},
        500: {"description": "Internal server error"},
    },
)
async def unflag_flagged_audit(
    audit_id: str,
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    """
    Remove the flagged status from an audit report.

    This endpoint allows an auditor to remove the flagged status from a previously
    flagged audit report. Note that this operation may require specific permissions
    and is typically handled through the manager repository.

    Args:
        audit_id (str): The unique identifier of the audit report to unflag.
        auditor (Auditor): The authenticated auditor requesting the unflag operation.
        service (AuditorService): The auditor service instance for business logic.

    Returns:

        BaseResponse: Confirmation of successful unflag operation.

    Raises:
        HTTPException:
            - 401: If user is not authenticated or not an auditor.
            - 500: If there's an internal server error during the unflag process.
    """
    return service.unflag_flagged_audit(auditor, audit_id)


@router.post("/", description="Endpoint to add new auditor")
def add_auditor(
    manager_id: str,
    name: str,
    email: str,
    phone: str,
    password: str,
    service: AuditorService = Depends(get_auditor_service),
):
    return service.add_new_auditor(
        {
            "manager_id": manager_id,
            "name": name,
            "email": email,
            "phone": phone,
            "password": password,
        }
    )


@router.get(
    "/flagged-audits",
    description="API endpoint to get total flagged audits.",
    response_model=FlaggedAuditsResponse,
    summary="Get Flagged Audits",
    responses={
        200: {"description": "Flagged audits retrieved successfully"},
        401: {"description": "Unauthorized access"},
        500: {"description": "Internal server error"},
    },
)
def get_flagged_audits(
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    """
    Retrieve all audits flagged by the authenticated auditor.

    This endpoint fetches a list of all audit reports that have been flagged
    by the current auditor, including detailed information about each flagged audit.

    Args:
        auditor (Auditor): The authenticated auditor whose flagged audits are requested.
        service (AuditorService): The auditor service instance for business logic.

    Returns:

        FlaggedAuditsResponse: Contains list of flagged audit reports.

    Raises:
        HTTPException:
            - 401: If user is not authenticated or not an auditor.
            - 500: If there's an internal server error during data retrieval.
    """
    return service.get_flagged_audits(auditor)

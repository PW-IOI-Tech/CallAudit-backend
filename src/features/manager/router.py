"""
Manager API Router Module

This module defines the FastAPI routes (endpoints) specifically for manager-related
functionalities. It handles HTTP requests, delegates business logic to the
ManagerService, and returns appropriate responses.

All routes are prefixed with '/manager'.
"""

from typing import Optional
from fastapi import APIRouter, Response, Form, Depends
import logging

from dependency import get_current_user
from features.auditor.schemas import LoginSchema
from features.manager.schemas import (
    AuditorAnalyticsResponse,
    BaseResponse,
    CounsellorAnalysisResponse,
    FlaggedAuditsResponse,
    ManagerAnalyticsResponse,
    NewUserCreatedSchema,
)
from features.manager.dependency import get_manager_service
from features.manager.services import ManagerService
from models import Manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["API Endpoints for manager"])


@router.get(
    "/",
    description="API endpoint to get dashboard data for manager",
    response_model=ManagerAnalyticsResponse,
)
def get_dashboard_data_for_manager(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Get comprehensive dashboard analytics for the authenticated manager.

    Args:
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        ManagerAnalyticsResponse: Dashboard data including leads, audits, and flagged calls
    """
    return service.get_manager_analytics(manager)


@router.get(
    "/flagged-audits",
    description="API endpoint to get total flagged audits.",
    response_model=FlaggedAuditsResponse,
)
def get_flagged_audits(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Get all flagged audit reports for the authenticated manager.

    Args:
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        FlaggedAuditsResponse: List of all flagged audit reports
    """
    return service.get_flagged_audits(manager)


@router.get(
    "/auditors",
    description="Get auditors analysis under the manager",
    response_model=AuditorAnalyticsResponse,
)
def get_auditor_analytics(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Get analytics and statistics for all auditors under the authenticated manager.

    Args:
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        AuditorAnalyticsResponse: Auditor statistics and list of auditors
    """
    return service.get_auditors_analytics(manager)


@router.get(
    "/counsellor",
    description="Get counsellors analysis",
    response_model=CounsellorAnalysisResponse,
)
def get_counsellor_analysis(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Get analytics and statistics for all counsellors under the authenticated manager.

    Args:
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        CounsellorAnalysisResponse: Counsellor statistics and list of counsellors
    """
    return service.get_counsellor_analysis(manager)


@router.post(
    "/add",
    description="API endpoint to add new auditor or new counsellor",
    response_model=NewUserCreatedSchema,
)
def add_auditor_or_counsellor(
    role: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    auditor_id: Optional[str] = Form(None),
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Add a new auditor or counsellor to the system.

    Args:
        role (str): Role of the new user ('auditor' or 'counsellor')
        name (str): Name of the new user
        email (str): Email of the new user
        phone (str): Phone number of the new user
        auditor_id (Optional[str]): ID of the auditor (required for counsellor creation)
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        NewUserCreatedSchema: Response with success status and generated password (for auditors)
    """
    return service.add_new_user(role, name, email, phone, auditor_id, manager.id)


@router.post(
    "/deactivate",
    description="API endpoint to deactivate an auditor or counsellor",
    response_model=BaseResponse,
)
def delete_auditor_or_counsellor(
    role: str = Form(...),
    counsellor_id: Optional[str] = Form(None),
    auditor_id: Optional[str] = Form(None),
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Deactivate an auditor or counsellor in the system.

    Args:
        role (str): Role to deactivate ('auditor' or 'counsellor')
        counsellor_id (Optional[str]): ID of the counsellor to deactivate
        auditor_id (Optional[str]): ID of the auditor to deactivate
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        BaseResponse: Response with success status
    """
    return service.deactivate_auditor_or_counsellor(counsellor_id, auditor_id, role)


@router.post(
    "/activate",
    description="API endpoint to activate an auditor or counsellor",
    response_model=BaseResponse,
)
def activate_auditor_or_counsellor(
    role: str = Form(...),
    counsellor_id: Optional[str] = Form(None),
    auditor_id: Optional[str] = Form(None),
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Activate an auditor or counsellor in the system.

    Args:
        role (str): Role to activate ('auditor' or 'counsellor')
        counsellor_id (Optional[str]): ID of the counsellor to activate
        auditor_id (Optional[str]): ID of the auditor to activate
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        BaseResponse: Response with success status
    """
    return service.activate_auditor_or_counsellor(counsellor_id, auditor_id, role)


@router.get(
    "/unflag",
    description="API endpoint to unflag any flagged audit report",
    response_model=BaseResponse,
)
def unflag_flagged_audit(
    audit_id: str,
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    """Unflag a previously flagged audit report.

    Args:
        audit_id (str): ID of the audit report to unflag
        manager (Manager): Authenticated manager object from dependency injection
        service (ManagerService): Manager service instance from dependency injection

    Returns:

        BaseResponse: Response with success status
    """
    return service.unflag_flagged_audit(manager, audit_id)


@router.post(
    "/", description="Endpoint to add new manager", response_model=BaseResponse
)
def add_manager(
    name: str,
    email: str,
    phone: str,
    password: Optional[str] = None,
    service: ManagerService = Depends(get_manager_service),
):
    return service.add_new_manager(
        {"name": name, "email": email, "phone": phone, "password": password}
    )

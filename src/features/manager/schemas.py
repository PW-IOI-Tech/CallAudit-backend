"""
Manager Schema Models Module

This module defines Pydantic models (schemas) used for data validation and serialization
in the manager feature set. These schemas represent the structure of data exchanged
between the API endpoints, services, and clients for manager-related operations.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import List


class BaseResponse(BaseModel):
    """Base response model containing common fields for all API responses."""

    success: bool
    message: str


# manager analysis
class AuditFlaggedResponse(BaseModel):
    """Response model for flagged audit report information."""

    id: str
    call_id: str
    auditor_id: str
    auditor_name: str
    score: int
    comments: str
    flag_reason: str
    client_number: str
    counsellor_name: str
    updated_at: datetime
    created_at: datetime


class OneDayAuditData(BaseModel):
    """Response model for daily audit statistics."""

    date: datetime
    audited_calls: int


class ManagerAnalyticsResponse(BaseResponse):
    """Response model for manager analytics dashboard data."""

    total_assigned_leads: int
    total_audited_calls: int
    flagged_calls: int
    latest_flagged_audit: List[AuditFlaggedResponse]
    last_7_days_data: List[OneDayAuditData]


# Auditor analysis
class AuditorResponse(BaseModel):
    """Response model for individual auditor information and statistics."""

    id: str
    name: str
    is_active: bool
    total_assigned_leads: int
    total_audited_leads: int
    email: str


class AuditorAnalyticsResponse(BaseResponse):
    """Response model for auditor analytics and list of auditors."""

    number_of_auditors: int
    total_audited_calls: int
    auditors: List[AuditorResponse]


# counsellor analysis
class CounsellorResponse(BaseModel):
    """Response model for individual counsellor information and call statistics."""

    id: str
    name: str
    is_active: bool
    email: str
    total_calls: int


class CounsellorAnalysisResponse(BaseResponse):
    """Response model for counsellor analytics and list of counsellors."""

    total_counsellors: int
    total_calls_made: int
    counsellors: List[CounsellorResponse]


# FlaggedAuditsResponse
class FlaggedAuditsResponse(BaseResponse):
    """Response model for list of flagged audit reports."""

    flagged_audits: List[AuditFlaggedResponse]


class NewUserCreatedSchema(BaseResponse):
    """Response model for newly created user with generated password."""

    password: str

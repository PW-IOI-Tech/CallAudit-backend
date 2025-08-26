"""
Auditor Schema Models Module

This module defines Pydantic models (schemas) used for data validation and serialization
in the auditor feature set. These schemas represent the structure of data exchanged
between the API endpoints, services, and clients for auditor-related operations.
"""

from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from features.manager.schemas import OneDayAuditData


class User(BaseModel):
    """
    Schema representing basic user information.

    This model contains essential user details typically included in authentication
    responses and user context information.
    """

    id: str
    name: str
    email: str
    role: str


class LoginSchema(BaseModel):
    """
    Schema for auditor login response.

    Represents the response structure returned after a successful auditor login,
    including authentication status, user information, and success message.
    """

    success: bool
    message: str
    user: User


class BaseResponse(BaseModel):
    """
    Base schema for API responses.

    A common response structure used across various API endpoints to provide
    consistent feedback about the success status and descriptive messages.
    """

    success: bool
    message: str


class CallStats(BaseModel):
    """
    Schema for call statistics.

    Contains aggregated counts of different call statuses assigned to an auditor,
    used for dashboard metrics and reporting.
    """

    audited: int
    unaudited: int
    flagged: int


class CallResponse(BaseModel):
    """
    Schema for individual call information.

    Represents detailed information about a single call, including metadata,
    AI analysis results, and recording details.
    """

    id: str
    client_number: str
    duration: int
    tags: str
    ai_confidence: float
    recording_url: str
    summary: str
    sentiment_score: Optional[int] = None
    anomalies: str


class CallsResponseSchema(BaseResponse):
    """
    Schema for calls listing response.

    Extends BaseResponse to include a list of calls and their statistics,
    typically returned by endpoints that fetch call assignments for an auditor.
    """

    calls: List[CallResponse]
    call_stats: CallStats


class LatestCallResponse(BaseModel):
    """
    Schema for recent call information.

    Represents minimal information about recently audited calls, used for
    displaying recent activity in dashboards.
    """

    id: str
    call_start: datetime
    client_number: str


class DashboardAnalysisResponse(BaseResponse):
    """
    Schema for auditor dashboard data response.

    Comprehensive response schema containing all the metrics and analytics
    displayed on an auditor's dashboard, including call statistics, recent activity,
    and historical trends.
    """

    total_assigned_leads: int
    total_audited_calls: int
    flagged_calls: int
    latest_calls: List[LatestCallResponse]
    last_7_days_data: List[OneDayAuditData]

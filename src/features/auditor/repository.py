"""
Auditor Repository Module

This module contains the `AuditorRepository` class, which provides an interface for
interacting with the database for auditor-related operations. It encapsulates
data access logic for auditors, their assigned calls, audit reports, and related statistics.
"""

from passlib.context import CryptContext
from datetime import datetime, timedelta
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Date, cast, func
from typing import Any, Dict, List, Optional
from features.auditor.schemas import CallResponse, CallStats, LatestCallResponse
from features.manager.schemas import AuditFlaggedResponse, OneDayAuditData
from models import (
    AuditReport,
    Auditor,
    Call,
    CallAnalysis,
    CallFlag,
    Counsellor,
    Manager,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, desc

logger = logging.getLogger(__name__)


class AuditorRepository:
    """
    Repository class for handling database operations related to auditors.

    This class provides methods to query and update data in the database
    specifically for auditor functionalities such as fetching calls,
    statistics, dashboard data, and managing audit reports.
    """

    def __init__(self, db: Session):
        """
        Initializes the AuditorRepository with a database session.

        Args:
            db (Session): An active SQLAlchemy database session.
        """
        self.db = db

    # Reading methods

    def get_auditor(
        self, id: Optional[str] = None, email: Optional[str] = None
    ) -> Auditor | None:
        """
        Retrieves an auditor by ID or email.

        Fetches a single auditor record from the database based on either
        the provided ID or email address. If both are provided, ID takes precedence.

        Args:
            id (Optional[str]): The unique identifier of the auditor.
            email (Optional[str]): The email address of the auditor.

        Returns:

            Auditor | None: The Auditor object if found, otherwise None.

        Example:
            >>> auditor = repo.get_auditor(email="auditor@example.com")
            >>> if auditor:
            ...     print(f"Auditor found: {auditor.name}")
        """
        try:
            if id:
                return self.db.query(Auditor).filter(Auditor.id == id).first()
            return self.db.query(Auditor).filter(Auditor.email == email).first()
        except Exception as e:
            logger.error(f"Failed to get auditor, error: {str(e)}")
            return None

    def get_calls(self, auditor_id: str) -> List[CallResponse] | None:
        """
        Retrieves all calls assigned to a specific auditor.

        Fetches call details along with analysis data, ordered by AI confidence score.
        This includes client information, call metadata, and AI-generated analysis.

        Args:
            auditor_id (str): The unique identifier of the auditor.

        Returns:

            List[CallResponse] | None: A list of CallResponse objects containing
                                       call details, or None if an error occurs.

        Example:
            >>> calls = repo.get_calls("auditor-123")
            >>> for call in calls:
            ...     print(f"Call ID: {call.id}, Duration: {call.duration}")
        """
        try:
            results = (
                self.db.query(
                    Call.id,
                    Call.client_number,
                    Call.duration,
                    Call.tags,
                    CallAnalysis.ai_confidence,
                    Call.recording_url,
                    CallAnalysis.summary,
                    CallAnalysis.sentiment_score,
                    CallAnalysis.anomalies,
                )
                .outerjoin(CallAnalysis, CallAnalysis.call_id == Call.id)
                .filter(Call.auditor_id == auditor_id)
                .order_by(CallAnalysis.ai_confidence.asc())
                .all()
            )
            final_response: List[CallResponse] = []
            for result in results:
                final_response.append(
                    CallResponse(
                        id=result.id,
                        client_number=result.client_number,
                        duration=result.duration,
                        tags=result.tags,
                        ai_confidence=result.ai_confidence or 0,
                        recording_url=result.recording_url,
                        summary=result.summary or "no_summary",
                        sentiment_score=int(result.sentiment_score or 0),
                        anomalies=result.anomalies or "no_anomalies",
                    )
                )
            return final_response
        except Exception as e:
            logger.error(f"Failed to fetch calls from database, error: {str(e)}")
            return None

    def get_call_stats(self, auditor_id: str) -> Dict[str, Any] | None:
        """
        Retrieves call statistics for a specific auditor.

        Calculates the count of audited, unaudited, and flagged calls assigned
        to the auditor using database aggregation functions.

        Args:
            auditor_id (str): The unique identifier of the auditor.

        Returns:

            Dict[str, Any] | None: A dictionary containing statistics with keys
                                  'audited', 'unaudited', and 'flagged', or None
                                  if an error occurs.

        Example:
            >>> stats = repo.get_call_stats("auditor-123")
            >>> print(f"Audited calls: {stats['audited']}")
            >>> print(f"Flagged calls: {stats['flagged']}")
        """
        try:
            stats = (
                self.db.query(
                    func.count().filter(Call.is_audited.is_(True)).label("audited"),
                    func.count().filter(Call.is_audited.is_(False)).label("unaudited"),
                    func.count().filter(Call.flag != CallFlag.NORMAL).label("flagged"),
                )
                .filter(Call.auditor_id == auditor_id)
                .one()
            )
            return {
                "audited": stats.audited,
                "unaudited": stats.unaudited,
                "flagged": stats.flagged,
            }
        except Exception as e:
            logger.error(f"Failed to fetch stats from database, error: {str(e)}")
            return None

    def get_latest_calls(self, auditor_id: str) -> List[LatestCallResponse]:
        """
        Retrieves the most recently audited calls for an auditor.

        Fetches basic information about the latest calls that have been marked
        as audited, ordered by call start time in descending order.

        Args:

            auditor_id (str): The unique identifier of the auditor.

        Returns:
            List[LatestCallResponse]: A list of LatestCallResponse objects
                                    containing recent call information, or None
                                    if an error occurs.

        Example:
            >>> latest_calls = repo.get_latest_calls("auditor-123")
            >>> for call in latest_calls:
            ...     print(f"Recent call: {call.client_number} at {call.call_start}")
        """
        try:
            results = (
                self.db.query(
                    Call.id,
                    Call.call_start,
                    Call.client_number,
                )
                .filter(Call.auditor_id == auditor_id, Call.is_audited.is_(True))
                .order_by(Call.call_start.desc())
                .all()
            )
            final_response: List[LatestCallResponse] = []
            for result in results:
                final_response.append(
                    LatestCallResponse(
                        id=result.id,
                        call_start=result.call_start,
                        client_number=result.client_number,
                    )
                )
            return final_response
        except Exception as e:
            logger.error(f"Failed to fetch latest calls from database, error: {str(e)}")
            return None

    def get_last_7_days_data(self, auditor_id: str) -> List[OneDayAuditData] | None:
        """
        Retrieves audit completion data for the last 7 days.

        Generates a time series of daily audit counts for the past week,
        including days with zero audits to ensure complete data representation.

        Args:
            auditor_id (str): The unique identifier of the auditor.

        Returns:

            List[OneDayAuditData] | None: A list of OneDayAuditData objects
                                        representing daily audit counts, or None
                                        if an error occurs.

        Example:
            >>> weekly_data = repo.get_last_7_days_data("auditor-123")
            >>> for day_data in weekly_data:
            ...     print(f"Date: {day_data.date}, Audits: {day_data.audited_calls}")
        """
        try:
            # Step 1: Generate last 7 days
            today = datetime.utcnow().date()
            date_range = [
                (today - timedelta(days=i)) for i in reversed(range(7))
            ]  # oldest to newest
            # Step 2: Fetch counts from DB
            raw_results = (
                self.db.query(
                    cast(AuditReport.created_at, Date).label("date"),
                    func.count(AuditReport.id).label("completed_audits"),
                )
                .filter(
                    AuditReport.auditor_id == auditor_id,
                    cast(AuditReport.created_at, Date) >= date_range[0],
                )
                .group_by(cast(AuditReport.created_at, Date))
                .all()
            )
            # Step 3: Build dict from raw results
            audit_dict = {row.date: row.completed_audits for row in raw_results}
            # Step 4: Fill missing dates with 0
            final_result = [
                OneDayAuditData(
                    date=date.isoformat(), audited_calls=audit_dict.get(date, 0)
                )
                for date in date_range
            ]
            return final_result
        except Exception as e:
            logger.error(f"Failed to fetch latest calls from database, error: {str(e)}")
            return None

    def approve_lead_and_update_db(self, data: Dict[str, Any], auditor_id: str):
        """
        Approves a lead and updates related database records.

        Processes an audit approval by updating the Call record and either
        creating or updating the corresponding AuditReport record. This includes
        handling flagged status and associated comments/reasons.

        Args:
            data (Dict[str, Any]): A dictionary containing approval data including:
                                 - 'call_id': The ID of the call being approved
                                 - 'comments': Optional comments from the auditor
                                 - 'is_flag': Optional flag status
                                 - 'flag_reasons': Optional reasons for flagging
            auditor_id (str): The ID of the auditor performing the approval.

        Raises:

            HTTPException:
                - 400 Bad Request: If required 'call_id' is missing from data.
                - 404 Not Found: If the specified call is not found for this auditor.
                - 500 Internal Server Error: If a database error occurs during update.

        Example:
            >>> approval_data = {
            ...     "call_id": "call-456",
            ...     "comments": "Good call quality",
            ...     "is_flag": False
            ... }
            >>> repo.approve_lead_and_update_db(approval_data, "auditor-123")
        """
        try:
            call_id = data.get("call_id")
            comments = data.get("comments")
            flag = data.get("flag", "normal")
            flag_reasons = data.get("flag_reasons")

            if flag != "NORMAL" and flag != "CONCERN" and flag != "FATAL":
                logger.error("Flag is not valid, it should be NORMAL, CONCERN or FATAL")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Flag is not valid, it should be NORMAL, CONCERN or FATAL",
                )

            if not call_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Call ID is required.",
                )
            # Update Call table
            call = (
                self.db.query(Call)
                .filter(Call.id == call_id, Call.auditor_id == auditor_id)
                .first()
            )
            if not call:
                logger.error("Call not found for the given auditor.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Call not found for the given auditor.",
                )
            call.is_audited = True  # always mark as audited
            # Update flag if is_flag is not None
            if flag is not None:
                call.flag = CallFlag(flag)
            # Update AuditReport
            audit_report = (
                self.db.query(AuditReport)
                .filter(
                    AuditReport.call_id == call_id, AuditReport.auditor_id == auditor_id
                )
                .first()
            )
            if audit_report:
                # Update existing report
                if comments is not None:
                    audit_report.comments = comments
                if flag is not None:
                    audit_report.flag = CallFlag(flag)
                if flag_reasons is not None:
                    audit_report.flag_reason = flag_reasons
                audit_report.updated_at = datetime.utcnow()
            else:
                # Create new report
                logger.error("Audit report not found creating new one.")
                new_report = AuditReport(
                    call_id=call_id,
                    auditor_id=auditor_id,
                    manager_id=call.manager_id,
                    score=call.audit_score or 0,  # default to 0 if not set
                    comments=comments,
                    flag=flag,
                    flag_reason=flag_reasons,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(new_report)
            # Commit changes
            self.db.commit()
            logger.info("Database update succesfull")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"SQLAlchemy error occurred: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while updating call and audit report.",
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve lead and update db, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while approving lead.",
            )

    def get_all_latest_flagged_audit(
        self, auditor_id: str
    ) -> List[AuditFlaggedResponse] | None:
        """
        Retrieves all flagged audits for a specific auditor.

        Fetches detailed information about all calls that have been flagged
        by the auditor, including audit report details, counsellor information,
        and flag reasons. Results are ordered by update time (most recent first).

        Args:
            auditor_id (str): The unique identifier of the auditor.

        Returns:

            List[AuditFlaggedResponse] | None: A list of AuditFlaggedResponse objects
                                             containing flagged audit details, or None
                                             if an error occurs.

        Example:
            >>> flagged_audits = repo.get_all_latest_flagged_audit("auditor-123")
            >>> for audit in flagged_audits:
            ...     print(f"Flagged audit {audit.id}: {audit.flag_reason}")
        """
        try:
            logger.info(
                f"Getting all latest flagged audits for auditor with id: {auditor_id}"
            )
            flagged_calls_query = (
                self.db.query(
                    AuditReport.id,
                    AuditReport.call_id,
                    AuditReport.auditor_id,
                    Auditor.name.label("auditor_name"),
                    AuditReport.score,
                    AuditReport.comments,
                    AuditReport.flag_reason,
                    AuditReport.updated_at,
                    AuditReport.created_at,
                    Call.client_number,
                    Counsellor.name.label("counsellor_name"),
                )
                .join(Auditor, AuditReport.auditor_id == Auditor.id)
                .join(Call, AuditReport.call_id == Call.id)
                .join(Counsellor, Call.counsellor_id == Counsellor.id)
                .filter(
                    and_(
                        AuditReport.auditor_id == auditor_id,
                        AuditReport.flag != CallFlag.NORMAL,
                    )
                )
                .order_by(desc(AuditReport.updated_at))
            )
            results = flagged_calls_query.all()
            final_response: List[AuditFlaggedResponse] = []
            if results:
                for result in results:
                    # print(result.updated_at)
                    final_response.append(
                        AuditFlaggedResponse(
                            id=result.id,
                            call_id=result.call_id,
                            auditor_id=result.auditor_id,
                            auditor_name=result.auditor_name,
                            score=int(result.score) if result.score is not None else 0,
                            comments=result.comments,
                            flag_reason=(
                                result.flag_reason
                                if result.flag_reason is not None
                                else ""
                            ),
                            updated_at=result.updated_at,
                            created_at=result.created_at,
                            client_number=result.client_number,
                            counsellor_name=result.counsellor_name,
                        )
                    )
            return final_response
        except Exception as e:
            logger.error(
                f"Failed to retrieve all latest flagged audit from database, error: {str(e)}"
            )
            return None

    def create_new_auditor(self, auditor_data: Dict[str, any]):
        try:
            # hash the password and update the dictionary
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            auditor_data["password"] = pwd_context.hash(auditor_data["password"])

            auditor = Auditor(**auditor_data)

            self.db.add(auditor)
            self.db.commit()
            self.db.refresh(auditor)
            logger.info("Succesfully created new auditor in database")
            return True

        except Exception as e:
            logger.error(
                f"Internal server error occurred while creating new auditor, error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while creating new auditor",
            )

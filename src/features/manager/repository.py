"""
Manager Repository Module

This module provides a comprehensive repository pattern implementation for managing
business operations related to managers, auditors, counsellors, and their associated
calls and audit reports. It serves as the data access layer for the manager feature,
encapsulating all database operations and providing a clean interface for the service layer.

Key Features:
- Manager data retrieval and validation
- Auditor management (creation, activation, deactivation)
- Counsellor management (creation, activation, deactivation)
- Call and audit report analytics
- Flagged audit management
- Statistical reporting for dashboard views

Database Models Used:
- Manager: Represents management users
- Auditor: Users responsible for call quality auditing
- Counsellor: Users who handle customer calls
- Call: Individual call records
- AuditReport: Quality audit results for calls
- Lead: Customer lead information

Dependencies:
- FastAPI: For HTTP exception handling
- SQLAlchemy: For database ORM operations
- Pydantic: For response schema validation (via imported schemas)

Author: Shoyeb Ansari
Last Modified: 25-07-2025
Version: 0.1.0
"""

from passlib.context import CryptContext
import logging
from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select, func, cast, Date
from sqlalchemy.orm import Session
from typing import Optional
from models import CallFlag, Counsellor, Manager, Lead, AuditReport, Call, Auditor
from features.manager.schemas import (
    AuditFlaggedResponse,
    AuditorResponse,
    CounsellorResponse,
    OneDayAuditData,
)
from typing import List, Dict, Any
from sqlalchemy import func
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ManagerRepository:
    """
    Repository class for handling manager-related database operations.

    This class implements the Repository pattern to encapsulate all database access
    logic for manager-related entities. It provides a clean interface for CRUD operations
    and complex queries involving managers, auditors, counsellors, calls, and audit reports.

    The repository handles:
    - Manager authentication and retrieval
    - Statistical data aggregation for dashboards
    - Auditor and counsellor lifecycle management
    - Call and audit report queries with filtering
    - Flagged audit management workflows

    Attributes:
        db (Session): SQLAlchemy database session for executing queries

    Example:
        >>> db_session = get_db_session()
        >>> manager_repo = ManagerRepository(db_session)
        >>> manager = manager_repo.get_manager(email="manager@example.com")
        >>> auditors = manager_repo.get_auditors(manager.id)
    """

    def __init__(self, db: Session):
        """
        Initialize the ManagerRepository with a database session.

        Args:
            db (Session): SQLAlchemy database session for executing queries.
                         This session should be properly configured with the
                         database connection and transaction management.

        Note:
            The database session should be managed by the calling code.
            This repository does not handle session lifecycle.
        """
        self.db = db

    # Reading methods

    def get_manager(
        self, id: Optional[str] = None, email: Optional[str] = None
    ) -> Manager | None:
        """
        Retrieve a manager by ID or email address.

        This method provides flexible manager lookup by either unique identifier
        or email address. It's commonly used for authentication and authorization.

        Args:
            id (Optional[str]): Unique manager identifier. Takes precedence if provided.
            email (Optional[str]): Manager's email address. Used if id is not provided.

        Returns:
            Manager | None: Manager instance if found, None if not found or on error.

        Note:
            If both id and email are provided, id takes precedence.
            If neither is provided, returns None.

        Example:
            >>> manager = repo.get_manager(email="john.doe@company.com")
            >>> manager = repo.get_manager(id="mgr_123")
        """
        try:
            if id:
                return self.db.query(Manager).filter(Manager.id == id).first()
            return self.db.query(Manager).filter(Manager.email == email).first()
        except Exception as e:
            logger.error(f"Failed to get auditor, error: {str(e)}")
            return None

    def get_all_leads(self, manager_id: str) -> int:
        """
        Get the total count of calls (leads) for a specific manager.

        This method counts all calls associated with a manager, regardless of
        their status (audited, flagged, etc.). Used for dashboard statistics.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            int: Total count of calls. Returns 0 if no calls found or on error.

        Note:
            In this context, "leads" refers to calls, as each call represents
            a potential business lead.

        Example:
            >>> total_calls = repo.get_all_leads("mgr_123")
            >>> print(f"Manager has {total_calls} total calls")
        """
        try:
            logger.info(f"Getting all leads for manager with id: {manager_id}")
            count = (
                self.db.query(func.count(Call.id))
                .filter(Call.manager_id == manager_id)
                .scalar()
            )
            return count
        except Exception as e:
            logger.error(f"Failed to get all leads, error: {str(e)}")
            return None

    def get_all_audit(self, manager_id: str) -> int:
        """
        Get the total count of distinct audit reports for a manager.

        This method counts unique audit reports created for calls under a manager's
        supervision. Uses DISTINCT to avoid counting duplicate reports.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            int: Total count of distinct audit reports. Returns 0 if none found or on error.

        Example:
            >>> audit_count = repo.get_all_audit("mgr_123")
            >>> print(f"Manager has {audit_count} audited calls")
        """
        try:
            logger.info(f"Getting all audits for manager with id: {manager_id}")
            reports = (
                self.db.query(func.count(func.distinct(AuditReport.id)))
                .filter(AuditReport.manager_id == manager_id)
                .scalar()
            )
            return reports
        except Exception as e:
            logger.error(f"Failed to get total audited calls, error: {str(e)}")
            return None

    def get_all_flagged_call(self, manager_id: str) -> int:
        """
        Get the total count of flagged calls for a manager.

        Flagged calls are those that have been marked for attention due to
        quality issues or policy violations during the audit process.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            int: Total count of flagged calls. Returns 0 if none found or on error.

        Example:
            >>> flagged_count = repo.get_all_flagged_call("mgr_123")
            >>> print(f"Manager has {flagged_count} flagged calls requiring attention")
        """
        try:
            logger.info(f"Getting all flagged calls for manager with id: {manager_id}")
            count = (
                self.db.query(func.count(func.distinct(Call.id)))
                .filter(Call.manager_id == manager_id, Call.flag != CallFlag.NORMAL)
                .scalar()
            )
            return count
        except Exception as e:
            logger.error(f"Failed to get total audited calls, error: {str(e)}")
            return None

    def get_all_latest_flagged_audit(
        self, manager_id: str
    ) -> List[AuditFlaggedResponse] | None:
        """
        Retrieve all latest flagged audit reports for a manager with detailed information.

        This method returns comprehensive information about flagged audits, including
        auditor details, call information, and flagging reasons. Results are ordered
        by most recent updates first.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            List[AuditFlaggedResponse] | None: List of detailed flagged audit responses
                                               ordered by update time (newest first).
                                               Returns None on error.

        Note:
            This method performs multiple JOINs to gather comprehensive information.
            Consider pagination for managers with large numbers of flagged audits.

        Example:
            >>> flagged_audits = repo.get_all_latest_flagged_audit("mgr_123")
            >>> for audit in flagged_audits:
            ...     print(f"Call {audit.call_id} flagged by {audit.auditor_name}")
        """
        try:
            logger.info(
                f"Getting all latest flagged audits for manager with id: {manager_id}"
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
                        AuditReport.manager_id == manager_id,
                        AuditReport.flag != CallFlag.NORMAL,
                    )
                )
                .order_by(desc(AuditReport.updated_at))
            )
            results = flagged_calls_query.all()
            final_response: List[AuditFlaggedResponse] = []
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
                            result.flag_reason if result.flag_reason is not None else ""
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

    def get_auditor_and_audited_call_counts(self, manager_id: str):
        """
        Get aggregate counts of auditors and audited calls for a manager.

        This method provides key metrics for manager dashboards, showing the total
        number of auditors under management and the total calls that have been audited.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            Dict[str, int] | None: Dictionary with keys:
                - 'number_of_auditors': Count of distinct auditors
                - 'total_audited_calls': Count of calls that have been audited
                Returns None on error.

        Example:
            >>> counts = repo.get_auditor_and_audited_call_counts("mgr_123")
            >>> print(f"Manager oversees {counts['number_of_auditors']} auditors")
            >>> print(f"Total audited calls: {counts['total_audited_calls']}")
        """
        try:
            logger.info("Getting auditor and audited calls count")
            result = (
                self.db.query(
                    func.count(func.distinct(Auditor.id)).label("number_of_auditors"),
                    func.count(func.distinct(Call.id))
                    .filter(Call.is_audited.is_(True))
                    .label("total_audited_calls"),
                )
                .join(Call, Auditor.id == Call.auditor_id, isouter=True)
                .filter(Auditor.manager_id == manager_id)
                .one()
            )
            return {
                "number_of_auditors": result.number_of_auditors,
                "total_audited_calls": result.total_audited_calls,
            }
        except Exception as e:
            logger.error(f"Failed to get auditor and call counts, Error: {e}")
            return None

    def get_last_7_days_audited_calls(
        self, manager_id: str
    ) -> Optional[List[OneDayAuditData]]:
        """
        Get daily audited call counts for the last 7 days for trend analysis.

        This method provides time-series data for dashboard charts showing audit
        activity over the past week. It ensures all 7 days are represented,
        filling in zero counts for days with no audit activity.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            Optional[List[OneDayAuditData]]: List of daily audit data covering the
                                           last 7 days (including today), ordered
                                           chronologically. Returns None on error.

        Note:
            - Uses UTC date calculations for consistency
            - Includes days with zero audit activity for complete time series
            - Results are ordered from oldest to newest (7 days ago to today)

        Example:
            >>> trend_data = repo.get_last_7_days_audited_calls("mgr_123")
            >>> for day_data in trend_data:
            ...     print(f"{day_data.date}: {day_data.audited_calls} audits")
        """
        try:
            logger.info("Getting last 7 days audited data")
            today = datetime.utcnow().date()
            date_range = [
                (today - timedelta(days=i)) for i in reversed(range(7))
            ]  # 7 days including today
            # Query for actual audit counts
            results = (
                self.db.query(
                    cast(Call.call_start, Date).label("date"),
                    func.count(Call.id).label("audited_calls"),
                )
                .filter(
                    Call.manager_id == manager_id,
                    Call.is_audited.is_(True),
                    cast(Call.call_start, Date) >= date_range[0],
                )
                .group_by(cast(Call.call_start, Date))
                .order_by(cast(Call.call_start, Date))
                .all()
            )
            # Build a lookup dictionary
            result_map = {row.date: row.audited_calls for row in results}
            # Merge with fixed 7-day range
            final_response = [
                OneDayAuditData(date=day, audited_calls=result_map.get(day, 0))
                for day in date_range
            ]
            return final_response
        except Exception as e:
            logger.error(f"Failed to get auditor and call counts, Error: {e}")
            return None

    def get_auditors(self, manager_id: str) -> List[AuditorResponse] | None:
        """
        Retrieve all auditors under a manager with their performance statistics.

        This method returns comprehensive information about each auditor including
        their assignment load and audit completion statistics for performance tracking.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            List[AuditorResponse] | None: List of auditor details with statistics:
                - Basic auditor information (id, name, status)
                - Total assigned leads count
                - Total completed audits count
                Returns None on error.

        Example:
            >>> auditors = repo.get_auditors("mgr_123")
            >>> for auditor in auditors:
            ...     efficiency = auditor.total_audited_leads / auditor.total_assigned_leads
            ...     print(f"{auditor.name}: {efficiency:.2%} completion rate")
        """

        try:
            logger.info("Getting auditors")
            results = (
                self.db.query(
                    Auditor.id,
                    Auditor.name,
                    Auditor.is_active,
                    Auditor.email,
                    func.count(func.distinct(Lead.id)).label("total_assigned_leads"),
                    func.count(func.distinct(AuditReport.id)).label(
                        "total_audited_leads"
                    ),
                )
                .outerjoin(Lead, Lead.auditor_id == Auditor.id)
                .outerjoin(AuditReport, AuditReport.auditor_id == Auditor.id)
                .filter(Auditor.manager_id == manager_id)
                .group_by(Auditor.id, Auditor.name)
                .all()
            )
            final_response: List[AuditorResponse] = []
            for result in results:
                final_response.append(
                    AuditorResponse(
                        id=result.id,
                        name=result.name,
                        is_active=result.is_active,
                        total_assigned_leads=result.total_assigned_leads,
                        total_audited_leads=result.total_audited_leads,
                        email=result.email,
                    )
                )
            return final_response
        except Exception as e:
            print(f"Failed to get auditor and call counts, Error: {e}")
            return None

    def get_counsellor_data(self, manager_id: str) -> Dict[str, Any] | None:
        """Get counsellor data including total counsellors and calls made.

        Args:
            manager_id (str): ID of the manager

        Returns:
            Dict[str, Any] | None: Dictionary containing 'total_counsellors' and 'total_calls_made' counts, or None if an error occurs
        """
        try:
            logger.info("Getting counsellor data...")
            result = self.db.query(
                select(func.count())
                .select_from(Counsellor)
                .filter(Counsellor.manager_id == manager_id)
                .scalar_subquery()
                .label("total_counsellors"),
                select(func.count())
                .select_from(Call)
                .filter(Call.manager_id == manager_id)
                .scalar_subquery()
                .label("total_calls_made"),
            ).one()
            return {
                "total_counsellors": result.total_counsellors,
                "total_calls_made": result.total_calls_made,
            }
        except Exception as e:
            logger.error(f"Failed to get counsellor analysis, Error: {e}")
            return None

    def get_counsellors(self, manager_id: str) -> List[CounsellorResponse] | None:
        """Get all counsellors for a manager with their call statistics.

        Args:
            manager_id (str): ID of the manager

        Returns:
            List[CounsellorResponse] | None: List of counsellor responses with call statistics, or None if an error occurs
        """
        try:
            logger.info("Getting counsellors...")
            counsellors = (
                self.db.query(
                    Counsellor.id,
                    Counsellor.name,
                    Counsellor.email,
                    Counsellor.is_active,
                    func.count(Call.id).label("total_calls"),
                )
                .outerjoin(Call, Call.counsellor_id == Counsellor.id)
                .filter(Counsellor.manager_id == manager_id)
                .group_by(Counsellor.id, Counsellor.name, Counsellor.email)
                .all()
            )
            final_response: List[CounsellorResponse] = []
            for counsellor in counsellors:
                final_response.append(
                    CounsellorResponse(
                        id=counsellor.id,
                        name=counsellor.name,
                        is_active=counsellor.is_active,
                        email=counsellor.email,
                        total_calls=counsellor.total_calls,
                    )
                )
            return final_response
        except Exception as e:
            print(f"Failed to get counsellors, Error: {e}")
            return None

    # Creation methods

    def create_auditor(self, auditor_data) -> bool:
        """
        Retrieve all auditors under a manager with their performance statistics.

        This method returns comprehensive information about each auditor including
        their assignment load and audit completion statistics for performance tracking.

        Args:
            manager_id (str): Unique identifier of the manager

        Returns:
            List[AuditorResponse] | None: List of auditor details with statistics:
                - Basic auditor information (id, name, status)
                - Total assigned leads count
                - Total completed audits count
                Returns None on error.

        Example:
            >>> auditors = repo.get_auditors("mgr_123")
            >>> for auditor in auditors:
            ...     efficiency = auditor.total_audited_leads / auditor.total_assigned_leads
            ...     print(f"{auditor.name}: {efficiency:.2%} completion rate")
        """

        try:
            auditor = Auditor(**auditor_data)
            self.db.add(auditor)
            self.db.commit()
            self.db.refresh(auditor)
            logger.info("Succesfully created new auditor in database")
            return True
        except Exception as e:
            logger.error(f"Failed to create new auditor in database, error: {str(e)}")
            return False

    def create_counsellor(self, counsellor_data) -> bool:
        """
        Create a new counsellor.

        Args:
            counsellor_data (dict): Data for creating the new counsellor

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            counsellor = Counsellor(**counsellor_data)
            self.db.add(counsellor)
            self.db.commit()
            self.db.refresh(counsellor)
            logger.info("Succesfully created new counsellor in database")
            return True
        except Exception as e:
            logger.error(
                f"Failed to create new counsellor in database, error: {str(e)}"
            )
            return False

    # Deactivation methods

    def deactivate_auditor(self, auditor_id: str) -> bool:
        """Deactivate an auditor.

        Args:
            auditor_id (str): ID of the auditor to deactivate

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            auditor = self.db.query(Auditor).filter_by(id=auditor_id).first()
            if not auditor:
                logger.warning(f"Auditor with ID {auditor_id} does not exist.")
                return False
            logger.debug(
                f"Deactivating auditor: {auditor.id} (current status: {auditor.is_active})"
            )
            auditor.is_active = False
            auditor.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(auditor)
            logger.info(f"Successfully deactivated auditor with ID {auditor_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate auditor, error: {str(e)}")
            return False

    def deactivate_counsellor(self, counsellor_id: str) -> bool:
        """Deactivate a counsellor.

        Args:
            counsellor_id (str): ID of the counsellor to deactivate

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            counsellor = self.db.query(Counsellor).filter_by(id=counsellor_id).first()
            if not counsellor:
                logger.warning(f"Counsellor with ID {counsellor_id} does not exist.")
                return False
            logger.debug(
                f"Deactivating counsellor: {counsellor.id} (current status: {counsellor.is_active})"
            )
            counsellor.updated_at = datetime.utcnow()
            counsellor.is_active = False
            self.db.commit()
            self.db.refresh(counsellor)
            logger.info(f"Successfully deactivated counsellor with ID {counsellor_id}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to deactivate counsellor from database, error: {str(e)}"
            )
            return False

    # Activation methods

    def activate_auditor(self, auditor_id: str) -> bool:
        """Activate an auditor.

        Args:
            auditor_id (str): ID of the auditor to activate

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            auditor = self.db.query(Auditor).filter_by(id=auditor_id).first()
            if not auditor:
                logger.warning(f"Auditor with ID {auditor_id} does not exist.")
                return False
            logger.debug(
                f"Activating auditor: {auditor.id} (current status: {auditor.is_active})"
            )
            auditor.is_active = True
            auditor.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(auditor)
            logger.info(f"Successfully activated auditor with ID {auditor_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate auditor, error: {str(e)}")
            return False

    def activate_counsellor(self, counsellor_id: str) -> bool:
        """Activate a counsellor.

        Args:
            counsellor_id (str): ID of the counsellor to activate

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            counsellor = self.db.query(Counsellor).filter_by(id=counsellor_id).first()
            if not counsellor:
                logger.warning(f"Counsellor with ID {counsellor_id} does not exist.")
                return False
            logger.debug(
                f"Activating counsellor: {counsellor.id} (current status: {counsellor.is_active})"
            )
            counsellor.updated_at = datetime.utcnow()
            counsellor.is_active = True
            self.db.commit()
            self.db.refresh(counsellor)
            logger.info(f"Successfully activated counsellor with ID {counsellor_id}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to activate counsellor from database, error: {str(e)}"
            )
            return False

    # Flagging methods

    def unflag_audit(self, audit_id) -> bool:
        """Unflag an audit report and its associated call.

        Args:
            audit_id (str): ID of the audit report to unflag

        Returns:
            bool: True if successful, False otherwise

        Raises:
            HTTPException: If audit report or call is not found
        """
        try:
            report = (
                self.db.query(AuditReport).filter(AuditReport.id == audit_id).first()
            )
            if not report:
                logger.error("No audit report found for given call id")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No audit report found with given audit id",
                )
            # Unflag audit
            report.flag = CallFlag.NORMAL
            # replace reason
            report.flag_reason = ""
            report.updated_at = datetime.utcnow()
            # Sync with Call
            call = self.db.query(Call).filter(Call.id == report.call_id).first()
            if not call:
                logger.error("No call found with given audit id")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No call found  with given audit id",
                )
            call.flag = CallFlag.NORMAL

            call.updated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Succesfully unflagged audit with audit id: {audit_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unflag audit, error: {str(e)}")
            return False

    def create_new_manager(self, manager_data: Dict[str, any]):
        try:
            # hash the password and update the dictionary
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            manager_data["password"] = pwd_context.hash(manager_data["password"])

            manager = Manager(**manager_data)

            self.db.add(manager)
            self.db.commit()
            self.db.refresh(manager)
            logger.info("Succesfully created new manager in database")
            return True

        except Exception as e:
            logger.error(
                f"Internal server error occurred while creating new manager, error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while creating new manager",
            )

from typing import Dict

from fastapi import HTTPException, status
from models import Call, CallAnalysis, Counsellor
from sqlalchemy.orm import Session
import logging
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class CounsellorRepository:
    """
    Repository class for handling database operations related to Counsellors, Calls, and CallAnalyses.

    This class provides an abstraction layer over the SQLAlchemy ORM to perform
    Create, Read, Update, and Delete (CRUD) operations for counsellor-related
    entities. It manages the lifecycle of call records and their associated AI analysis data.
    """

    def __init__(self, db: Session):
        """
        Initializes the CounsellorRepository with a SQLAlchemy database session.

        Args:
            db (Session): An active SQLAlchemy database session used for all database interactions.
        """
        self.db = db

    def create_call(self, call_data: dict) -> str:
        """
        Creates a new call record in the database.

        This method first verifies the existence of the associated counsellor.
        If the counsellor exists, it automatically populates the `auditor_id`
        and `manager_id` fields from the counsellor's record before creating the call.
        It returns the unique identifier of the newly created call record.

        Args:
            call_data (dict): A dictionary containing the data for the new call.
                            Must include 'counsellor_id'. Other expected keys are
                            'call_start', 'call_end', 'duration', 'call_type',
                            'client_number', and 'tags'.

        Returns:

            str: The unique identifier (ID) of the newly created Call record.
                 Returns None if the counsellor is not found or if an error occurs
                 during database insertion.

        Raises:
            Exception: Propagates any unexpected exceptions that occur during
                       the database operation after logging them.
        """
        try:
            logger.info("Adding call in database")

            counsellor = (
                self.db.query(Counsellor)
                .filter(Counsellor.id == call_data["counsellor_id"])
                .first()
            )

            if not counsellor:
                logger.error(f"Counsellor not found: {call_data['counsellor_id']}")
                return None

            # set auditor_id and manager_id from the counsellor record
            call_data["auditor_id"] = counsellor.auditor_id
            call_data["manager_id"] = counsellor.manager_id

            # Create and persist the new Call object
            call = Call(**call_data)
            self.db.add(call)
            self.db.commit()
            self.db.refresh(call)
            logger.info("Successfully added call in database")
            return call.id
        except Exception as e:
            logger.error(f"Failed to create call record in database, error: {str(e)}")
            # Returning None indicates failure to the caller
            return None

    def update_call_recording_url(self, call_id: str, recording_url: str):
        """
        Updates the S3 recording URL for an existing call record.

        Locates the call by its ID and updates the `recording_url` field with
        the provided URL. This is typically called after a call recording has
        been successfully uploaded to S3 storage.

        Args:
            call_id (str): The unique identifier of the call record to update.
            recording_url (str): The new S3 URL where the call recording is stored.

        Raises:
            Exception: If an error occurs during the database update operation.
                       The error is logged and then re-raised.
        """
        try:
            logger.info("Updating call recording audio..")

            call = self.db.query(Call).filter(Call.id == call_id).first()
            if call:
                call.recording_url = recording_url
                self.db.commit()
                logger.info("Successfully updated call")
            else:
                logger.warning(f"Call not found for ID: {call_id}, update skipped.")
        except Exception as e:
            logger.error(f"Failed to update call url for call ID {call_id}: {e}")
            # Re-raise the exception to notify the calling service of the failure
            raise e

    def save_call_analysis(self, call_id: str, ai_results: dict):
        """
        Saves the results of AI analysis for a call into the database.

        Creates a new `CallAnalysis` record associated with the given `call_id`.
        It extracts relevant data from the `ai_results` dictionary and populates
        the corresponding fields in the new `CallAnalysis` object.

        Args:
            call_id (str): The unique identifier of the call this analysis belongs to.
            ai_results (dict): A dictionary containing the results from AI processing.
                             Expected keys include 'sentiment_score', 'transcript',
                             'summary', 'anomalies', 'keywords', and 'ai_confidence'.

        Raises:
            Exception: If an error occurs during the creation or saving of the
                       CallAnalysis record. The error is logged and then re-raised.
        """
        try:
            analysis = CallAnalysis(
                call_id=call_id,
                sentiment_score=ai_results.get("sentiment_score", 0.0),
                transcript=ai_results.get("transcript"),
                summary=ai_results.get("summary"),
                anomalies=ai_results.get("anomalies"),
                keywords=ai_results.get("keywords", ""),  # Default to empty string
                ai_confidence=ai_results.get("ai_confidence", 0.0),  # Default to 0.0
            )
            self.db.add(analysis)
            self.db.commit()
            logger.info(f"Successfully saved AI analysis for call ID {call_id}")
        except Exception as e:
            logger.error(
                f"Failed to save AI analysis for call ID {call_id} in database: {e}"
            )
            raise e

    def create_new_counsellor(self, counsellor_data: Dict[str, any]):
        try:
            # hash the password and update the dictionary
            # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # counsellor_data["password"] = pwd_context.hash(counsellor_data["password"])

            counsellor = Counsellor(**counsellor_data)

            self.db.add(counsellor)
            self.db.commit()
            self.db.refresh(counsellor)
            logger.info("Succesfully created new counsellor in database")
            return True

        except Exception as e:
            logger.error(
                f"Internal server error occurred while creating new counsellor, error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while creating new counsellor",
            )

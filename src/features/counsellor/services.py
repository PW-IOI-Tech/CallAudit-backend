from typing import Any, Dict
from core.save_to_s3 import S3Saver
from features.auditor.schemas import BaseResponse
from features.counsellor.repository import CounsellorRepository
from fastapi import HTTPException, status
from datetime import datetime
import logging, os, time
from threading import Thread
from functools import wraps
from features.counsellor.schemas import CallRecordingProcessingSchema
from features.counsellor.utils.ai_analysis import (
    AzureOpenAIService,
    ElevenLabsSpeechService,
)

# Get a logger instance for this module
logger = logging.getLogger(__name__)


def retry(max_attempts=3, delay=60):
    """
    A decorator to add retry logic with exponential backoff to functions.

    This decorator will attempt to call the wrapped function up to `max_attempts` times.
    If an exception occurs, it logs the error and waits for `delay` seconds before
    retrying. If all attempts fail, the last exception is re-raised.

    Args:
        max_attempts (int, optional): Maximum number of times to attempt the function call.
                                    Defaults to 3.
        delay (int, optional): Delay in seconds between retry attempts. Defaults to 60.

    Returns:
        function: The decorated function with retry logic applied.
    """

    def decorator(func):
        @wraps(func)  # Preserves the original function's metadata
        def wrapper(*args, **kwargs):
            # Loop for the specified number of attempts
            for attempt in range(max_attempts):
                try:
                    # Try to execute the function
                    return func(*args, **kwargs)
                except Exception as e:
                    # Log the failure for this attempt
                    logger.error(
                        f"Attempt {attempt + 1} failed for function '{func.__name__}': {e}"
                    )
                    # If this was the last attempt, re-raise the exception
                    if attempt == max_attempts - 1:
                        raise e
                    # Otherwise, wait before retrying
                    logger.info(f"Retrying '{func.__name__}' in {delay} seconds...")
                    time.sleep(delay)
            # This line is theoretically unreachable due to the `raise e` above,
            # but included for explicitness.
            return None

        return wrapper

    return decorator


class CounsellorService:
    """
    Service class encapsulating the business logic for counsellor-related operations.

    This service handles the orchestration of call recording processing, including
    initial database record creation, background audio processing (upload, AI analysis),
    and database updates. It acts as an intermediary between the API layer (router)
    and the data access layer (repository).
    """

    def __init__(self, repo: CounsellorRepository):
        """
        Initializes the CounsellorService with a repository instance.

        Args:
            repo (CounsellorRepository): An instance of CounsellorRepository used
                                       for database interactions.
        """
        self.repo = repo

    def process_call_recording(
        self,
        s3_saver: S3Saver,
        audio_path: str,
        call_start: str,
        call_end: str,
        duration: str,
        call_type: str,
        client_number: str,
        tags: str,
        counsellor_id: str,
    ) -> CallRecordingProcessingSchema:
        """
        Initiates the processing workflow for an uploaded call recording.

        This method performs the initial steps:
        1. Parses input data and creates a preliminary call record in the database.
        2. If successful, it starts a background thread to handle the rest of the
           processing (upload to S3, AI analysis, saving results, cleanup).
        3. Immediately returns a response to the client indicating the recording
           was received and is being processed.

        Args:
            s3_saver (S3Saver): An instance of the S3 utility for uploading files.
            audio_path (str): The local file system path to the temporary audio file.
            call_start (str): ISO format string representing the call's start time.
            call_end (str): ISO format string representing the call's end time.
            duration (str): String representation of the call's duration in seconds.
            call_type (str): The type or category of the call.
            client_number (str): The phone number or identifier of the client.
            tags (str): Comma-separated tags associated with the call.
            counsellor_id (str): The unique identifier of the counsellor who handled the call.

        Returns:

            CallRecordingProcessingSchema: A Pydantic model representing the immediate
                                         response to the client, indicating the call
                                         record was created and processing has started.

        Raises:
            HTTPException: If creating the initial call record in the database fails,
                         an HTTP 500 error is raised.
        """
        try:
            logger.info("Processing call recording and adding the call in database")
            # Prepare data for the initial call record
            call_data = {
                "counsellor_id": counsellor_id,
                "call_start": datetime.fromisoformat(call_start),
                "call_end": datetime.fromisoformat(call_end),
                "duration": int(duration),
                "call_type": call_type,
                "client_number": client_number,
                "tags": tags,
            }

            # Attempt to create the call record in the database via the repository
            call_id = self.repo.create_call(call_data)

            # If creation failed (e.g., counsellor not found), raise an HTTP error
            if not call_id:
                logger.error("call_id is none")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while saving the call in database, please try again",
                )

            # Schedule the rest of the processing to happen in the background
            # Using a daemon thread ensures it doesn't prevent the main program from exiting
            thread = Thread(
                target=self.process_audio_background,
                args=(s3_saver, call_id, audio_path),
                daemon=True,
                name=f"AudioProcessor-{call_id}",
            )

            logger.info(
                f"Starting background thread for call analysis (Call ID: {call_id})"
            )
            thread.start()

            # Return an immediate success response to the client
            return CallRecordingProcessingSchema(
                success=True,
                message="Call recording uploaded successfully",
                call_id=call_id,
                status="processing",  # Indicates asynchronous processing has begun
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to process call recording, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while processing audio.",
            )

    @retry(max_attempts=5)  # Apply the retry decorator with 5 attempts
    def process_audio_background(
        self, s3_saver: S3Saver, call_id: str, audio_path: str
    ) -> None:
        """
        Performs the background processing steps for a call recording.

        This method is intended to run in a separate thread. It handles:
        1. Uploading the audio file to S3 storage.
        2. Updating the call record in the database with the S3 URL.
        3. Performing AI analysis (transcription, summarization, sentiment, etc.) on the audio.
        4. Saving the AI analysis results to the database.
        5. Cleaning up the temporary local audio file.

        This method is decorated with `@retry` to handle transient failures in any
        of these steps.

        Args:
            s3_saver (S3Saver): An instance of the S3 utility for uploading files.
            call_id (str): The unique identifier of the call being processed.
            audio_path (str): The local file system path to the temporary audio file.

        Raises:
            Exception: If any step in the process fails after all retry attempts,
                       the exception is logged and re-raised.
        """
        try:
            logger.info(f"Starting background processing for call {call_id}")

            # --- Step 1: Upload to S3 ---
            s3_url = self.upload_to_s3(s3_saver, audio_path, call_id)
            logger.info(f"Uploaded audio for call {call_id} to S3.")

            # --- Step 2: Update database with S3 URL ---
            self.repo.update_call_recording_url(call_id, s3_url)
            logger.info(f"Updated database record for call {call_id} with S3 URL.")

            # --- Step 3: Perform AI analysis ---
            ai_results = self.perform_ai_analysis(audio_path)
            logger.info(f"Completed AI analysis for call {call_id}.")

            # --- Step 4: Save AI analysis results ---
            self.repo.save_call_analysis(call_id, ai_results)
            logger.info(f"Saved AI analysis results for call {call_id} to database.")

            # --- Step 5: Clean up temp file ---
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Cleaned up temporary audio file for call {call_id}.")

            logger.info(f"Successfully processed audio for call {call_id}")

        except Exception as e:
            # Log the error with context
            logger.error(f"Failed to process audio for call {call_id}: {e}")
            # Re-raise the exception to allow the @retry decorator to handle it
            raise e

    def upload_to_s3(self, s3_saver: S3Saver, audio_path: str, call_id: str) -> str:
        """
        Uploads an audio file to S3 storage.

        Args:
            s3_saver (S3Saver): An instance of the S3 utility for uploading files.
            audio_path (str): The local file system path to the audio file.
            call_id (str): The unique identifier of the call (used potentially for naming/object structure in S3).

        Returns:

            str: The public or presigned URL of the uploaded audio file in S3.

        Raises:
            Exception: If the upload process fails, the exception is logged and re-raised.
        """
        try:
            logger.info(f"Uploading audio for call {call_id} to S3.")
            # Delegate the actual upload to the S3Saver utility
            audio_url = s3_saver.upload_audio_to_s3(audio_path)
            logger.info(f"Successfully uploaded audio for call {call_id} to S3.")
            return audio_url
        except Exception as e:
            logger.error(
                f"Failed to upload audio file for call {call_id} to S3, error: {str(e)}"
            )
            # Re-raise the exception so the calling function (process_audio_background)
            # knows the upload failed
            raise e

    def perform_ai_analysis(self, audio_path: str) -> Dict[str, Any]:
        """
        Performs comprehensive AI analysis on a call recording.

        This method orchestrates several AI processing steps:
        1. Speech-to-text transcription using ElevenLabs.
        2. Conversation analysis, summary generation, sentiment scoring,
           anomaly detection, and keyword extraction using Azure OpenAI.

        Args:
            audio_path (str): The local file system path to the audio file.

        Returns:
            Dict[str, Any]: A dictionary containing the results of all AI analyses.
                          Keys include 'sentiment_score', 'transcript', 'summary',
                          'anomalies', 'keywords', and 'ai_confidence'.

        Raises:
            Exception: If any step in the AI analysis pipeline fails, the exception
                       is logged and re-raised.
        """
        try:
            logger.info("Performing AI analysis for audio")

            # --- Step 1: Transcription ---
            speech_service = ElevenLabsSpeechService()
            logger.info("Extracting transcription from audio")
            transcription_result = speech_service.transcribe_audio(audio_path)
            logger.info("Successfully transcribed audio")

            # --- Prepare data for OpenAI analysis ---
            speaker_analysis = {
                "Speaker_0": {
                    "text": transcription_result["full_transcript"],
                    "word_count": len(transcription_result["full_transcript"].split()),
                    "total_duration": 60.0,  # Rough estimate placeholder
                    "avg_confidence": 0.95,  # Placeholder confidence
                }
            }

            # --- Step 2: Azure OpenAI Analysis ---
            azure_service = AzureOpenAIService()

            logger.info("Analyzing conversation")
            analysis_result = azure_service.analyze_conversation(
                transcript=transcription_result["full_transcript"],
                speakers_data=speaker_analysis,
            )
            logger.info("Successfully analyzed conversation")

            logger.info("Generating summary")
            summary_result = azure_service.generate_conversation_summary(
                transcript=transcription_result["full_transcript"],
                speakers_data=speaker_analysis,  # Note: speakers_data is not used in the summary prompt
            )
            logger.info("Successfully generated summary")

            logger.info("Getting sentiment score")
            sentiment_score = azure_service.get_customer_sentiment_score(
                transcription_result["full_transcript"]
            )
            logger.info("Successfully generated sentiment score")

            logger.info("Getting anomalies")
            anomalies = azure_service.detect_anomalies(
                transcription_result["full_transcript"]
            )
            logger.info("Successfully generated anomalies")

            logger.info("Extracting keywords")
            keywords = azure_service.extract_keywords(
                transcription_result["full_transcript"]
            )
            logger.info("Successfully extracted keywords")

            logger.info("Getting AI confidence score")
            # Estimate confidence based on token usage from the detailed analysis
            confidence = azure_service.estimate_ai_confidence(
                analysis_result.get("usage", {})
            )
            logger.info("Successfully got AI confidence score")

            # --- Compile final results ---
            return {
                "sentiment_score": sentiment_score,
                "transcript": transcription_result["full_transcript"].strip(),
                "summary": summary_result["summary"].strip(),
                "anomalies": anomalies,
                "keywords": keywords,
                "ai_confidence": confidence,
            }
        except Exception as e:
            logger.error(f"Failed to perform AI analysis on audio, error: {str(e)}")
            raise e

    def add_new_counsellor(self, counsellor_data: Dict[str, any]) -> BaseResponse:
        try:
            is_created = self.repo.create_new_counsellor(counsellor_data)

            if not is_created:
                logger.error(f"Failed to create new counsellor")
                raise HTTPException(
                    detail="Failed to create new counsellor",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            logger.info("Counsellor created successfully")
            return BaseResponse(
                success=True, message="Counsellor created successfully."
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error while creating new counsellor, {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server error occurred while creating new counsellor",
            )

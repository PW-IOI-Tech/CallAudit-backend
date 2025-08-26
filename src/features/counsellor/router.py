# Import necessary modules from FastAPI for building the API
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status,
    Request,
)
import logging, os
from features.counsellor.dependency import get_counsellor_service
from features.counsellor.services import CounsellorService

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# Create an APIRouter instance to define routes for the 'counsellor' resource
router = APIRouter(prefix="/counsellor", tags=["API endpoint for counsellor"])


# Define a POST endpoint at '/counsellor/upload-audio'
# The 'description' parameter provides a summary for API documentation
@router.post(
    "/upload-audio",
    description="API endpoint to upload the audio in s3 and perform AI analysis.",
)
async def upload_audio_and_perform_ai_analysis(
    request: Request,
    call_recording: UploadFile = File(...),
    call_start: str = Form(...),
    call_end: str = Form(...),
    duration: str = Form(...),
    call_type: str = Form(...),
    client_number: str = Form(...),
    tags: str = Form(...),
    counsellor_id: str = Form(...),
    service: CounsellorService = Depends(get_counsellor_service),
):
    """
    Handles the upload of a call recording and initiates its processing pipeline.

    This endpoint receives an audio file and associated metadata via a multipart
    form request. It saves the file temporarily, then delegates the processing
    workflow to the `CounsellorService`. The service handles database record
    creation, background audio upload to S3, AI analysis, and result storage.

    Args:
        request (Request): The incoming FastAPI Request object. Used to access
                           application state, specifically `request.app.state.s3_saver`.
        call_recording (UploadFile): The audio file uploaded by the client.
        call_start (str): ISO format string representing the call's start time.
        call_end (str): ISO format string representing the call's end time.
        duration (str): String representation of the call's duration in seconds.
        call_type (str): The type or category of the call.
        client_number (str): The phone number or identifier of the client.
        tags (str): Comma-separated tags associated with the call.
        counsellor_id (str): The unique identifier of the counsellor who handled the call.
        service (CounsellorService): An instance of CounsellorService, injected
                                   by FastAPI's dependency system.

    Returns:

        CallRecordingProcessingSchema: A Pydantic model representing the immediate
                                     response to the client. Indicates that the
                                     recording was received and initial processing
                                     (database record creation) was successful.
                                     The status is typically 'processing'.

    Raises:
        HTTPException: An HTTP 422 Unprocessable Entity error is raised automatically
                       by FastAPI if required form fields or the file are missing.
                       An HTTP 500 Internal Server Error is raised if there's a failure
                       during file saving or initial processing within the service.
    """
    try:
        # --- Step 1: Save the uploaded file temporarily ---
        os.makedirs("temp", exist_ok=True)
        # Construct the full path for the temporary file
        temp_path = os.path.join("temp", call_recording.filename)
        content = await call_recording.read()

        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        logger.info(
            f"Successfully saved call recording file '{call_recording.filename}' to temp directory"
        )

        # --- Step 2: Delegate processing to the service layer ---
        return service.process_call_recording(
            request.app.state.s3_saver,
            temp_path,
            call_start,
            call_end,
            duration,
            call_type,
            client_number,
            tags,
            counsellor_id,
        )
    except HTTPException as e:
        logger.warning(f"HTTP error occurred in router: {e.detail}")
        raise e
    except Exception as e:
        logger.error(
            f"Unexpected error occurred while processing audio upload: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process audio",
        )


@router.post("/", description="Endpoint to add new counsellor")
def add_counsellor(
    manager_id: str,
    name: str,
    auditor_id: str,
    email: str,
    phone: str,
    password: Optional[str] = None,
    service: CounsellorService = Depends(get_counsellor_service),
):
    return service.add_new_counsellor(
        {
            "manager_id": manager_id,
            "auditor_id": auditor_id,
            "name": name,
            "email": email,
            "phone": phone,
        }
    )

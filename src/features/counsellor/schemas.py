from pydantic import BaseModel

# Importing BaseResponse likely from a shared location for consistent API responses
from features.auditor.schemas import BaseResponse


class CallRecordingProcessingSchema(BaseResponse):
    """
    Pydantic model for the response returned by the call recording processing endpoint.

    This schema defines the structure of the JSON response sent back to the client
    after initiating the call recording upload and processing workflow. It inherits
    common fields like 'success' and 'message' from `BaseResponse` and adds specific
    fields related to the call processing status.

    Attributes:
        call_id (str): The unique identifier of the call record created in the database.
        status (str): The current processing status of the call recording (e.g., "processing").
    """

    call_id: str
    status: str

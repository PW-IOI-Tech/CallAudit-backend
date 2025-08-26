"""
FastAPI Server Module

This module provides functionality to create and configure a FastAPI application
with proper lifecycle management, and AWS S3 capabilities.
"""

from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from config import get_app_settings
from core.save_to_s3 import S3Saver

logger = logging.getLogger(__name__)


def create_server():
    """
    Create and configure a FastAPI application instance.

    This function initializes the FastAPI server with:
    - Application lifecycle management
    - CORS middleware configuration
    - S3 client initialization
    - Database table creation

    Returns:
        FastAPI: Configured FastAPI application instance, or None if initialization fails

    Example:
        >>> app = create_server()
        >>> if app:
        ...     # Use the application
        ...     pass
    """
    app_settings = get_app_settings()

    try:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """
            Manage application lifecycle events.

            Handles startup and shutdown operations including:
            - S3 client initialization
            - Database table creation
            - Logging of application state changes

            Args:
                app (FastAPI): The FastAPI application instance

            Yields:
                None: Allows the application to run between startup and shutdown
            """
            # Startup sequence
            logger.info("Starting up FastAPI application...")

            # Initialize S3 saver and store in app state for dependency injection
            app.state.s3_saver = S3Saver()
            logger.info("S3 client initialized and stored in app.state")

            # Application runs here
            yield

            # Shutdown sequence
            logger.info("Shutting down FastAPI application...")

            # Cleanup operations can be added here if needed
            # For example: close database connections, cleanup resources

        # Create FastAPI application with metadata
        app = FastAPI(
            title=app_settings.app_name,
            description="""
This API allows Managers, Auditors, and Counsellors to manage calls, audits, and leads.
Features:
- Upload call recordings
- Audit call quality
- AI call analysis
- Lead management

Built using FastAPI, SQLAlchemy, and PostgreSQL.            
""",
            version=app_settings.version,
            debug=app_settings.debug,
            lifespan=lifespan,
            contact={
                "name": "Shoyeb Ansari",
                "email": "mohammad.ansari4@pw.live",
                "url": "https://github.com/Ashutosh-pw-ioi/CallAudit-backend",
            },
        )

        # Configure CORS middleware for cross-origin resource sharing
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return app

    except Exception as e:
        logger.error(f"Failed to create FastAPI server: {e}", exc_info=True)
        return None

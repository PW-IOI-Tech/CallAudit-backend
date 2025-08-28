"""
Main Application Entry Point - QC Backend Server

This module serves as the primary entry point for the Quality Control (QC) backend
application built with FastAPI. It handles server initialization, configuration,
routing setup, middleware registration, and application lifecycle management.

The application follows a modular architecture with feature-based routing and
comprehensive logging, error handling, and health monitoring capabilities.

Key Features:
    - FastAPI server initialization and configuration
    - Feature-based router registration (auditor, manager, counsellor, auth)
    - Centralized logging with file rotation and size management
    - Global error handling with standardized response format
    - Health check endpoints for monitoring
    - Environment variable configuration
    - Production-ready server setup with Uvicorn

Architecture Overview:
    The application uses a layered architecture:
    - Presentation Layer: FastAPI routers and endpoints
    - Business Logic Layer: Feature modules (auditor, manager, counsellor)
    - Data Access Layer: SQLAlchemy ORM with database models
    - Infrastructure Layer: Logging, configuration, and server setup

Environment Setup:
    - Requires .env file for configuration
    - Supports development and production environments
    - Configurable logging levels and file management
    - Database connection configuration

API Structure:
    - All API endpoints are prefixed with '/api/v1'
    - RESTful design patterns
    - Standardized error responses
    - Health monitoring endpoints

Usage:
    Development:
        python main.py

    Production:
        uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

Dependencies:
    - FastAPI: Modern web framework for building APIs
    - Uvicorn: ASGI server for running FastAPI applications
    - SQLAlchemy: Database ORM
    - python-dotenv: Environment variable management
    - Custom core modules: logging, server configuration

Author: QC Backend Team
Version: 0.1.0
Created: 2025
Last Modified: 2025-07-25
"""

from core.logging import setup_logging
from dotenv import load_dotenv

setup_logging(
    log_level="INFO",
    log_file="logs/app.log",
    max_file_size=8 * 1024 * 1024,  # 8MB per file
    backup_count=3,  # Keep 3 old log files
)
load_dotenv()

from core.server import create_server
from sqlalchemy.orm import Session
import uvicorn
import logging
from database import get_db
from fastapi import HTTPException, Request, responses, Form, Depends
import os

# import routerssudo snap install astral-uv
from features.auditor.router import router as auditor_router
from features.manager.router import router as manager_router
from features.counsellor.router import router as counsellor_router
from features.auth.router import router as auth_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_server()

# Include routers
app.include_router(auditor_router, prefix="/api/v1")
app.include_router(manager_router, prefix="/api/v1")
app.include_router(counsellor_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


# Register global error
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return responses.JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "code": exc.status_code},
    )


# Test endpoints
@app.get("/")
async def root():
    return {"message": "QC backend app is running!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def main():
    """Main Function"""
    logger.info(
        f"Environment variables loaded successfully, test env: {os.getenv('TEST')}"
    )
    uvicorn.run("main:app", host="0.0.0.0")


if __name__ == "__main__":
    main()

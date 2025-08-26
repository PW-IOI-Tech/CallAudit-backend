from sqlalchemy.orm import Session
from database import get_db
from fastapi import Depends

from features.counsellor.repository import CounsellorRepository
from features.counsellor.services import CounsellorService


def get_counsellor_repository(db: Session = Depends(get_db)) -> CounsellorRepository:
    """
    FastAPI dependency to create and provide a CounsellorRepository instance.

    This function is used by FastAPI's dependency injection system. It automatically
    obtains a database session by calling the `get_db` dependency and then uses
    that session to instantiate a `CounsellorRepository`.

    Args:
        db (Session, optional): An SQLAlchemy database session, provided by the `get_db` dependency.

    Returns:

        CounsellorRepository: An instance of the CounsellorRepository, ready for use
                              in services that require database access for counsellor data.
    """
    return CounsellorRepository(db)


def get_counsellor_service(
    repo: CounsellorRepository = Depends(get_counsellor_repository),
) -> CounsellorService:
    """
    FastAPI dependency to create and provide a CounsellorService instance.

    This function facilitates FastAPI's dependency injection. It first resolves
    the `get_counsellor_repository` dependency to obtain a `CounsellorRepository`
    instance, and then uses that repository to instantiate the `CounsellorService`.

    Args:
        repo (CounsellorRepository, optional): A CounsellorRepository instance,
                                               provided by the `get_counsellor_repository` dependency.

    Returns:

        CounsellorService: An instance of the CounsellorService, ready for use
                           in API routers to handle counsellor-related business logic.
    """
    return CounsellorService(repo)

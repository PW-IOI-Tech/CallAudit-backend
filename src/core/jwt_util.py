from config import get_jwt_settings
from datetime import datetime, timedelta
from jose import JWTError, jwt
import logging

logger = logging.getLogger(__name__)


class JWTUtil:
    def __init__(self):
        self.jwt_settings = get_jwt_settings()
        self.access_token_expire_minutes = self.jwt_settings.access_token_expire_minutes

    def create_jwt_token(self, data: dict) -> str | None:
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(days=1)
            to_encode.update({"exp": expire})
            return jwt.encode(
                to_encode,
                self.jwt_settings.jwt_secret,
                algorithm=self.jwt_settings.algorithm,
            )
        except Exception as e:
            logger.error("Failed to generate jwt token")
            return None

    def create_refresh_token(self, data: dict) -> str | None:
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(days=7)
            to_encode.update({"exp": expire})
            return jwt.encode(
                to_encode,
                self.jwt_settings.jwt_secret,
                algorithm=self.jwt_settings.algorithm,
            )
        except Exception as e:
            logger.error(f"Failed to generate refresh token, error: {str(e)}")
            return None


def get_jwt_util():
    return JWTUtil()

"""
Configuration management for the FastAPI application.
Handles database connections, environment variables, and application settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import os


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    # PostgreSQL connection parameters
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(..., env="POSTGRES_DB")

    # Connection pool settings for production
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")  # 1 hour

    # model_config = {
    #     "extra": "allow"
    # }

    class Config:
        """Pydantic configuration for DatabaseSettings."""

        env_file = "../.env"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Generate database URL for SQLAlchemy.

        Returns:
            str: Formatted database connection URL string
        """
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


class AppSettings(BaseSettings):
    """Application configuration settings."""

    app_name: str = Field(default="FastAPI QC backend", env="APP_NAME")
    debug: bool = Field(default=True, env="DEBUG")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")

    # model_config = {
    #     "extra": "allow"
    # }
    class Config:
        """Pydantic configuration for AppSettings."""

        env_file = "../.env"
        case_sensitive = False


class AWSSettings(BaseSettings):
    """AWS configuration settings for cloud services."""

    aws_access_key_id: str = Field(default="your_access_key", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(
        default="your_secret_key", env="AWS_SECRET_ACCESS_KEY"
    )
    aws_region: str = Field(default="your_region", env="AWS_REGION")
    aws_s3_bucket_name: str = Field(
        default="your_bucket_name", env="AWS_S3_BUCKET_NAME"
    )

    # model_config = {
    #     "extra": "allow"
    # }

    class Config:
        """Pydantic configuration for AWSSettings."""

        env_file = "../.env"
        case_sensitive = False


class JWT_SETTINGS(BaseSettings):
    """JWT (JSON Web Token) security configuration settings."""

    jwt_secret: str = Field(default="jwt_secret", env="JWT_SECRET")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # model_config = {
    #     "extra": "allow"
    # }

    class Config:
        """Pydantic configuration for JWT_SETTINGS."""

        env_file = "../.env"
        case_sensitive = False


class LLMConfig(BaseSettings):
    """Large Language Model configuration settings for AI services."""

    elevenlabs_api_key: str = Field(default="", env="ELEVENLABS_API_KEY")
    azure_openai_endpoint: str = Field(default="", env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", env="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="", env="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="", env="AZURE_OPENAI_API_VERSION")

    # model_config = {
    #     "extra": "allow",
    # }
    class Config:
        """Pydantic configuration for LLMConfig."""

        env_file = "../.env"
        case_sensitive = False


@lru_cache()
def get_jwt_settings() -> JWT_SETTINGS:
    """Get cached JWT settings instance.

    Returns:
        JWT_SETTINGS: Cached instance of JWT configuration settings
    """
    return JWT_SETTINGS()


@lru_cache()
def get_database_settings() -> DatabaseSettings:
    """Get cached database settings instance.

    Returns:
        DatabaseSettings: Cached instance of database configuration settings
    """
    return DatabaseSettings()


@lru_cache()
def get_app_settings() -> AppSettings:
    """Get cached application settings instance.

    Returns:
        AppSettings: Cached instance of application configuration settings
    """
    return AppSettings()


@lru_cache()
def get_aws_settings() -> AWSSettings:
    """Get cached aws configuration settings

    Returns:
        AWSSettings: instance with correct settings
    """
    return AWSSettings()


@lru_cache()
def get_llm_config() -> LLMConfig:
    """Get cached LLM config which contains all the configuration keys of openai and elevenlabs

    Returns:
        LLMConfig: instance with LLM configuration settings
    """
    return LLMConfig()

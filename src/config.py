"""
Configuration module for loading environment variables and application settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Anthropic Configuration
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Environment Configuration
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Telegram Configuration
    # Automatically selects the correct bot token based on ENVIRONMENT
    @property
    def telegram_bot_token(self) -> str:
        """
        Get the appropriate Telegram bot token based on environment.

        - development: Uses TELEGRAM_BOT_TOKEN_DEV
        - production: Uses TELEGRAM_BOT_TOKEN_PROD
        - Falls back to TELEGRAM_BOT_TOKEN if specific token not found
        """
        if self.environment == "production":
            token = os.getenv("TELEGRAM_BOT_TOKEN_PROD", "")
            if token:
                return token
        else:  # development or any other environment
            token = os.getenv("TELEGRAM_BOT_TOKEN_DEV", "")
            if token:
                return token

        # Fallback to generic TELEGRAM_BOT_TOKEN
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")

    # Dashboard Configuration
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "")

    # Application Configuration
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    # LangSmith Configuration
    langsmith_tracing: str = os.getenv("LANGSMITH_TRACING", "false")
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "default")

    # Access Control Configuration
    @property
    def allowed_users_only(self) -> bool:
        """Whether to restrict bot access to authorized users only.

        Selects the appropriate flag based on environment:
        - production: ALLOWED_USERS_ONLY_PROD
        - development: ALLOWED_USERS_ONLY_DEV

        Returns:
            True if access restriction is enabled.
        """
        if self.environment == "production":
            val = os.getenv("ALLOWED_USERS_ONLY_PROD", "false")
        else:
            val = os.getenv("ALLOWED_USERS_ONLY_DEV", "false")
        return val.lower() in ("true", "1", "yes")

    @property
    def secret_code(self) -> str:
        """Secret code users must provide to gain authorized access.

        Selects the appropriate code based on environment:
        - production: SECRET_CODE_PROD
        - development: SECRET_CODE_DEV

        Returns:
            The secret code string for the current environment.
        """
        if self.environment == "production":
            return os.getenv("SECRET_CODE_PROD", "")
        return os.getenv("SECRET_CODE_DEV", "")

    @property
    def admin_secret_code(self) -> str:
        """Secret code a user must provide to gain admin access.

        Selects the appropriate code based on environment:
        - production: ADMIN_SECRET_CODE_PROD
        - development: ADMIN_SECRET_CODE_DEV

        Returns:
            The admin secret code string for the current environment.
        """
        if self.environment == "production":
            return os.getenv("ADMIN_SECRET_CODE_PROD", "")
        return os.getenv("ADMIN_SECRET_CODE_DEV", "")

    @property
    def daily_report_hour(self) -> int:
        """UTC hour at which the daily admin report is sent.

        Returns:
            Integer hour (0-23). Defaults to 21 (9 PM UTC).
        """
        return int(os.getenv("DAILY_REPORT_HOUR", "21"))

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Create a global settings instance
settings = Settings()

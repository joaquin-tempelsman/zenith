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
    
    # Telegram Configuration
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")
    
    # Dashboard Configuration
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "admin123")
    
    # Application Configuration
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    
    # LangSmith Configuration
    langsmith_tracing: str = os.getenv("LANGSMITH_TRACING", "false")
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "default")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create a global settings instance
settings = Settings()

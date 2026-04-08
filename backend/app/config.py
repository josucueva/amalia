"""
Configuration management for the application.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Agentic AutoML Platform"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # CORS
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # Local Models
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "gemini/gemini-2.5-flash"

    # File Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "./data/uploads"
    allowed_file_types: str = ".csv"

    # MongoDB
    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_db_name: str = "amalia"

    # Agent Configuration
    agent_config_dir: str = "./config/agents"
    agent_timeout_seconds: int = 300

    # MCP
    mcp_server_enabled: bool = True
    mcp_server_port: int = 3000

    # Batch Processing
    batch_enabled: bool = True
    batch_max_workers: int = 2
    batch_item_max_retries: int = 2
    batch_retry_delay_seconds: int = 5
    batch_artifacts_dir: str = "./data/batch_exports"
    batch_auto_zip_on_completion: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "./logs/app.log"

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow extra fields for dynamically added API keys
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

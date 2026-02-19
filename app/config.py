"""
Configuration management for the automation platform.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # Azure OpenAI Keys
    AZURE_API_KEY: str
    AZURE_ENDPOINT: str
    AZURE_DEPLOYMENT: str
    AZURE_API_VERSION: str = "2024-02-01"
    
    # OpenAI Keys (optional, for backwards compatibility)
    OPENAI_API_KEY: Optional[str] = None
    
    # Browser Settings (always headed so user can see the browser)
    HEADLESS: bool = False
    BROWSER_TIMEOUT: int = 60000  # 60s for slow pages (e.g. LG e-commerce)
    
    # Execution Settings
    MAX_RETRIES: int = 3
    SCORE_THRESHOLD: float = 0.65
    RETRY_DELAY: float = 1.0
    
    # State Management
    ENABLE_STATE_TRACKING: bool = True
    MAX_STATE_HISTORY: int = 100

    # Fragment Reuse
    FRAGMENT_SAVE_ENABLED: bool = True
    FRAGMENT_MIN_LENGTH: int = 2
    
    # Memory Settings
    ENABLE_MEMORY: bool = True
    MEMORY_THRESHOLD: float = 0.75
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/automation.log"
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env


# Global settings instance
settings = Settings()

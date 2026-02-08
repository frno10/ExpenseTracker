"""
Configuration settings for the Expense Tracker application.
"""
import logging
import os
from urllib.parse import urlparse
from pydantic_settings import BaseSettings
from pydantic import validator
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration with parsed connection details."""
    
    def __init__(self, url: str):
        self.url = url
        self.parsed = urlparse(url)
        self.host = self.parsed.hostname
        self.port = self.parsed.port or 5432
        self.database = self.parsed.path.lstrip('/')
        self.username = self.parsed.username
        self.password = self.parsed.password
        self.max_retries = 5
        self.retry_delay = 1.0
        self.connection_timeout = 30


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Expense Tracker"
    debug: bool = False
    
    # Database Mode Selection
    # Options: "postgresql", "supabase_rest", "memory"
    database_mode: str = "postgresql"
    
    # Database
    database_url: str = "postgresql+asyncpg://expense_user:expense_pass@localhost:5432/expense_tracker"
    
    # Supabase
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Environment settings
    environment: str = "development"
    log_level: str = "INFO"
    
    # Authentication mode
    auth_mode: str = "supabase"  # Options: "supabase", "local"
    
    # Local auth settings
    enable_registration: bool = True
    require_email_verification: bool = False
    sync_supabase_users: bool = False
    
    class Config:
        env_file = [".env.local", ".env"]  # Try .env.local first, then .env
    
    @validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format and accessibility."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        
        try:
            parsed = urlparse(v)
            if not parsed.scheme:
                raise ValueError("Database URL must include a scheme (e.g., postgresql://)")
            if not parsed.hostname:
                raise ValueError("Database URL must include a hostname")
            if not parsed.path or parsed.path == '/':
                raise ValueError("Database URL must include a database name")
            
            logger.info(f"Database URL validated: {parsed.scheme}://{parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')}")
            return v
        except Exception as e:
            logger.error(f"Invalid database URL format: {e}")
            raise ValueError(f"Invalid database URL: {e}")
    
    def get_database_config(self) -> DatabaseConfig:
        """Get parsed database configuration."""
        return DatabaseConfig(self.database_url)
    
    def is_render_environment(self) -> bool:
        """Detect if running on Render platform."""
        return bool(os.getenv('RENDER'))
    
    def get_render_config(self) -> Dict[str, Any]:
        """Get Render-specific configuration details."""
        return {
            'is_render': self.is_render_environment(),
            'render_service_name': os.getenv('RENDER_SERVICE_NAME'),
            'render_service_type': os.getenv('RENDER_SERVICE_TYPE'),
            'render_git_commit': os.getenv('RENDER_GIT_COMMIT'),
        }
    
    def log_config_summary(self) -> None:
        """Log configuration summary without sensitive data."""
        db_config = self.get_database_config()
        render_config = self.get_render_config()
        
        logger.info("=== Application Configuration ===")
        logger.info(f"App Name: {self.app_name}")
        logger.info(f"Debug Mode: {self.debug}")
        logger.info(f"Database Mode: {self.database_mode}")
        logger.info(f"Database Host: {db_config.host}:{db_config.port}")
        logger.info(f"Database Name: {db_config.database}")
        logger.info(f"Database User: {db_config.username}")
        
        if render_config['is_render']:
            logger.info("=== Render Environment Detected ===")
            logger.info(f"Service Name: {render_config['render_service_name']}")
            logger.info(f"Service Type: {render_config['render_service_type']}")
            logger.info(f"Git Commit: {render_config['render_git_commit']}")
        else:
            logger.info("=== Local Development Environment ===")
        
        logger.info("=== Configuration Loaded Successfully ===")


settings = Settings()
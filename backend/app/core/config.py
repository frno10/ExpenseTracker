"""
Configuration settings for the Expense Tracker application.
"""
from pydantic_settings import BaseSettings
from typing import Optional


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
    
    class Config:
        env_file = ".env"


settings = Settings()
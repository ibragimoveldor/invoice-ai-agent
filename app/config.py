# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: str
    aws_secret_access_key: str
    
    # Database
    database_url: str = "sqlite:///./invoice_intelligence.db"
    
    # Application
    upload_dir: str = "uploads/invoices"
    reports_dir: str = "uploads/reports"
    max_file_size: int = 10485760  # 10MB
    
    # API
    api_title: str = "Invoice Intelligence Agent"
    api_version: str = "1.0.0"
    
    # Vector Store
    vector_db_path: str = "./chroma_db"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    
    # Database Config
    DATABASE_URL: str
    SYNC_DATABASE_URL: str
    
    # Redis Config
    REDIS_URL: str
    
    # Meilisearch Config
    MEILI_URL: str = "http://localhost:7700"
    MEILI_MASTER_KEY: str = "masterKey123456!"
    
    # JWT & Security Config
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # PII Encryption Config (Fernet URL-safe base64 key)
    PII_ENCRYPTION_KEY: str
    
    # OTP Mocking Config
    MOCK_OTP: bool = True
    MOCK_OTP_CODE: str = "123456"
    
    # S3 Object Storage Config
    S3_BUCKET_NAME: str = "samuday-kyc"
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # Google OAuth Config
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173"
    
    # Frontend URL (for CORS and redirects)
    FRONTEND_URL: str = "http://localhost:5173"

    # NVIDIA AI Config
    NVIDIA_API_KEY: str = os.environ.get("NVIDIA_API_KEY")
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "nvidia/nemotron-3-nano-30b-a3b"

    # Groq AI Config
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY")

    # Gemini AI Config
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

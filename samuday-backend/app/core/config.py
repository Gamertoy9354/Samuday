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

    # Supabase Storage — used for all uploaded/AI-generated images instead of local
    # disk, since Render's free/ephemeral instances lose local files on restart.
    # SUPABASE_SERVICE_ROLE_KEY is a secret admin key: never expose it to the frontend.
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Payment gateway webhook signing secret (HMAC-SHA256) used to verify callback authenticity
    PAYMENT_WEBHOOK_SECRET: str = "dev-payment-webhook-secret-change-in-production"
    
    # OTP Mocking Config — defaults to False (secure) so a forgotten env var in
    # production fails closed rather than silently accepting a fixed bypass code.
    MOCK_OTP: bool = False
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

    # Backend's own public URL — used to build links back to itself (e.g. uploaded
    # image URLs). Deliberately separate from FRONTEND_URL: on a real deployment
    # the two are different hosts entirely, not just different ports.
    BACKEND_URL: str = "http://localhost:8000"

    # NVIDIA AI Config
    NVIDIA_API_KEY: str = os.environ.get("NVIDIA_API_KEY")
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "nvidia/nemotron-3-nano-30b-a3b"

    # Groq AI Config
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY")

    # Gemini AI Config
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY")

    # Cloudflare Workers AI — free image-generation/editing fallback used only when
    # Gemini image editing is unavailable (see app/ai/service.py::_edit_image_with_fallback)
    CLOUDFLARE_ACCOUNT_ID: str = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    CLOUDFLARE_API_TOKEN: str = os.environ.get("CLOUDFLARE_API_TOKEN", "")

    # Delhivery shipping (optional — empty means no account connected yet; the
    # shipping module falls back to clearly-labeled simulated rates/tracking)
    DELHIVERY_API_KEY: str = ""

    # Google Maps (optional — geocoding defaults to free OpenStreetMap Nominatim
    # when unset; add this + billing later for Google's more polished autocomplete)
    GOOGLE_MAPS_API_KEY: str = ""

    # Platform fee taken on each order, absorbed gateway-cut-included (see
    # app/marketplace/fees.py for the split). 0.05 = 5%.
    PLATFORM_FEE_RATE: float = 0.05
    # Informational only (no real gateway connected yet) — used to estimate the
    # net platform margin after gateway processing costs.
    ESTIMATED_GATEWAY_FEE_RATE: float = 0.02

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

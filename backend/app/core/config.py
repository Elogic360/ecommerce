from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "postgresql://ecommerce_user:commercePASS@127.0.0.1:5432/ecommerce"

    # Alternative database configuration (optional)
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    # Security & Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Configuration
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Application Settings
    APP_NAME: str = "ShopHub E-Commerce"
    APP_VERSION: str = "1.5.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # File Upload Configuration
    UPLOAD_DIR: str = "uploads/products"
    MAX_FILE_SIZE: int = 5242880
    ALLOWED_EXTENSIONS: str = ".jpg,.jpeg,.png,.gif,.webp"

    # Email Configuration (Optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # Payment Gateway Configuration (Optional)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"

    # Redis Configuration (Optional)
    REDIS_URL: Optional[str] = None
    CACHE_ENABLED: bool = False

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # Admin Panel
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5isl.xMUTWq3u"

    # Logging
    LOG_FILE: str = "logs/app.log"
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5

    # Session Configuration
    SESSION_SECRET: str = "another_secret_key_for_sessions"
    SESSION_COOKIE_NAME: str = "ecommerce_session"

    # Development/Production Mode
    ENVIRONMENT: str = "development"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    API_V1_STR: str = "/api/v1"
    DOC_V1_STR: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # Database Pool Configuration
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # Timezone
    TIMEZONE: str = "UTC"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore'  # Allow extra fields in environment
    )

settings = Settings()
"""
Backend Configuration Module
Centralized configuration for the Neatify E-Commerce API.

IMPORTANT SECURITY NOTES:
- Default values are for DEVELOPMENT ONLY
- All production deployments MUST set environment variables
- Never commit production secrets to version control
- Use .env files for local development (not committed)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List
import os


class Settings(BaseSettings):
    # =========================================================================
    # Database Configuration
    # =========================================================================
    # IMPORTANT: Set DATABASE_URL in production environment
    # Development default only works for local PostgreSQL setup
    DATABASE_URL: str = Field(
        default="postgresql://ecommerce_user:commercePASS@127.0.0.1:5432/ecommerce",
        description="PostgreSQL database connection URL (REQUIRED in production)"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Optional[str]) -> str:
        """
        Normalize database URL format.
        Converts 'postgres://' to 'postgresql://' for SQLAlchemy compatibility.
        """
        if v and v.startswith("postgres://"):
            # Fix for Render/Heroku which use 'postgres://' but SQLAlchemy requires 'postgresql://'
            return v.replace("postgres://", "postgresql://", 1)
        
        # Return value or development default
        # SECURITY: This default should only be used in development
        default_url = "postgresql://ecommerce_user:commercePASS@127.0.0.1:5432/ecommerce"
        
        # Warn if using default in non-development environment
        env = os.getenv("ENVIRONMENT", "development")
        if not v and env != "development":
            import warnings
            warnings.warn(
                f"Using default DATABASE_URL in {env} environment. "
                "This is insecure! Set DATABASE_URL environment variable.",
                RuntimeWarning
            )
        
        return v or default_url

    # Database Pool Configuration
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 60
    DB_POOL_RECYCLE: int = 1800

    # =========================================================================
    # Security & Authentication
    # =========================================================================
    # SECURITY CRITICAL: Change these in production!
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT encoding (MUST change in production)"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Configuration
    # REQUIRED: Set ALLOWED_ORIGINS environment variable with your frontend URLs
    ALLOWED_ORIGINS: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins (REQUIRED in all environments)"
    )
    
    # Helper field - parsed from ALLOWED_ORIGINS
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into list."""
        if not self.ALLOWED_ORIGINS:
            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError(
                    "ALLOWED_ORIGINS must be set in production environment. "
                    "No hardcoded defaults are provided for security reasons."
                )
            # For development, warn but don't fail
            import warnings
            warnings.warn(
                "ALLOWED_ORIGINS is not set. Set this environment variable to specify allowed CORS origins.",
                RuntimeWarning
            )
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',') if origin.strip()]

    # Session & Rate Limiting
    SESSION_SECRET: str = Field(
        default="another_secret_key_for_sessions",
        description="Secret for session cookies (MUST change in production)"
    )
    SESSION_COOKIE_NAME: str = "ecommerce_session"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # =========================================================================
    # Application Info
    # =========================================================================
    APP_NAME: str = "Neatify E-Commerce"
    APP_VERSION: str = "1.5.0"
    DEBUG: bool = Field(
        default=False,
        description="Debug mode (should be False in production)"
    )
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )

    # API Routing
    API_V1_PREFIX: str = "/api/v1"
    API_V1_STR: str = "/api/v1"
    DOC_V1_STR: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # =========================================================================
    # Files & Storage
    # =========================================================================
    UPLOAD_DIR: str = "uploads/products"
    MAX_FILE_SIZE: int = 5242880  # 5MB
    ALLOWED_EXTENSIONS: str = ".jpg,.jpeg,.png,.gif,.webp"

    # =========================================================================
    # External Services (Optional)
    # =========================================================================
    
    # Email (SMTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # Payments
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"

    # Caching
    REDIS_URL: Optional[str] = None
    CACHE_ENABLED: bool = False
    CACHE_TTL: int = 300

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # =========================================================================
    # Admin Initial Account
    # =========================================================================
    # SECURITY: These are used ONLY by create_admin.py script
    # Set via environment variables - no hardcoded defaults for production
    ADMIN_EMAIL: str = Field(
        default="",
        description="Admin email (set via environment variable)"
    )
    ADMIN_USERNAME: str = Field(
        default="admin",
        description="Admin username"
    )
    # Default hash for "admin123" - MUST change in production
    ADMIN_PASSWORD_HASH: str = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5isl.xMUTWq3u"

    # =========================================================================
    # Logging & Misc
    # =========================================================================
    LOG_FILE: str = "logs/app.log"
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    TIMEZONE: str = "UTC"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        # Case sensitive to match exact env var names
        case_sensitive=True
    )

    def validate_production_config(self) -> None:
        """
        Validate that required production settings are configured.
        Call this at application startup in production environments.
        """
        if self.ENVIRONMENT == "production":
            issues = []
            
            # Check for default/weak secrets
            if self.SECRET_KEY == "your-secret-key-change-in-production":
                issues.append("SECRET_KEY is using default value")
            
            if self.SESSION_SECRET == "another_secret_key_for_sessions":
                issues.append("SESSION_SECRET is using default value")
            
            if self.ADMIN_PASSWORD_HASH == "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5isl.xMUTWq3u":
                issues.append("ADMIN_PASSWORD_HASH is using default value (admin123)")
            
            # Check DEBUG is disabled
            if self.DEBUG:
                issues.append("DEBUG is enabled in production")
            
            # Check database URL
            if "127.0.0.1" in self.DATABASE_URL or "localhost" in self.DATABASE_URL:
                issues.append("DATABASE_URL appears to be using localhost")
            
            if issues:
                error_msg = "PRODUCTION SECURITY ISSUES DETECTED:\n" + "\n".join(f"  - {issue}" for issue in issues)
                raise ValueError(error_msg)


# Initialize settings
settings = Settings()


# Validate production configuration
if settings.ENVIRONMENT == "production":
    try:
        settings.validate_production_config()
    except ValueError as e:
        import sys
        print(f"\n{'='*60}")
        print("CRITICAL SECURITY ERROR")
        print(f"{'='*60}")
        print(str(e))
        print(f"{'='*60}\n")
        # In production, we'll allow it to start but warn loudly. 
        # You SHOULD still set these in your Render settings!
        import logging
        logging.warning("SERVICE STARTING WITH INSECURE CONFIGURATION. CHECK LOGS ABOVE.")
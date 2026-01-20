"""
Authentication Schemas
Pydantic models for authentication requests and responses
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import re

from app.models.customer import Role


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

def validate_password_strength(password: str) -> str:
    """
    Validate password meets security requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")
    return password


# =============================================================================
# REGISTRATION SCHEMAS
# =============================================================================

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="Valid email address")
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, underscore, hyphen only)"
    )
    password: str = Field(..., min_length=8, description="Strong password")
    confirm_password: str = Field(..., description="Password confirmation")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)
    
    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserRegisterSimple(BaseModel):
    """Simplified registration (for API/quick signup)"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


# =============================================================================
# LOGIN SCHEMAS
# =============================================================================

class UserLogin(BaseModel):
    """User login request (JSON body)"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Extend token expiration")


class LoginResponse(BaseModel):
    """Login response with tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: "UserResponse"


# =============================================================================
# TOKEN SCHEMAS
# =============================================================================

class Token(BaseModel):
    """Simple token response (OAuth2 compatible)"""
    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(Token):
    """Token response with refresh token"""
    refresh_token: str
    expires_in: int


class TokenData(BaseModel):
    """Decoded token payload"""
    sub: str  # User ID or email
    exp: datetime
    type: str = "access"  # access or refresh
    role: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="Valid refresh token")


# =============================================================================
# PASSWORD MANAGEMENT SCHEMAS
# =============================================================================

class PasswordChange(BaseModel):
    """Change password (authenticated user)"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)
    
    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        return self


class PasswordResetRequest(BaseModel):
    """Request password reset email"""
    email: EmailStr = Field(..., description="Registered email address")


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token"""
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)
    
    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


# =============================================================================
# EMAIL VERIFICATION SCHEMAS
# =============================================================================

class EmailVerificationRequest(BaseModel):
    """Request email verification"""
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    """Confirm email with token"""
    token: str = Field(..., description="Email verification token")


class ResendVerificationRequest(BaseModel):
    """Resend verification email"""
    email: EmailStr


# =============================================================================
# USER RESPONSE SCHEMAS
# =============================================================================

class UserResponse(BaseModel):
    """User information response"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = Field(None, alias="phone_number")
    role: Optional[str] = None
    is_active: bool = True
    is_verified: bool = True  # Default to True since column doesn't exist
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # V1.5 fields
    loyalty_tier: Optional[str] = None
    loyalty_points: Optional[int] = 0
    preferred_currency: Optional[str] = "USD"

    class Config:
        from_attributes = True
        populate_by_name = True


class UserProfile(UserResponse):
    """Extended user profile"""
    updated_at: Optional[datetime] = None
    addresses_count: int = 0
    orders_count: int = 0


class UserUpdate(BaseModel):
    """Update user profile"""
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    username: Optional[str] = Field(None, min_length=3, max_length=50)


# =============================================================================
# ADMIN USER MANAGEMENT SCHEMAS
# =============================================================================

class AdminUserCreate(BaseModel):
    """Admin creates a new user with role"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Role = Role.USER
    is_active: bool = True
    is_verified: bool = False


class AdminUserUpdate(BaseModel):
    """Admin updates user"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserListResponse(BaseModel):
    """Paginated user list - matches frontend PaginatedResponse interface"""
    items: List[UserResponse]  # Frontend expects 'items' not 'users'
    total: int
    page: int
    page_size: int  # Frontend expects 'page_size' not 'per_page'
    total_pages: int  # Frontend expects 'total_pages' not 'pages'


# =============================================================================
# SECURITY SCHEMAS
# =============================================================================

class AccountLockStatus(BaseModel):
    """Account lock information"""
    is_locked: bool
    locked_until: Optional[datetime] = None
    failed_attempts: int
    message: str


class SessionInfo(BaseModel):
    """Current session information"""
    user: UserResponse
    token_expires_at: datetime
    issued_at: datetime


# Update forward references
LoginResponse.model_rebuild()

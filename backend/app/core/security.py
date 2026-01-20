"""
Security Utilities
Password hashing, JWT token management, and authentication helpers
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any
import secrets
import hashlib

from jose import JWTError, jwt, ExpiredSignatureError
import bcrypt  # Use bcrypt directly instead of passlib
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.customer import User, Role


# =============================================================================
# PASSWORD HASHING (using bcrypt directly for Python 3.14 compatibility)
# =============================================================================

# Bcrypt cost factor (rounds)
BCRYPT_ROUNDS = 12


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The password to verify
        hashed_password: The hashed password to check against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be updated (e.g., bcrypt rounds changed).
    
    Args:
        hashed_password: The current password hash
        
    Returns:
        True if password should be rehashed
    """
    # For bcrypt, we can check the cost factor in the hash
    # Format: $2b$XX$... where XX is the cost factor
    try:
        parts = hashed_password.split('$')
        if len(parts) >= 3:
            current_rounds = int(parts[2])
            return current_rounds < BCRYPT_ROUNDS
    except (ValueError, IndexError):
        pass
    return False


# =============================================================================
# TOKEN CONFIGURATION
# =============================================================================

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=True
)

# Optional OAuth2 scheme (doesn't raise error if no token)
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


# Token types
class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"


# =============================================================================
# JWT TOKEN FUNCTIONS
# =============================================================================

def create_access_token(
    subject: Union[str, int],
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (usually user ID or email)
        role: User role for RBAC
        expires_delta: Custom expiration time
        additional_claims: Extra claims to include in token
        
    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "type": TokenType.ACCESS,
        "iat": now,
        "exp": expire,
    }
    
    if role:
        to_encode["role"] = role
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject of the token (usually user ID or email)
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(subject),
        "type": TokenType.REFRESH,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),  # Unique token ID
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(email: str) -> str:
    """
    Create a token for password reset.
    
    Args:
        email: User's email address
        
    Returns:
        Password reset token
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry
    
    to_encode = {
        "sub": email,
        "type": TokenType.PASSWORD_RESET,
        "exp": expire,
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_email_verification_token(email: str) -> str:
    """
    Create a token for email verification.
    
    Args:
        email: User's email address
        
    Returns:
        Email verification token
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry
    
    to_encode = {
        "sub": email,
        "type": TokenType.EMAIL_VERIFICATION,
        "exp": expire,
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token_type(payload: dict, expected_type: str) -> bool:
    """
    Verify that a token is of the expected type.
    
    Args:
        payload: Decoded token payload
        expected_type: Expected token type
        
    Returns:
        True if token type matches
    """
    return payload.get("type") == expected_type


def hash_token(token: str) -> str:
    """
    Create a hash of a token for storage (e.g., refresh tokens).
    
    Args:
        token: Token to hash
        
    Returns:
        SHA256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


# =============================================================================
# AUTHENTICATION DEPENDENCIES
# =============================================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        
        # Verify it's an access token
        if not verify_token_type(payload, TokenType.ACCESS):
            raise credentials_exception
        
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
            
    except HTTPException:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.email == email).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    # Note: locked_until column doesn't exist in DB, skip check
    # Account lockout is handled by is_account_locked() which returns False
    
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work both with and without authentication.
    
    Args:
        token: Optional JWT access token
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not token:
        return None
    
    try:
        payload = decode_token(token)
        
        if not verify_token_type(payload, TokenType.ACCESS):
            return None
        
        email: Optional[str] = payload.get("sub")
        if email is None:
            return None
            
    except HTTPException:
        return None
    
    user = db.query(User).filter(User.email == email).first()
    
    if user is None or not user.is_active:
        return None
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify the current user is active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify the current user has verified their email.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Verified user
        
    Raises:
        HTTPException: If user email is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email address."
        )
    return current_user


# =============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC) DEPENDENCIES
# =============================================================================

def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify current user has admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def get_current_staff_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify current user is a staff member (any admin role).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Staff user
        
    Raises:
        HTTPException: If user is not staff
    """
    staff_roles = [r.value for r in Role.get_staff_roles()]
    
    if current_user.role not in staff_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff privileges required"
        )
    return current_user


def get_inventory_manager(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify current user can manage inventory.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User with inventory permissions
        
    Raises:
        HTTPException: If user lacks inventory permissions
    """
    allowed_roles = [Role.ADMIN.value, Role.INVENTORY_MANAGER.value]
    
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inventory management privileges required"
        )
    return current_user


def get_order_manager(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify current user can manage orders.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User with order management permissions
        
    Raises:
        HTTPException: If user lacks order permissions
    """
    allowed_roles = [
        Role.ADMIN.value, 
        Role.SALES_ADMIN.value, 
        Role.ORDER_VERIFIER.value
    ]
    
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Order management privileges required"
        )
    return current_user


class RoleChecker:
    """
    Flexible role checker dependency.
    
    Usage:
        @router.get("/protected")
        def protected_route(user: User = Depends(RoleChecker([Role.ADMIN, Role.SALES_ADMIN]))):
            return {"user": user.email}
    """
    
    def __init__(self, allowed_roles: list[Role]):
        self.allowed_roles = [r.value if isinstance(r, Role) else r for r in allowed_roles]
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(self.allowed_roles)}"
            )
        return current_user


# =============================================================================
# SECURITY HELPERS
# =============================================================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes (output will be longer due to base64)
        
    Returns:
        URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)


def check_password_strength(password: str) -> dict:
    """
    Check password strength and return feedback.
    
    Args:
        password: Password to check
        
    Returns:
        Dictionary with strength score and suggestions
    """
    import re
    
    score = 0
    suggestions = []
    
    if len(password) >= 8:
        score += 1
    else:
        suggestions.append("Use at least 8 characters")
    
    if len(password) >= 12:
        score += 1
    
    if re.search(r"[A-Z]", password):
        score += 1
    else:
        suggestions.append("Add uppercase letters")
    
    if re.search(r"[a-z]", password):
        score += 1
    else:
        suggestions.append("Add lowercase letters")
    
    if re.search(r"\d", password):
        score += 1
    else:
        suggestions.append("Add numbers")
    
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1
    else:
        suggestions.append("Add special characters")
    
    strength = "weak"
    if score >= 5:
        strength = "strong"
    elif score >= 3:
        strength = "medium"
    
    return {
        "score": score,
        "max_score": 6,
        "strength": strength,
        "suggestions": suggestions
    }


# Account lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def handle_failed_login(user: User, db: Session) -> None:
    """
    Handle a failed login attempt. 
    NOTE: Currently no-op since users table doesn't have failed_login_attempts column.
    """
    # DB doesn't have failed_login_attempts or locked_until columns
    pass


def handle_successful_login(user: User, db: Session) -> None:
    """
    Handle a successful login.
    NOTE: Currently no-op since users table doesn't have last_login column.
    """
    # DB doesn't have failed_login_attempts, locked_until, or last_login columns
    # Update last_seen_at instead if needed
    pass


def is_account_locked(user: User) -> bool:
    """
    Check if a user account is currently locked.
    NOTE: Currently always returns False since users table doesn't have locked_until column.
    """
    # DB doesn't have locked_until column
    return False
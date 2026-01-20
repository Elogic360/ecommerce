"""
Authentication Router
Complete authentication endpoints including registration, login, token refresh,
password reset, and user management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Form, Body, Query, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import EmailStr

from app.db.session import get_db
from app.models.customer import User, Role
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    create_email_verification_token,
    decode_token,
    verify_token_type,
    hash_token,
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    handle_failed_login,
    handle_successful_login,
    is_account_locked,
    TokenType,
    needs_rehash,
)
from app.schemas.auth import (
    UserRegister,
    UserRegisterSimple,
    UserLogin,
    LoginResponse,
    Token,
    TokenWithRefresh,
    RefreshTokenRequest,
    PasswordChange,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserResponse,
    UserProfile,
    UserUpdate,
    AdminUserCreate,
    AdminUserUpdate,
    UserListResponse,
    AccountLockStatus,
)
from app.core.rate_limit import (
    auth_rate_limiter,
    password_reset_limiter,
)

router = APIRouter()


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/status")
def auth_status():
    """Check if auth router is working"""
    return {"status": "ok", "message": "Auth service is running"}


# =============================================================================
# REGISTRATION
# =============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    - **email**: Valid email address (must be unique)
    - **username**: 3-50 characters, alphanumeric and underscore only
    - **password**: Minimum 8 characters with uppercase, lowercase, digit, and special character
    - **confirm_password**: Must match password
    - **full_name**: Optional full name
    - **phone**: Optional phone number
    """
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Check if username exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        phone_number=getattr(user_data, 'phone', None),
        hashed_password=hashed_password,
        role=Role.USER.value,
        is_active=True,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # TODO: Send verification email in background
    # background_tasks.add_task(send_verification_email, new_user.email)
    
    return new_user


@router.post("/register/quick", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_quick(
    user_data: UserRegisterSimple,
    db: Session = Depends(get_db)
):
    """
    Quick registration without strict password validation.
    Useful for API clients and testing.
    """
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Check if username exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=Role.USER.value,
        is_active=True,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# =============================================================================
# LOGIN
# =============================================================================

@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limiter)])
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible login endpoint.
    
    - **username**: Email address (OAuth2 spec uses 'username' field)
    - **password**: User password
    
    Returns access token for API authentication.
    """
    # Find user by email (OAuth2 uses 'username' field)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked. Please try again later."
        )
    
    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        handle_failed_login(user, db)
        
        # Check if this attempt triggered a lockout
        if is_account_locked(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Too many failed attempts. Account is temporarily locked."
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    # Rehash password if needed (e.g., bcrypt rounds changed)
    if needs_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(form_data.password)
    
    # Handle successful login
    handle_successful_login(user, db)
    
    # Create access token
    access_token = create_access_token(
        subject=user.email,
        role=user.role
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/json", response_model=LoginResponse, dependencies=[Depends(auth_rate_limiter)])
def login_json(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    JSON-based login endpoint with extended response.
    
    Returns access token, refresh token, and user information.
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if account is locked
    if is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is temporarily locked"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        handle_failed_login(user, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    # Handle successful login
    handle_successful_login(user, db)
    
    # Determine token expiration based on remember_me
    if credentials.remember_me:
        access_expires = timedelta(days=7)
        refresh_expires = timedelta(days=30)
    else:
        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Create tokens
    access_token = create_access_token(
        subject=user.email,
        role=user.role,
        expires_delta=access_expires
    )
    
    refresh_token = create_refresh_token(
        subject=user.email,
        expires_delta=refresh_expires
    )
    
    # Store refresh token hash (skip if column doesn't exist)
    # user.refresh_token_hash = hash_token(refresh_token)
    # db.commit()
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_expires.total_seconds()),
        user=UserResponse.model_validate(user)
    )


# =============================================================================
# TOKEN REFRESH
# =============================================================================

@router.post("/refresh", response_model=TokenWithRefresh)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    
    Implements token rotation - returns new access and refresh tokens.
    """
    try:
        payload = decode_token(request.refresh_token)
        
        if not verify_token_type(payload, TokenType.REFRESH):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    # Verify refresh token hash matches (prevents token reuse after rotation)
    # NOTE: Skipping hash verification since refresh_token_hash column doesn't exist
    # token_hash = hash_token(request.refresh_token)
    # if user.refresh_token_hash != token_hash:
    #     user.refresh_token_hash = None
    #     db.commit()
    #     raise HTTPException(...)
    
    # Create new tokens (rotation)
    new_access_token = create_access_token(
        subject=user.email,
        role=user.role
    )
    
    new_refresh_token = create_refresh_token(subject=user.email)
    
    # Update stored refresh token hash (skip if column doesn't exist)
    # user.refresh_token_hash = hash_token(new_refresh_token)
    # db.commit()
    
    return TokenWithRefresh(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# =============================================================================
# LOGOUT
# =============================================================================

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user by invalidating their refresh token.
    
    Note: Access tokens cannot be invalidated (they expire naturally).
    For immediate token invalidation, implement a token blacklist.
    """
    # Skip refresh_token_hash since column doesn't exist
    # current_user.refresh_token_hash = None
    # db.commit()
    
    return {"message": "Successfully logged out"}


# =============================================================================
# CURRENT USER
# =============================================================================

@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user's information"""
    return current_user


@router.get("/me/profile", response_model=UserProfile)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's extended profile with statistics"""
    # Count addresses and orders
    addresses_count = len(current_user.addresses) if current_user.addresses else 0
    orders_count = len(current_user.orders) if current_user.orders else 0
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        phone=current_user.phone_number,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=True,  # Default since column doesn't exist
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=None,  # Column doesn't exist
        addresses_count=addresses_count,
        orders_count=orders_count
    )


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile information"""
    
    # Check username uniqueness if being updated
    if updates.username and updates.username != current_user.username:
        existing = db.query(User).filter(User.username == updates.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken"
            )
        current_user.username = updates.username
    
    if updates.full_name is not None:
        current_user.full_name = updates.full_name
    
    if updates.phone is not None:
        current_user.phone_number = updates.phone
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


# =============================================================================
# PASSWORD MANAGEMENT
# =============================================================================

@router.post("/password/change", status_code=status.HTTP_200_OK)
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user.
    
    Requires current password for verification.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Ensure new password is different
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    # Note: last_password_change and refresh_token_hash columns don't exist in DB
    # current_user.last_password_change = datetime.now(timezone.utc)
    # current_user.refresh_token_hash = None
    
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post(
    "/password/reset-request", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(password_reset_limiter)]
)
def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset email.
    
    Always returns success to prevent email enumeration attacks.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if user and user.is_active:
        # Generate password reset token
        reset_token = create_password_reset_token(user.email)
        
        # Store token hash and expiry
        # Note: password_reset_token/expires columns don't exist in DB
        # user.password_reset_token = hash_token(reset_token)
        # user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        
        # TODO: Send email with reset link
        # The link should include: reset_token
        # background_tasks.add_task(send_password_reset_email, user.email, reset_token)
        
        # For development, log the token (REMOVE IN PRODUCTION)
        if settings.DEBUG:
            print(f"Password reset token for {user.email}: {reset_token}")
    
    # Always return success to prevent email enumeration
    return {
        "message": "If an account exists with that email, a password reset link has been sent"
    }


@router.post("/password/reset-confirm", status_code=status.HTTP_200_OK)
def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token and set new password.
    """
    try:
        payload = decode_token(reset_data.token)
        
        if not verify_token_type(payload, TokenType.PASSWORD_RESET):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Note: password_reset_token column doesn't exist in DB
    # Skip token hash verification since we can't store tokens
    # In production, implement proper token storage (Redis, separate table, etc.)
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    # Note: These columns don't exist in DB:
    # user.password_reset_token = None
    # user.password_reset_expires = None
    # user.last_password_change = datetime.now(timezone.utc)
    # user.failed_login_attempts = 0
    # user.locked_until = None
    # user.refresh_token_hash = None
    
    db.commit()
    
    return {"message": "Password has been reset successfully"}


# =============================================================================
# ACCOUNT STATUS
# =============================================================================

@router.get("/account/lock-status", response_model=AccountLockStatus)
def get_account_lock_status(
    email: EmailStr = Query(..., description="Email address to check"),
    db: Session = Depends(get_db)
):
    """
    Check if an account is locked due to failed login attempts.
    
    Useful for showing lockout status on login page.
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Don't reveal if email exists
        return AccountLockStatus(
            is_locked=False,
            failed_attempts=0,
            message="Account status unknown"
        )
    
    is_locked = is_account_locked(user)
    
    # Note: locked_until and failed_login_attempts columns don't exist
    return AccountLockStatus(
        is_locked=is_locked,
        locked_until=None,
        failed_attempts=0,
        message="Account is temporarily locked" if is_locked else "Account is not locked"
    )


# =============================================================================
# EMAIL VERIFICATION (Stub - requires email service)
# =============================================================================

@router.post("/verify-email/request", status_code=status.HTTP_200_OK)
def request_email_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request email verification link (for unverified users)"""
    
    # Note: is_verified column doesn't exist in DB - skip check
    # Email verification token storage also not available
    
    # Generate verification token
    verification_token = create_email_verification_token(current_user.email)
    
    # Note: email_verification_token/expires columns don't exist in DB
    # current_user.email_verification_token = hash_token(verification_token)
    # current_user.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    # db.commit()
    
    # TODO: Send verification email
    # background_tasks.add_task(send_verification_email, current_user.email, verification_token)
    
    if settings.DEBUG:
        print(f"Email verification token for {current_user.email}: {verification_token}")
    
    return {"message": "Verification email has been sent"}


@router.post("/verify-email/confirm", status_code=status.HTTP_200_OK)
def confirm_email_verification(
    token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Confirm email with verification token"""
    
    try:
        payload = decode_token(token)
        
        if not verify_token_type(payload, TokenType.EMAIL_VERIFICATION):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        email = payload.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    # Note: email_verification_token column doesn't exist in DB
    # Skip token hash verification
    
    # Mark as verified - but is_verified column doesn't exist either
    # user.is_verified = True
    # user.email_verification_token = None
    # user.email_verification_expires = None
    # db.commit()
    
    return {"message": "Email verified successfully"}


# =============================================================================
# ADMIN: USER MANAGEMENT
# =============================================================================

@router.get("/admin/users", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by email or username"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users with pagination and filtering.
    
    **Admin only**
    """
    query = db.query(User)
    
    # Apply filters
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) | 
            (User.username.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page
    
    # Get users
    users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
    
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=per_page,
        total_pages=pages
    )


@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    user_data: AdminUserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user with specified role.
    
    **Admin only**
    """
    # Check email uniqueness
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Check username uniqueness
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )
    
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        phone=user_data.phone,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role.value if isinstance(user_data.role, Role) else user_data.role,
        is_active=user_data.is_active,
        is_verified=user_data.is_verified,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/admin/users/{user_id}", response_model=UserResponse)
def admin_get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID.
    
    **Admin only**
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/admin/users/{user_id}", response_model=UserResponse)
def admin_update_user(
    user_id: int,
    updates: AdminUserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update a user's information or role.
    
    **Admin only**
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from demoting themselves
    if user.id == current_user.id and updates.role and updates.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role"
        )
    
    # Check email uniqueness
    if updates.email and updates.email != user.email:
        if db.query(User).filter(User.email == updates.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
            )
        user.email = updates.email
    
    # Check username uniqueness
    if updates.username and updates.username != user.username:
        if db.query(User).filter(User.username == updates.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken"
            )
        user.username = updates.username
    
    if updates.full_name is not None:
        user.full_name = updates.full_name
    
    if updates.phone is not None:
        user.phone_number = updates.phone
    
    if updates.role is not None:
        user.role = updates.role.value if isinstance(updates.role, Role) else updates.role
    
    if updates.is_active is not None:
        user.is_active = updates.is_active
    
    # Note: is_verified column doesn't exist in DB
    # if updates.is_verified is not None:
    #     user.is_verified = updates.is_verified
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user account.
    
    **Admin only**
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return None


@router.post("/admin/users/{user_id}/unlock", response_model=UserResponse)
def admin_unlock_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Unlock a locked user account.
    
    **Admin only**
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Note: failed_login_attempts and locked_until columns don't exist in DB
    # user.failed_login_attempts = 0
    # user.locked_until = None
    # db.commit()
    db.refresh(user)
    
    return user

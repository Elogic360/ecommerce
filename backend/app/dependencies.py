"""
Dependency Injection Module
Database sessions and authentication dependencies for FastAPI routes.

This module re-exports security dependencies for backward compatibility
and provides database session management.
"""
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.customer import User, Role

# Re-export security dependencies from core.security
# This maintains backward compatibility with existing imports
from app.core.security import (
    # OAuth2 schemes
    oauth2_scheme,
    oauth2_scheme_optional,
    
    # User authentication dependencies
    get_current_user,
    get_current_user_optional,
    get_current_active_user,
    get_current_verified_user,
    
    # Role-based access control dependencies
    get_current_admin_user,
    get_current_staff_user,
    get_inventory_manager,
    get_order_manager,
    RoleChecker,
    
    # Password utilities
    verify_password,
    get_password_hash,
    check_password_strength,
    
    # Token utilities
    create_access_token,
    create_refresh_token,
    decode_token,
)


# =============================================================================
# DATABASE SESSION DEPENDENCY
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Yields a database session and ensures it's closed after use.
    Use with FastAPI's Depends():
    
    Example:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# CONVENIENCE DEPENDENCIES
# =============================================================================

def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    
    This is an alias for get_current_user_optional for backward compatibility.
    Use for endpoints that work both with and without authentication.
    
    Example:
        @router.get("/products")
        def list_products(user: Optional[User] = Depends(get_optional_current_user)):
            if user:
                return get_personalized_products(user)
            return get_public_products()
    
    Args:
        token: Optional JWT access token
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    return get_current_user_optional(token=token, db=db)


# =============================================================================
# ROLE-SPECIFIC DEPENDENCIES
# =============================================================================

def require_role(*roles: Role):
    """
    Factory function to create a dependency that requires specific roles.
    
    Usage:
        @router.get("/admin/reports")
        def get_reports(user: User = Depends(require_role(Role.ADMIN, Role.SALES_ADMIN))):
            return generate_reports()
    
    Args:
        *roles: One or more Role enum values that are allowed
        
    Returns:
        Dependency function that validates user has one of the specified roles
    """
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        allowed_roles = [r.value if isinstance(r, Role) else r for r in roles]
        
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_dependency


def require_any_staff_role(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires user to have any staff role.
    
    Staff roles include: ADMIN, INVENTORY_MANAGER, SALES_ADMIN, ORDER_VERIFIER, TRANSPORTER
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if they have a staff role
        
    Raises:
        HTTPException: If user is not staff
    """
    staff_roles = [r.value for r in Role.get_staff_roles()]
    
    if current_user.role not in staff_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user


# =============================================================================
# RESOURCE OWNERSHIP DEPENDENCIES
# =============================================================================

class ResourceOwnerChecker:
    """
    Dependency class to verify resource ownership.
    
    Allows access if user owns the resource OR has admin privileges.
    
    Usage:
        @router.get("/orders/{order_id}")
        def get_order(
            order_id: int,
            order: Order = Depends(get_order_by_id),
            user: User = Depends(ResourceOwnerChecker("user_id"))
        ):
            return order
    """
    
    def __init__(self, owner_field: str = "user_id", allow_admin: bool = True):
        """
        Initialize the resource owner checker.
        
        Args:
            owner_field: Name of the field containing the owner's user ID
            allow_admin: Whether to allow admin users regardless of ownership
        """
        self.owner_field = owner_field
        self.allow_admin = allow_admin
    
    def __call__(
        self,
        resource: any,
        current_user: User = Depends(get_current_user)
    ) -> User:
        """
        Check if current user owns the resource or is admin.
        
        Args:
            resource: The resource object to check ownership of
            current_user: Current authenticated user
            
        Returns:
            Current user if authorized
            
        Raises:
            HTTPException: If user doesn't own resource and isn't admin
        """
        # Allow admin users if configured
        if self.allow_admin and current_user.role == Role.ADMIN.value:
            return current_user
        
        # Check ownership
        owner_id = getattr(resource, self.owner_field, None)
        
        if owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource"
            )
        
        return current_user


# =============================================================================
# PAGINATION DEPENDENCIES
# =============================================================================

class PaginationParams:
    """
    Common pagination parameters.
    
    Usage:
        @router.get("/items")
        def list_items(
            pagination: PaginationParams = Depends(),
            db: Session = Depends(get_db)
        ):
            return db.query(Item).offset(pagination.skip).limit(pagination.limit).all()
    """
    
    def __init__(
        self,
        page: int = 1,
        per_page: int = 20,
        max_per_page: int = 100
    ):
        """
        Initialize pagination parameters.
        
        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            max_per_page: Maximum allowed items per page
        """
        self.page = max(1, page)
        self.per_page = min(max(1, per_page), max_per_page)
        self.skip = (self.page - 1) * self.per_page
        self.limit = self.per_page
    
    def paginate_query(self, query):
        """Apply pagination to a SQLAlchemy query."""
        return query.offset(self.skip).limit(self.limit)
    
    def get_pagination_info(self, total: int) -> dict:
        """Get pagination metadata."""
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": total,
            "pages": (total + self.per_page - 1) // self.per_page
        }

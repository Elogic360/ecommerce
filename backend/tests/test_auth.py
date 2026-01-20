"""
Authentication Tests
Comprehensive tests for all authentication and authorization flows.

Run with: pytest tests/test_auth.py -v
"""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.customer import User, Role
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)

# =============================================================================
# TEST DATABASE SETUP
# =============================================================================

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db):
    """Create a test user"""
    user = User(
        email="testuser@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("TestPass123!"),
        role=Role.USER.value,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    user = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("AdminPass123!"),
        role=Role.ADMIN.value,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(test_user):
    """Get access token for test user"""
    return create_access_token(subject=test_user.email, role=test_user.role)


@pytest.fixture
def admin_token(admin_user):
    """Get access token for admin user"""
    return create_access_token(subject=admin_user.email, role=admin_user.role)


# =============================================================================
# PASSWORD HASHING TESTS
# =============================================================================

class TestPasswordHashing:
    """Tests for password hashing functions"""
    
    def test_password_hash_is_different(self):
        """Password hash should not equal plain password"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        assert hashed != password
    
    def test_password_hash_is_unique(self):
        """Same password should produce different hashes"""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2  # Salt makes each hash unique
    
    def test_password_verification_correct(self):
        """Correct password should verify"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
    
    def test_password_verification_incorrect(self):
        """Incorrect password should not verify"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        assert verify_password("WrongPassword123!", hashed) is False
    
    def test_password_verification_empty(self):
        """Empty password should not verify"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        assert verify_password("", hashed) is False


# =============================================================================
# TOKEN TESTS
# =============================================================================

class TestTokens:
    """Tests for JWT token functions"""
    
    def test_create_access_token(self):
        """Access token should be created successfully"""
        token = create_access_token(subject="test@example.com")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_access_token(self):
        """Access token should decode correctly"""
        email = "test@example.com"
        token = create_access_token(subject=email, role="user")
        payload = decode_token(token)
        assert payload["sub"] == email
        assert payload["type"] == "access"
        assert payload["role"] == "user"
    
    def test_create_refresh_token(self):
        """Refresh token should be created successfully"""
        token = create_refresh_token(subject="test@example.com")
        assert token is not None
        assert isinstance(token, str)
    
    def test_decode_refresh_token(self):
        """Refresh token should decode correctly"""
        email = "test@example.com"
        token = create_refresh_token(subject=email)
        payload = decode_token(token)
        assert payload["sub"] == email
        assert payload["type"] == "refresh"
        assert "jti" in payload  # Unique token ID
    
    def test_token_with_custom_expiry(self):
        """Token should respect custom expiry"""
        token = create_access_token(
            subject="test@example.com",
            expires_delta=timedelta(hours=2)
        )
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Should expire approximately 2 hours from now
        assert (exp - now).total_seconds() > 7000  # ~2 hours minus small buffer


# =============================================================================
# REGISTRATION TESTS
# =============================================================================

class TestRegistration:
    """Tests for user registration"""
    
    def test_register_success(self, client, db):
        """User should register successfully with valid data"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "New User"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["role"] == "user"
    
    def test_register_duplicate_email(self, client, test_user):
        """Registration should fail with duplicate email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "different",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_duplicate_username(self, client, test_user):
        """Registration should fail with duplicate username"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()
    
    def test_register_password_mismatch(self, client, db):
        """Registration should fail when passwords don't match"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "confirm_password": "DifferentPass123!"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_register_weak_password(self, client, db):
        """Registration should fail with weak password"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "weak",
                "confirm_password": "weak"
            }
        )
        assert response.status_code == 422
    
    def test_register_invalid_email(self, client, db):
        """Registration should fail with invalid email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "username": "newuser",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
        )
        assert response.status_code == 422


# =============================================================================
# LOGIN TESTS
# =============================================================================

class TestLogin:
    """Tests for user login"""
    
    def test_login_success(self, client, test_user):
        """User should login successfully with correct credentials"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "TestPass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, test_user):
        """Login should fail with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client, db):
        """Login should fail for non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!"
            }
        )
        assert response.status_code == 401
    
    def test_login_inactive_user(self, client, db):
        """Login should fail for inactive user"""
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=False,
            role=Role.USER.value
        )
        db.add(inactive_user)
        db.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "inactive@example.com",
                "password": "TestPass123!"
            }
        )
        assert response.status_code == 403
    
    def test_login_json_endpoint(self, client, test_user):
        """JSON login endpoint should return extended response"""
        response = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
                "remember_me": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == test_user.email


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class TestAuthentication:
    """Tests for authentication and protected routes"""
    
    def test_get_current_user(self, client, test_user, user_token):
        """Should get current user info with valid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
    
    def test_get_current_user_no_token(self, client):
        """Should fail without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client):
        """Should fail with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401
    
    def test_get_current_user_expired_token(self, client, test_user):
        """Should fail with expired token"""
        expired_token = create_access_token(
            subject=test_user.email,
            expires_delta=timedelta(seconds=-1)
        )
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401


# =============================================================================
# TOKEN REFRESH TESTS
# =============================================================================

class TestTokenRefresh:
    """Tests for token refresh functionality"""
    
    def test_refresh_token_success(self, client, test_user, db):
        """Should refresh tokens successfully"""
        # First, login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": test_user.email,
                "password": "TestPass123!"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh the token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != login_response.json()["access_token"]
    
    def test_refresh_token_invalid(self, client, db):
        """Should fail with invalid refresh token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401
    
    def test_refresh_token_reuse_detection(self, client, test_user, db):
        """Should detect refresh token reuse (rotation)"""
        # Login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": test_user.email,
                "password": "TestPass123!"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token once
        first_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert first_refresh.status_code == 200
        
        # Try to reuse the old refresh token
        second_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert second_refresh.status_code == 401


# =============================================================================
# PASSWORD MANAGEMENT TESTS
# =============================================================================

class TestPasswordManagement:
    """Tests for password change and reset"""
    
    def test_change_password_success(self, client, test_user, user_token):
        """Should change password successfully"""
        response = client.post(
            "/api/v1/auth/password/change",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
    
    def test_change_password_wrong_current(self, client, test_user, user_token):
        """Should fail with wrong current password"""
        response = client.post(
            "/api/v1/auth/password/change",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecurePass456!",
                "confirm_password": "NewSecurePass456!"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 400
    
    def test_change_password_same_password(self, client, test_user, user_token):
        """Should fail when new password is same as current"""
        response = client.post(
            "/api/v1/auth/password/change",
            json={
                "current_password": "TestPass123!",
                "new_password": "TestPass123!",
                "confirm_password": "TestPass123!"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 400
    
    def test_password_reset_request(self, client, test_user):
        """Should handle password reset request"""
        response = client.post(
            "/api/v1/auth/password/reset-request",
            json={"email": test_user.email}
        )
        # Should always return 200 to prevent email enumeration
        assert response.status_code == 200
    
    def test_password_reset_nonexistent_email(self, client, db):
        """Should return 200 even for non-existent email"""
        response = client.post(
            "/api/v1/auth/password/reset-request",
            json={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 200


# =============================================================================
# AUTHORIZATION TESTS (RBAC)
# =============================================================================

class TestAuthorization:
    """Tests for role-based access control"""
    
    def test_admin_access_admin_route(self, client, admin_user, admin_token):
        """Admin should access admin routes"""
        response = client.get(
            "/api/v1/auth/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_user_denied_admin_route(self, client, test_user, user_token):
        """Regular user should be denied admin routes"""
        response = client.get(
            "/api/v1/auth/admin/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
    
    def test_admin_create_user(self, client, admin_user, admin_token, db):
        """Admin should be able to create users"""
        response = client.post(
            "/api/v1/auth/admin/users",
            json={
                "email": "created@example.com",
                "username": "createduser",
                "password": "Password123!",
                "role": "user",
                "is_active": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "created@example.com"
    
    def test_admin_update_user_role(self, client, test_user, admin_token, db):
        """Admin should be able to update user roles"""
        response = client.patch(
            f"/api/v1/auth/admin/users/{test_user.id}",
            json={"role": "inventory_manager"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "inventory_manager"
    
    def test_admin_cannot_demote_self(self, client, admin_user, admin_token):
        """Admin should not be able to remove their own admin role"""
        response = client.patch(
            f"/api/v1/auth/admin/users/{admin_user.id}",
            json={"role": "user"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400


# =============================================================================
# LOGOUT TESTS
# =============================================================================

class TestLogout:
    """Tests for logout functionality"""
    
    def test_logout_success(self, client, test_user, user_token, db):
        """Should logout successfully"""
        # First login to set refresh token
        client.post(
            "/api/v1/auth/login/json",
            json={
                "email": test_user.email,
                "password": "TestPass123!"
            }
        )
        
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
    
    def test_logout_without_auth(self, client):
        """Should fail logout without authentication"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401


# =============================================================================
# ACCOUNT LOCKOUT TESTS
# =============================================================================

class TestAccountLockout:
    """Tests for account lockout functionality"""
    
    def test_account_locks_after_failed_attempts(self, client, test_user, db):
        """Account should lock after too many failed attempts"""
        # Make multiple failed login attempts
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.email,
                    "password": "WrongPassword123!"
                }
            )
        
        # Next attempt should be blocked
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "TestPass123!"  # Even correct password
            }
        )
        assert response.status_code == 403
        assert "locked" in response.json()["detail"].lower()
    
    def test_check_lock_status(self, client, test_user, db):
        """Should be able to check account lock status"""
        response = client.get(
            f"/api/v1/auth/account/lock-status?email={test_user.email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_locked" in data
        assert "failed_attempts" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

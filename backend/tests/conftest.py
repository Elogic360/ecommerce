"""
Pytest Configuration
Fixtures and configuration for running tests.
"""
import pytest  # type: ignore[import-not-found]
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.customer import User, Role
from app.core.security import get_password_hash, create_access_token


# =============================================================================
# TEST DATABASE
# =============================================================================

# Use in-memory SQLite for testing
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


# Apply the override
app.dependency_overrides[get_db] = override_get_db


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.
    Tables are created before the test and dropped after.
    """
    # Import all models to ensure they're registered with Base
    from app.models import customer, product, order, cart, inventory_log, payment
    
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database session"""
    return TestClient(app)


@pytest.fixture
def test_user(db):
    """Create a standard test user"""
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
    """Create an admin test user"""
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
def inventory_manager(db):
    """Create an inventory manager test user"""
    user = User(
        email="inventory@example.com",
        username="inventory_mgr",
        full_name="Inventory Manager",
        hashed_password=get_password_hash("InventoryPass123!"),
        role=Role.INVENTORY_MANAGER.value,
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


@pytest.fixture
def inventory_token(inventory_manager):
    """Get access token for inventory manager"""
    return create_access_token(subject=inventory_manager.email, role=inventory_manager.role)


@pytest.fixture
def auth_headers(user_token):
    """Get authentication headers for test user"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Get authentication headers for admin user"""
    return {"Authorization": f"Bearer {admin_token}"}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_test_user(
    db,
    email: str = "user@example.com",
    username: str = "user",
    password: str = "Password123!",
    role: str = Role.USER.value,
    is_active: bool = True,
    is_verified: bool = True
) -> User:
    """Helper function to create a test user with custom parameters"""
    user = User(
        email=email,
        username=username,
        full_name=f"Test {username}",
        hashed_password=get_password_hash(password),
        role=role,
        is_active=is_active,
        is_verified=is_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

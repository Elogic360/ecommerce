#!/usr/bin/env python3
"""
Test script to verify bcrypt hashing and check if admin password matches 'admin123'.
"""

import bcrypt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.db.base import Base
from app.models.customer import User
from app.core.security import verify_password, get_password_hash

def test_bcrypt_functionality():
    """Test that bcrypt hashing and verification works."""
    test_password = "test123"
    hashed = get_password_hash(test_password)
    print(f"Test password: {test_password}")
    print(f"Hashed: {hashed}")
    
    # Verify it matches
    if verify_password(test_password, hashed):
        print("✅ Bcrypt hashing and verification working correctly.")
    else:
        print("❌ Bcrypt verification failed.")
    
    # Test with wrong password
    if not verify_password("wrong", hashed):
        print("✅ Bcrypt correctly rejects wrong password.")
    else:
        print("❌ Bcrypt incorrectly accepts wrong password.")

def check_admin_password():
    """Check if the admin password hash matches 'admin123'."""
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        admin_user = db.query(User).filter(User.email == "admin@shophub.com").first()
        if admin_user:
            print(f"Admin user found: {admin_user.email}")
            print(f"Stored hashed password: {admin_user.hashed_password}")
            
            # Check if 'admin123' matches
            if verify_password("admin123", admin_user.hashed_password):
                print("✅ Admin password matches 'admin123'.")
            else:
                print("❌ Admin password does not match 'admin123'.")
        else:
            print("❌ No admin user found.")
        db.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Testing bcrypt functionality...")
    test_bcrypt_functionality()
    print("\nChecking admin password...")
    check_admin_password()
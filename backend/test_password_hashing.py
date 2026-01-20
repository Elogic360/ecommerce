#!/usr/bin/env python3
"""
Test script to verify password hashing and verification works correctly with admin credentials.
"""

import bcrypt
from app.db.session import SessionLocal
from app.models.customer import User

def test_password_hashing():
    """Test basic password hashing and verification."""
    plain_password = b"testpassword123"
    hashed = bcrypt.hashpw(plain_password, bcrypt.gensalt())
    print(f"Plain password: {plain_password.decode()}")
    print(f"Hashed password: {hashed.decode()}")
    
    # Verify correct password
    if bcrypt.checkpw(plain_password, hashed):
        print("✅ Password verification successful for correct password")
    else:
        print("❌ Password verification failed for correct password")
    
    # Verify wrong password
    if not bcrypt.checkpw(b"wrongpassword", hashed):
        print("✅ Correctly rejects wrong password")
    else:
        print("❌ Incorrectly accepts wrong password")

def test_admin_credentials():
    """Test verification with admin credentials from database."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@shophub.com").first()
        if not admin:
            print("❌ Admin user not found in database")
            return
        
        print(f"Admin email: {admin.email}")
        print(f"Admin hashed password: {admin.hashed_password}")
        
        # Test with correct password
        if bcrypt.checkpw(b"admin123", admin.hashed_password.encode()):
            print("✅ Admin password verification successful")
        else:
            print("❌ Admin password verification failed")
        
        # Test with wrong password
        if not bcrypt.checkpw(b"wrongadminpass", admin.hashed_password.encode()):
            print("✅ Correctly rejects wrong admin password")
        else:
            print("❌ Incorrectly accepts wrong admin password")
    
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing password hashing and verification...")
    test_password_hashing()
    print("\nTesting admin credentials...")
    test_admin_credentials()
    print("\nTest completed.")
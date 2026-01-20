#!/usr/bin/env python3
"""
Test the new security functions.
"""

from app.core.security import verify_password, get_password_hash

# Test hashing
password = "admin123"
hash = get_password_hash(password)
print(f"New hash for admin123: {hash}")

# Test verify
if verify_password(password, hash):
    print("✅ New hash verifies")
else:
    print("❌ New hash fails")

# Test with DB hash
db_hash = "$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyB9q9gqKZTG"
if verify_password(password, db_hash):
    print("✅ DB hash matches admin123")
else:
    print("❌ DB hash does not match admin123")
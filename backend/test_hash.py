#!/usr/bin/env python3
"""
Test hashing with passlib.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

password = "admin123"
hash = pwd_context.hash(password)
print(f"Hash for admin123: {hash}")

# Verify
if pwd_context.verify(password, hash):
    print("✅ Verify works for new hash")
else:
    print("❌ Verify fails for new hash")

# Try with the DB hash
db_hash = "$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyB9q9gqKZTG"
if pwd_context.verify(password, db_hash):
    print("✅ DB hash matches admin123")
else:
    print("❌ DB hash does not match admin123")
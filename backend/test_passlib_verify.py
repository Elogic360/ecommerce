#!/usr/bin/env python3
"""
Test password verification with passlib.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt", "sha256_crypt"], deprecated="auto")

hashed_password = "$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyB9q9gqKZTG"
plain_password = "admin123"

if pwd_context.verify(plain_password, hashed_password):
    print("✅ Password verification successful with passlib")
else:
    print("❌ Password verification failed with passlib")
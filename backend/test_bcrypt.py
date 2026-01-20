#!/usr/bin/env python3
"""
Test bcrypt directly.
"""

import bcrypt

hashed = b"$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyB9q9gqKZTG"
password = b"admin123"

if bcrypt.checkpw(password, hashed):
    print("✅ Matches")
else:
    print("❌ Does not match")

# Let's see what the hash of admin123 is
new_hash = bcrypt.hashpw(password, bcrypt.gensalt())
print(f"New hash for admin123: {new_hash}")
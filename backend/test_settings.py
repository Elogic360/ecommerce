#!/usr/bin/env python3
"""Test script to verify settings configuration"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.core.config import settings
    print("✅ Settings loaded successfully!")
    print(f"   App Name: {settings.APP_NAME}")
    print(f"   Database URL: {settings.DATABASE_URL}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   Upload Dir: {settings.UPLOAD_DIR}")
    print(f"   CORS Origins: {settings.ALLOWED_ORIGINS}")
    print("✅ All configuration settings are working!")
except Exception as e:
    print(f"❌ Error loading settings: {e}")
    sys.exit(1)
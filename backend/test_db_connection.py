"""Test PostgreSQL database connection using settings from .env file."""

from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv; load_dotenv()

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from app.core.config import settings


def test_connection():
    """Test database connection."""
    print(f"Testing connection to: {settings.DATABASE_URL}")
    print("-" * 60)
    
    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print("✓ Connection successful!")
            print(f"\nPostgreSQL version:\n{version}")
            
            # Test database info
            result = conn.execute(text("SELECT current_database(), current_user"))
            db_info = result.fetchone()
            print(f"\nCurrent database: {db_info[0]}")
            print(f"Current user: {db_info[1]}")
            
            # Test basic query
            result = conn.execute(text("SELECT 1 + 1 as result"))
            print(f"\nTest query (1+1): {result.fetchone()[0]}")
            
        print("\n" + "=" * 60)
        print("✓ All database tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed!")
        print(f"\nError: {e}")
        print("\n" + "=" * 60)
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running: sudo systemctl status postgresql")
        print("2. Check if database exists: sudo -u postgres psql -c '\\l'")
        print("3. Verify .env file settings in backend/.env")
        print("4. Check pg_hba.conf authentication method")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

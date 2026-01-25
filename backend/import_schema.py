import psycopg2
import sys
import os
from dotenv import load_dotenv

# Add backend dir to path to import settings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

def run_sql_schema(file_path):
    print(f"📖 Reading schema from {file_path}...")
    try:
        with open(file_path, 'r') as f:
            sql = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    db_url = settings.DATABASE_URL
    # Fix for Render/Heroku postgres:// vs postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    print(f"🔌 Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("🚀 Executing schema commands...")
        # Split by semicolon to run blocks if needed, but simple execute might work
        cur.execute(sql)
        
        print("✅ Schema imported successfully!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("\nNote: If you see 'Connection Refused', ensure you are using the EXTERNAL database URL from Render, not the Internal one.")

if __name__ == "__main__":
    schema_path = "database_schema02.sql"
    if not os.path.exists(schema_path):
        print(f"❌ Schema file not found: {schema_path}")
        sys.exit(1)
    
    run_sql_schema(schema_path)

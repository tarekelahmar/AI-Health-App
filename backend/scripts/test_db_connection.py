#!/usr/bin/env python3
"""
Test database connection and run migrations.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import get_settings
import psycopg2

def test_connection():
    """Test database connection."""
    print("🔌 Testing database connection...")
    settings = get_settings()
    db_url = settings.DATABASE_URL
    
    # Parse connection string for display (hide password)
    if '@' in db_url:
        parts = db_url.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split('://')[1] if '://' in parts[0] else parts[0]
            if ':' in user_pass:
                user = user_pass.split(':')[0]
                print(f"   User: {user}")
        host_db = parts[1] if len(parts) > 1 else ""
        print(f"   Host: {host_db.split('/')[0] if '/' in host_db else host_db}")
    
    try:
        print("   Attempting to connect (this may take a moment)...")
        # Set a connection timeout
        conn = psycopg2.connect(db_url, connect_timeout=10)
        print("✅ Database connection successful!")
        
        # Test a simple query
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"   PostgreSQL version: {version.split(',')[0]}")
            
            # Check if users table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """)
            users_exists = cur.fetchone()[0]
            
            if users_exists:
                print("✅ 'users' table exists")
                
                # Check if hashed_password column exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'users' 
                        AND column_name = 'hashed_password'
                    );
                """)
                has_password_col = cur.fetchone()[0]
                
                if has_password_col:
                    print("✅ 'hashed_password' column exists")
                else:
                    print("⚠️  'hashed_password' column missing - migration needed")
            else:
                print("⚠️  'users' table does not exist - may need to run migrations")
        
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Possible issues:")
        print("1. Database server is not accessible (check AWS RDS security groups)")
        print("2. Network/firewall blocking port 5432")
        print("3. Database credentials are incorrect")
        print("4. VPN connection required")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)


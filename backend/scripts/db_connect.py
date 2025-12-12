#!/usr/bin/env python3
"""
Connect to PostgreSQL database and run SQL commands.
Usage:
    python scripts/db_connect.py
    python scripts/db_connect.py "SELECT * FROM users LIMIT 5;"
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

def connect_to_db():
    """Connect to the database using settings."""
    settings = get_settings()
    db_url = settings.DATABASE_URL
    
    # Parse connection string
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://', 1)
    
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def run_query(conn, query: str):
    """Run a SQL query and return results."""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            if query.strip().upper().startswith('SELECT'):
                results = cur.fetchall()
                return results
            else:
                conn.commit()
                return {"rows_affected": cur.rowcount}
    except Exception as e:
        conn.rollback()
        print(f"❌ Query failed: {e}")
        return None

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Run provided SQL query
        query = sys.argv[1]
        conn = connect_to_db()
        print(f"🔌 Connected to database")
        print(f"📝 Running query: {query[:100]}...")
        print()
        results = run_query(conn, query)
        if results:
            if isinstance(results, list):
                if results:
                    print(f"✅ Found {len(results)} rows:")
                    print()
                    for row in results:
                        print(dict(row))
                else:
                    print("✅ Query executed, no rows returned")
            else:
                print(f"✅ {results}")
        conn.close()
    else:
        # Interactive mode
        print("🔌 Connecting to database...")
        conn = connect_to_db()
        print("✅ Connected!")
        print()
        print("Enter SQL queries (type 'exit' or 'quit' to leave):")
        print()
        
        while True:
            try:
                query = input("sql> ").strip()
                if query.lower() in ('exit', 'quit', 'q'):
                    break
                if not query:
                    continue
                if query.endswith(';'):
                    query = query[:-1]
                
                results = run_query(conn, query)
                if results:
                    if isinstance(results, list):
                        if results:
                            print(f"✅ {len(results)} rows:")
                            for row in results:
                                print(dict(row))
                        else:
                            print("✅ No rows returned")
                    else:
                        print(f"✅ {results}")
                print()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}\n")
        
        conn.close()
        print("👋 Disconnected")

if __name__ == "__main__":
    main()


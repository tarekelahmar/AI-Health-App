#!/usr/bin/env python3
"""
Helper script to update DATABASE_URL in .env file.
Usage:
    python3 scripts/update_database_url.py "postgresql://user:password@host:5432/dbname"
"""
import sys
import os
from pathlib import Path

def update_env_file(db_url: str):
    """Update DATABASE_URL in .env file."""
    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / ".env"
    
    if not env_file.exists():
        print(f"❌ .env file not found at {env_file}")
        print("   Creating new .env file from env.example...")
        example_file = backend_dir / "env.example"
        if example_file.exists():
            env_file.write_text(example_file.read_text())
        else:
            print("   env.example also not found. Please create .env manually.")
            return False
    
    # Read current .env
    lines = env_file.read_text().splitlines()
    
    # Find and update DATABASE_URL
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={db_url}")
            updated = True
            print(f"✅ Updated DATABASE_URL")
        else:
            new_lines.append(line)
    
    # If not found, add it
    if not updated:
        new_lines.append(f"DATABASE_URL={db_url}")
        print(f"✅ Added DATABASE_URL")
    
    # Write back
    env_file.write_text("\n".join(new_lines) + "\n")
    
    # Verify
    print()
    print("📝 Updated .env file:")
    print(f"   DATABASE_URL={db_url.split('@')[0].split('://')[0]}://***@***")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/update_database_url.py <DATABASE_URL>")
        print()
        print("Example:")
        print('  python3 scripts/update_database_url.py "postgresql://user:password@host:5432/dbname"')
        sys.exit(1)
    
    db_url = sys.argv[1]
    
    if not db_url.startswith(("postgresql://", "postgres://")):
        print("❌ DATABASE_URL must start with postgresql:// or postgres://")
        sys.exit(1)
    
    if update_env_file(db_url):
        print()
        print("✅ Database URL updated successfully!")
        print()
        print("Next steps:")
        print("1. Test connection: python3 scripts/test_db_connection.py")
        print("2. Run migration: python3 scripts/run_migration.py")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()


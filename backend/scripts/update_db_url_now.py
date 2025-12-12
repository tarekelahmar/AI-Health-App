#!/usr/bin/env python3
"""Update DATABASE_URL in .env file with the new public database."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
env_file = backend_dir / ".env"
new_db_url = "postgresql://postgres:Watdehell1-@health-app-db-dev-public.c5c224qc6drg.eu-north-1.rds.amazonaws.com:5432/health_app?sslmode=require"

print("🔧 Updating DATABASE_URL in .env file...")
print()

if not env_file.exists():
    print(f"Creating .env file...")
    env_file.write_text(f"DATABASE_URL={new_db_url}\n")
    print("✅ Created .env file with new DATABASE_URL")
else:
    lines = env_file.read_text().splitlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={new_db_url}")
            updated = True
            print("✅ Found and updated existing DATABASE_URL")
        else:
            new_lines.append(line)
    
    if not updated:
        new_lines.append(f"DATABASE_URL={new_db_url}")
        print("✅ Added DATABASE_URL (was not present)")
    
    env_file.write_text("\n".join(new_lines) + "\n")

print()
print("✅ Database URL updated successfully!")
print()
print("New endpoint: health-app-db-dev-public.c5c224qc6drg.eu-north-1.rds.amazonaws.com")
print()
print("Next steps:")
print("1. Test connection: python3 scripts/test_db_connection.py")
print("2. Run migration: python3 scripts/run_migration.py")


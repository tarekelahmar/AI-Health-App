#!/usr/bin/env python3
"""
Run Alembic migration to add hashed_password column.
"""
import sys
import os
import subprocess
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def run_migration():
    """Run the Alembic migration."""
    print("🔄 Running database migration...")
    print()
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    # Check if migration exists
    migration_file = backend_dir / "app" / "migrations" / "versions" / "add_hashed_password_to_users.py"
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"✅ Found migration file: {migration_file.name}")
    print()
    
    # Run alembic upgrade
    try:
        print("Running: alembic upgrade head")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("❌ Migration failed:")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Migration timed out")
        return False
    except FileNotFoundError:
        print("❌ Alembic not found. Make sure it's installed:")
        print("   pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)


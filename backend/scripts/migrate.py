#!/usr/bin/env python3
"""
Migration script wrapper for Alembic.

This script provides a convenient way to run Alembic migrations
without needing to remember the exact commands.

Usage:
    python scripts/migrate.py create "message"    # Create new migration
    python scripts/migrate.py upgrade              # Apply all pending migrations
    python scripts/migrate.py upgrade head         # Apply all migrations to latest
    python scripts/migrate.py downgrade -1        # Rollback one migration
    python scripts/migrate.py current             # Show current migration
    python scripts/migrate.py history             # Show migration history
"""
import sys
import subprocess
from pathlib import Path

# Get the backend directory (parent of scripts)
BACKEND_DIR = Path(__file__).parent.parent


def run_alembic_command(args: list[str]) -> int:
    """Run an Alembic command with proper configuration."""
    cmd = ["alembic"] + args
    return subprocess.run(cmd, cwd=BACKEND_DIR).returncode


def create_migration(message: str) -> int:
    """Create a new migration with autogenerate."""
    if not message:
        print("Error: Migration message is required")
        print("Usage: python scripts/migrate.py create \"your message here\"")
        return 1
    
    print(f"Creating migration: {message}")
    return run_alembic_command([
        "revision",
        "--autogenerate",
        "-m",
        message
    ])


def upgrade_migration(target: str = "head") -> int:
    """Apply migrations."""
    print(f"Upgrading database to: {target}")
    return run_alembic_command(["upgrade", target])


def downgrade_migration(target: str = "-1") -> int:
    """Rollback migrations."""
    print(f"Downgrading database by: {target}")
    return run_alembic_command(["downgrade", target])


def show_current() -> int:
    """Show current migration version."""
    return run_alembic_command(["current"])


def show_history() -> int:
    """Show migration history."""
    return run_alembic_command(["history"])


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Error: Migration message is required")
            print("Usage: python scripts/migrate.py create \"your message here\"")
            return 1
        message = sys.argv[2]
        return create_migration(message)
    
    elif command == "upgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        return upgrade_migration(target)
    
    elif command == "downgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return downgrade_migration(target)
    
    elif command == "current":
        return show_current()
    
    elif command == "history":
        return show_history()
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())


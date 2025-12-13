#!/usr/bin/env python3
"""
Setup script to configure Homebrew and install PostgreSQL.
This script bypasses shell environment issues.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    print(f"🔧 Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=True,
            text=True,
            executable='/bin/bash'
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(f"⚠️  {result.stderr}", file=sys.stderr)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False

def main():
    print("🔧 Setting up Homebrew and PostgreSQL...")
    print()
    
    # Step 1: Check if Homebrew exists in multiple locations
    brew_paths = [
        Path("/opt/homebrew/bin/brew"),  # Apple Silicon
        Path("/usr/local/bin/brew"),     # Intel Mac
        Path.home() / ".homebrew/bin/brew",  # Alternative location
    ]
    
    brew_path = None
    for path in brew_paths:
        if path.exists():
            brew_path = path
            print(f"✅ Homebrew found at {brew_path}")
            break
    
    if brew_path is None:
        print("❌ Homebrew not found in any standard location")
        print("   Checked locations:")
        for path in brew_paths:
            print(f"     - {path}")
        print()
        print("   Please complete the Homebrew installation first:")
        print('   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
        return 1
    print()
    
    # Step 2: Add Homebrew to PATH in .zshrc
    print("📝 Step 1: Adding Homebrew to ~/.zshrc...")
    zshrc_path = Path.home() / ".zshrc"
    # Use the actual brew path we found
    brew_dir = brew_path.parent.parent  # e.g., /opt/homebrew or /usr/local
    brew_env_line = f'eval "$({brew_dir}/bin/brew shellenv)"'
    
    # Check if already added
    if zshrc_path.exists():
        with open(zshrc_path, 'r') as f:
            if brew_env_line in f.read():
                print("✅ Homebrew already in ~/.zshrc")
            else:
                with open(zshrc_path, 'a') as f:
                    f.write(f"\n{brew_env_line}\n")
                print("✅ Added Homebrew to ~/.zshrc")
    else:
        with open(zshrc_path, 'w') as f:
            f.write(f"{brew_env_line}\n")
        print("✅ Created ~/.zshrc with Homebrew")
    
    print()
    
    # Step 3: Verify Homebrew
    print("📝 Step 2: Verifying Homebrew...")
    if run_command(f"{brew_path} --version"):
        print("✅ Homebrew is working")
    else:
        print("❌ Homebrew verification failed")
        return 1
    
    print()
    
    # Step 4: Install PostgreSQL
    print("📝 Step 3: Installing PostgreSQL (this may take a few minutes)...")
    if run_command(f"{brew_path} install postgresql", check=False):
        print("✅ PostgreSQL installed")
    else:
        print("⚠️  PostgreSQL installation had issues, but continuing...")
    
    print()
    
    # Step 5: Verify PostgreSQL
    print("📝 Step 4: Verifying PostgreSQL...")
    # Check psql in the same directory as brew
    brew_dir = brew_path.parent  # e.g., /opt/homebrew/bin or /usr/local/bin
    psql_path = brew_dir / "psql"
    if psql_path.exists():
        if run_command(f"{psql_path} --version"):
            print("✅ PostgreSQL is ready")
        else:
            print("⚠️  PostgreSQL found but version check failed")
    else:
        print(f"⚠️  psql not found at {psql_path}")
        print("   You may need to restart your terminal or run:")
        brew_dir = brew_path.parent.parent
        print(f"   eval \"$({brew_dir}/bin/brew shellenv)\"")
    
    print()
    print("🎉 Setup complete!")
    print()
    print("To use psql, you may need to restart your terminal or run:")
    brew_dir = brew_path.parent.parent
    print(f'  eval "$({brew_dir}/bin/brew shellenv)"')
    print()
    print("Then connect to your database:")
    print('  psql "postgresql://postgres:<PASSWORD>@health-app-db.c5c224qc6drg.eu-north-1.rds.amazonaws.com:5432/health_app"')
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


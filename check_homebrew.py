#!/usr/bin/env python3
"""Quick script to check Homebrew installation status."""
from pathlib import Path

print("🔍 Checking for Homebrew installation...")
print()

locations = [
    ("/opt/homebrew/bin/brew", "Apple Silicon (M1/M2/M3)"),
    ("/usr/local/bin/brew", "Intel Mac"),
    (str(Path.home() / ".homebrew/bin/brew"), "Alternative location"),
]

found = False
for path_str, description in locations:
    path = Path(path_str)
    if path.exists():
        print(f"✅ Found Homebrew at: {path_str}")
        print(f"   Type: {description}")
        found = True
        # Try to get version
        import subprocess
        try:
            result = subprocess.run([str(path), "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"   Version: {version_line}")
        except:
            pass
        break

if not found:
    print("❌ Homebrew not found in any standard location")
    print()
    print("Possible reasons:")
    print("1. Installation is still in progress")
    print("2. Installation failed")
    print("3. Homebrew was installed in a non-standard location")
    print()
    print("To install Homebrew, run:")
    print('  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
    print()
    print("After installation completes, it will show you commands to run.")
    print("Usually something like:")
    print('  eval "$(/opt/homebrew/bin/brew shellenv)"')


#!/usr/bin/env python3
"""Set demo user password directly."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.domain.models import User
from app.config.security import hash_password

def main():
    db = SessionLocal()
    
    demo_user = db.query(User).filter(User.email == "demo@example.com").first()
    if not demo_user:
        print("❌ Demo user not found")
        return 1
    
    demo_password = "demo123"
    print(f"Setting password for {demo_user.email}...")
    
    try:
        # Hash the password
        hashed = hash_password(demo_password)
        demo_user.hashed_password = hashed
        db.commit()
        db.refresh(demo_user)
        
        print(f"✅ Password set successfully!")
        print(f"   Email: {demo_user.email}")
        print(f"   Password: {demo_password}")
        print(f"   Hash: {demo_user.hashed_password[:20]}...")
        print(f"\nYou can now login with:")
        print(f"   username: {demo_user.email}")
        print(f"   password: {demo_password}")
        
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())


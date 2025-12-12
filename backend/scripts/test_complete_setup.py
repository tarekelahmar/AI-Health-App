#!/usr/bin/env python3
"""
Complete setup test - verifies database, API, and seeded data.
"""
import sys
import requests
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import get_settings
from app.core.database import SessionLocal
from app.domain.models import User, WearableSample, LabResult

# Try to import hash_password, but handle if jose is not installed
try:
    from app.config.security import hash_password
    HAS_SECURITY = True
except ImportError:
    HAS_SECURITY = False
    print("⚠️  Warning: python-jose not installed. Install with: pip install python-jose[cryptography]")

BASE_URL = "http://localhost:8000"

def test_database_connection():
    """Test database connection and verify seeded data."""
    print("🔍 Testing database connection...")
    try:
        db = SessionLocal()
        
        # Check users
        user_count = db.query(User).count()
        print(f"   ✅ Database connected")
        print(f"   Users in database: {user_count}")
        
        # Check demo user
        demo_user = db.query(User).filter(User.email == "demo@example.com").first()
        if demo_user:
            print(f"   ✅ Demo user found (ID: {demo_user.id})")
            
            # Check wearable data
            wearable_count = db.query(WearableSample).filter(
                WearableSample.user_id == demo_user.id
            ).count()
            print(f"   Wearable samples: {wearable_count}")
            
            # Check lab results
            lab_count = db.query(LabResult).filter(
                LabResult.user_id == demo_user.id
            ).count()
            print(f"   Lab results: {lab_count}")
        else:
            print("   ⚠️  Demo user not found")
        
        db.close()
        return True
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False

def test_server_running():
    """Test if FastAPI server is running."""
    print("\n🔍 Testing FastAPI server...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Server is running")
            print(f"   Status: {data.get('status', 'N/A')}")
            return True
        else:
            print(f"   ⚠️  Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Server is not running")
        print("   Start it with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_api_endpoints():
    """Test available API endpoints."""
    print("\n🔍 Testing API endpoints...")
    try:
        # Test root
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"   GET / - Status: {response.status_code}")
        
        # Test OpenAPI schema
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            schema = response.json()
            paths = list(schema.get('paths', {}).keys())
            print(f"   ✅ OpenAPI schema available ({len(paths)} endpoints)")
            
            # Show key endpoints
            key_endpoints = [
                "/api/v1/users/",
                "/api/v1/insights/",
                "/api/v1/insights/sleep",
                "/api/v1/auth/login",
            ]
            print("   Key endpoints:")
            for endpoint in key_endpoints:
                if endpoint in paths:
                    print(f"     ✅ {endpoint}")
                else:
                    print(f"     ⚠️  {endpoint} (not found)")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_swagger_ui():
    """Test Swagger UI availability."""
    print("\n🔍 Testing Swagger UI...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Swagger UI available")
            print(f"   URL: {BASE_URL}/docs")
            return True
        else:
            print(f"   ⚠️  Swagger UI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def setup_demo_user_password():
    """Ensure demo user has a proper password hash."""
    print("\n🔍 Setting up demo user password...")
    if not HAS_SECURITY:
        print("   ⚠️  Skipping password setup (python-jose not installed)")
        print("   Install with: pip install python-jose[cryptography]")
        return False
    
    try:
        db = SessionLocal()
        demo_user = db.query(User).filter(User.email == "demo@example.com").first()
        
        if demo_user:
            # Check if password needs to be hashed (not a proper bcrypt hash)
            needs_hash = (
                not demo_user.hashed_password or 
                demo_user.hashed_password == "demo_hash" or 
                not demo_user.hashed_password.startswith("$2b$")  # bcrypt hash prefix
            )
            
            if needs_hash:
                # Hash the password - use a short, simple password
                demo_password = "demo123"  # Simple demo password
                try:
                    # Ensure password is bytes-compatible and not too long
                    if len(demo_password.encode('utf-8')) > 72:
                        demo_password = demo_password[:72]
                    
                    demo_user.hashed_password = hash_password(demo_password)
                    db.commit()
                    db.refresh(demo_user)
                    print(f"   ✅ Demo user password set to: demo123")
                    print(f"   (Use this to login via /api/v1/auth/login)")
                except Exception as e:
                    print(f"   ⚠️  Could not hash password: {e}")
                    print(f"   You may need to manually set the password")
                    db.rollback()
                    return False
            else:
                print(f"   ✅ Demo user already has hashed password")
                print(f"   (Password appears to be properly hashed)")
        else:
            print("   ⚠️  Demo user not found")
        
        db.close()
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 Complete Setup Test")
    print("=" * 60)
    
    results = []
    
    # Test database
    results.append(("Database Connection", test_database_connection()))
    
    # Test server
    server_running = test_server_running()
    results.append(("Server Running", server_running))
    
    if server_running:
        # Test API
        results.append(("API Endpoints", test_api_endpoints()))
        results.append(("Swagger UI", test_swagger_ui()))
    
    # Setup demo user password
    results.append(("Demo User Password", setup_demo_user_password()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Open Swagger UI: http://localhost:8000/docs")
        print("2. Test login: POST /api/v1/auth/login")
        print("   - username: demo@example.com")
        print("   - password: demo123")
        print("3. Generate insights: POST /api/v1/insights/sleep")
        print("   (Use the access token from login)")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Test API endpoints to verify the server is working correctly.
"""
import sys
import requests
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

BASE_URL = "http://localhost:8000"

def test_server_health():
    """Test if server is running."""
    print("🔍 Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            print(f"   Swagger UI: {BASE_URL}/docs")
            return True
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible")
        print("   Make sure uvicorn is running: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_root_endpoint():
    """Test root endpoint."""
    print("\n🔍 Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
            return True
    except Exception as e:
        print(f"   ⚠️  {e}")
    return False

def test_openapi_schema():
    """Test OpenAPI schema endpoint."""
    print("\n🔍 Testing OpenAPI schema...")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            schema = response.json()
            print(f"✅ OpenAPI schema available")
            print(f"   Title: {schema.get('info', {}).get('title', 'N/A')}")
            print(f"   Version: {schema.get('info', {}).get('version', 'N/A')}")
            paths = list(schema.get('paths', {}).keys())
            print(f"   Available endpoints: {len(paths)}")
            if paths:
                print(f"   Sample endpoints:")
                for path in paths[:5]:
                    print(f"     - {path}")
            return True
    except Exception as e:
        print(f"   ⚠️  {e}")
    return False

def test_users_endpoint():
    """Test users endpoint (may require auth)."""
    print("\n🔍 Testing users endpoint...")
    try:
        # Try to get users list (may require auth)
        response = requests.get(f"{BASE_URL}/api/v1/users/", timeout=5)
        print(f"   GET /api/v1/users/ - Status: {response.status_code}")
        if response.status_code == 200:
            users = response.json()
            print(f"   ✅ Found {len(users)} users")
            return True
        elif response.status_code == 401:
            print("   ⚠️  Authentication required (expected)")
            return True
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ⚠️  {e}")
    return False

def test_insights_endpoint():
    """Test insights endpoint."""
    print("\n🔍 Testing insights endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/insights/", timeout=5)
        print(f"   GET /api/v1/insights/ - Status: {response.status_code}")
        if response.status_code in [200, 401]:
            print("   ✅ Endpoint exists")
            return True
    except Exception as e:
        print(f"   ⚠️  {e}")
    return False

def main():
    print("🧪 Testing API Endpoints")
    print("=" * 50)
    
    # Test server health
    if not test_server_health():
        print("\n❌ Server is not running. Please start it with:")
        print("   cd backend && uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Test other endpoints
    test_root_endpoint()
    test_openapi_schema()
    test_users_endpoint()
    test_insights_endpoint()
    
    print("\n" + "=" * 50)
    print("✅ API testing complete!")
    print("\nNext steps:")
    print("1. Open Swagger UI: http://localhost:8000/docs")
    print("2. Test endpoints interactively")
    print("3. Try generating insights with seeded data")

if __name__ == "__main__":
    main()


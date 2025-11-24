"""
Test script for GitHub Service
Run this to verify the service is working correctly
"""
import asyncio
import httpx


async def test_github_service():
    """Test GitHub Service endpoints"""
    base_url = "http://localhost:8102"  # Direct to service
    
    print("🧪 Testing GitHub Service...")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Health Check
        print("\n1️⃣ Testing Health Check...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed!")
                print(f"   Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Test 2: Metrics endpoint
        print("\n2️⃣ Testing Metrics Endpoint...")
        try:
            response = await client.get(f"{base_url}/metrics")
            if response.status_code == 200:
                print("✅ Metrics endpoint working!")
                lines = response.text.split('\n')[:5]
                print(f"   First few lines: {lines}")
            else:
                print(f"❌ Metrics failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Metrics error: {e}")
        
        # Test 3: API endpoint (without auth for now)
        print("\n3️⃣ Testing API Endpoint Structure...")
        try:
            # This will fail without auth, but confirms routing works
            response = await client.get(f"{base_url}/api/github/installations")
            print(f"   Status: {response.status_code}")
            if response.status_code == 401 or response.status_code == 403:
                print("✅ API routing works (auth required as expected)")
            elif response.status_code == 200:
                print("✅ API endpoint accessible!")
            else:
                print(f"⚠️ Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"❌ API error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Service tests complete!")


async def test_via_kong():
    """Test GitHub Service via Kong Gateway"""
    kong_url = "http://localhost:8000"  # Kong gateway
    
    print("\n\n🧪 Testing via Kong Gateway...")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n🌐 Testing Kong routing to GitHub Service...")
        try:
            response = await client.get(f"{kong_url}/api/github/installations")
            print(f"   Status: {response.status_code}")
            if response.status_code in [401, 403, 200]:
                print("✅ Kong routing to GitHub Service works!")
            else:
                print(f"⚠️ Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"❌ Kong routing error: {e}")
    
    print("\n" + "=" * 60)


async def test_backend_client():
    """Test Backend calling GitHub Service"""
    backend_url = "http://localhost:8100"  # Backend service
    
    print("\n\n🧪 Testing Backend → GitHub Service communication...")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n🔗 Testing Backend proxy to GitHub Service...")
        try:
            response = await client.get(f"{backend_url}/api/github/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Backend → GitHub Service communication works!")
                print(f"   Response: {response.json()}")
            else:
                print(f"⚠️ Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Backend communication error: {e}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("🚀 GitHub Service Test Suite")
    print("=" * 60)
    print("Make sure services are running:")
    print("  docker-compose up github-service")
    print("=" * 60)
    
    asyncio.run(test_github_service())
    
    # Uncomment when Kong and Backend are running
    # asyncio.run(test_via_kong())
    # asyncio.run(test_backend_client())
    
    print("\n✅ All tests completed!")

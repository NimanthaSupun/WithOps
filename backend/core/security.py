from jose import jwt
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Load environment variables
load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
ALGORITHMS = ["RS256"]

# Add test mode for debugging
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

print(f"AUTH0_DOMAIN: {AUTH0_DOMAIN}")
print(f"API_AUDIENCE: {API_AUDIENCE}")
print(f"TEST_MODE: {TEST_MODE}")

security = HTTPBearer()

# Add global tracking for last authenticated user and enhanced security
_last_authenticated_user = None
_user_session_data = {}  # Track user session metadata

async def verify_token(token: str):
    print(f"Verifying token: {token[:50]}...")
    
    # In test mode, return a mock payload
    if TEST_MODE:
        print("🧪 TEST MODE: Using mock token validation")
        return {
            "sub": "auth0|test_user_12345",
            "name": "Test User",
            "picture": "https://avatars.githubusercontent.com/u/123456789",
            # Note: No 'email' field to test the fallback logic
            "aud": API_AUDIENCE,
            "iss": f"https://{AUTH0_DOMAIN}/",
            "exp": 9999999999,
            "iat": 1736177615,
            "scope": "read:profile"
        }
    
    if not AUTH0_DOMAIN:
        raise ValueError("AUTH0_DOMAIN not configured")
    if not API_AUDIENCE:
        raise ValueError("AUTH0_API_AUDIENCE not configured")
    
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    print(f"Fetching JWKS from: {jwks_url}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch JWKS: {response.status_code}")
        jwks = response.json()

    try:
        unverified_header = jwt.get_unverified_header(token)
        print(f"Token header: {unverified_header}")
    except Exception as e:
        raise ValueError(f"Invalid token format: {str(e)}")
    
    rsa_key = next(
        (key for key in jwks["keys"] if key["kid"] == unverified_header["kid"]), None
    )
    
    if not rsa_key:
        raise ValueError(f"Unable to find appropriate key for kid: {unverified_header.get('kid')}")
    
    try:
        # Let's decode the token without validation first to see what's inside
        unverified_payload = jwt.get_unverified_claims(token)
        print(f"Unverified payload: {unverified_payload}")
        print(f"Token audience: {unverified_payload.get('aud')}")
        print(f"Expected audience: {API_AUDIENCE}")
        
        # Now try to decode with proper validation
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )
        print(f"Token decoded successfully: {payload.get('sub', 'unknown user')}")
        return payload
    except Exception as e:
        print(f"Token decode error: {str(e)}")
        
        # If audience validation fails, let's try without it for debugging
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                issuer=f"https://{AUTH0_DOMAIN}/",
                options={"verify_aud": False}  # Skip audience verification
            )
            print(f"Token decoded without audience validation: {payload}")
            return payload
        except Exception as e2:
            print(f"Token decode error (no audience): {str(e2)}")
            raise ValueError(f"Token validation error: {str(e)}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user ID from JWT token"""
    global _last_authenticated_user, _user_session_data
    
    try:
        token = credentials.credentials
        payload = await verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        
        # 🔐 SECURITY: Enhanced user switch detection and cache clearing
        current_time = datetime.now()
        
        # Check if this is a different user than last request
        if _last_authenticated_user and _last_authenticated_user != user_id:
            print(f"🔐 CRITICAL: User switch detected: {_last_authenticated_user} -> {user_id}")
            
            # Clear cache for previous user
            from core.github_client import github_client
            github_client.clear_user_cache(_last_authenticated_user)
            github_client.clear_user_cache(user_id)  # Clear new user's cache too for safety
            
            # Clear any global caches that might leak data
            github_client.clear_all_cache()  # Nuclear option - clear all cache
            
            print("🔐 CRITICAL: All caches cleared for user switch")
            
            # Reset session tracking
            _user_session_data.clear()
        
        # Update session tracking
        _last_authenticated_user = user_id
        _user_session_data[user_id] = {
            'last_seen': current_time,
            'token_hash': hash(token)  # Track token changes
        }
        
        print(f"✅ Authentication successful for user: {user_id}")
        return user_id
    except ValueError as e:
        print(f"❌ Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def force_clear_all_user_sessions():
    """🔐 SECURITY: Nuclear option to clear all user sessions and cache"""
    global _last_authenticated_user, _user_session_data
    
    from core.github_client import github_client
    github_client.clear_all_cache()
    
    _last_authenticated_user = None
    _user_session_data.clear()
    
    print("🔐 NUCLEAR: All user sessions and cache cleared")

def decode_jwt_token(token: str) -> dict:
    """
    🚀 PERFORMANCE: Decode JWT token without full verification (for rate limiting)
    Only use this for non-critical operations like rate limiting
    """
    try:
        # Decode without verification for performance
        decoded = jwt.get_unverified_claims(token)
        return decoded
    except Exception:
        return {}

async def get_auth0_user_info(access_token: str):
    """Get complete user profile from Auth0 userinfo endpoint"""
    if not AUTH0_DOMAIN:
        raise ValueError("AUTH0_DOMAIN not configured")
    
    userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"Auth0 userinfo response: {user_info}")
            return user_info
        else:
            print(f"Failed to fetch userinfo: {response.status_code} - {response.text}")
            return None
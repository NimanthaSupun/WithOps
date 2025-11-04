# core/rate_limiter.py

import asyncio
import time
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    🚀 PERFORMANCE: Advanced rate limiter with user-based and IP-based limits
    Implements sliding window algorithm for more accurate rate limiting
    """
    
    def __init__(self):
        # User-based rate limits (per Auth0 user ID) - Development-friendly
        self.user_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_limits = {
            'per_minute': 200,  # 200 requests per minute per user (increased for dev)
            'per_hour': 4000,   # 4000 requests per hour per user (increased for dev)
            'burst': 50         # 50 requests in 10 seconds (increased for dev)
        }
        
        # IP-based rate limits (for unauthenticated requests) - Development-friendly
        self.ip_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.ip_limits = {
            'per_minute': 100,  # 100 requests per minute per IP (increased for dev)
            'per_hour': 2000,   # 2000 requests per hour per IP (increased for dev)
            'burst': 30         # 30 requests in 10 seconds (increased for dev)
        }
        
        # Special endpoint limits - More lenient for development
        self.endpoint_limits = {
            '/api/github/workspace/': {'per_minute': 60, 'burst': 15},  # Workspace data is expensive
            '/api/github/organizations/': {'per_minute': 40, 'burst': 10},  # GitHub API calls
            '/api/auth/': {'per_minute': 100, 'burst': 25}  # Auth endpoints
        }
        
        # Cleanup task to prevent memory leaks
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    async def check_rate_limit(self, request: Request, user_id: Optional[str] = None) -> bool:
        """
        🚀 Check if request should be rate limited
        Returns True if request is allowed, False if rate limited
        """
        # 🚧 DEVELOPMENT MODE: Temporarily disable rate limiting for debugging
        # TODO: Re-enable for production
        if True:  # Set to False to enable rate limiting
            return True
            
        current_time = time.time()
        client_ip = self._get_client_ip(request)
        endpoint = self._get_endpoint_pattern(request.url.path)
        
        # Periodic cleanup to prevent memory leaks
        if current_time - self._last_cleanup > self._cleanup_interval:
            await self._cleanup_old_requests()
            self._last_cleanup = current_time
        
        # Check user-based limits if authenticated
        if user_id:
            if not self._check_user_limits(user_id, current_time, endpoint):
                logger.warning(f"Rate limit exceeded for user {user_id} on {endpoint}")
                return False
        
        # Always check IP-based limits
        if not self._check_ip_limits(client_ip, current_time, endpoint):
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {endpoint}")
            return False
        
        # Record the request
        if user_id:
            self.user_requests[user_id].append(current_time)
        self.ip_requests[client_ip].append(current_time)
        
        return True
    
    def _check_user_limits(self, user_id: str, current_time: float, endpoint: str) -> bool:
        """Check user-specific rate limits"""
        requests = self.user_requests[user_id]
        
        # Get limits for this endpoint or use defaults
        limits = self.endpoint_limits.get(endpoint, self.user_limits)
        
        return self._check_limits(requests, current_time, limits)
    
    def _check_ip_limits(self, ip: str, current_time: float, endpoint: str) -> bool:
        """Check IP-specific rate limits"""
        requests = self.ip_requests[ip]
        
        # Get limits for this endpoint or use defaults
        limits = self.endpoint_limits.get(endpoint, self.ip_limits)
        
        return self._check_limits(requests, current_time, limits)
    
    def _check_limits(self, requests: deque, current_time: float, limits: dict) -> bool:
        """Check if current request exceeds any rate limits"""
        
        # Clean old requests (sliding window)
        self._clean_old_requests(requests, current_time, 3600)  # 1 hour window
        
        # Check burst limit (last 10 seconds)
        burst_count = sum(1 for req_time in requests if current_time - req_time <= 10)
        if burst_count >= limits.get('burst', float('inf')):
            return False
        
        # Check per-minute limit
        minute_count = sum(1 for req_time in requests if current_time - req_time <= 60)
        if minute_count >= limits.get('per_minute', float('inf')):
            return False
        
        # Check per-hour limit
        hour_count = len(requests)  # All requests in the deque are within 1 hour
        if hour_count >= limits.get('per_hour', float('inf')):
            return False
        
        return True
    
    def _clean_old_requests(self, requests: deque, current_time: float, window: int):
        """Remove requests older than the window"""
        while requests and current_time - requests[0] > window:
            requests.popleft()
    
    async def _cleanup_old_requests(self):
        """Periodic cleanup to prevent memory leaks"""
        current_time = time.time()
        
        # Clean user requests
        for user_id in list(self.user_requests.keys()):
            self._clean_old_requests(self.user_requests[user_id], current_time, 3600)
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
        
        # Clean IP requests
        for ip in list(self.ip_requests.keys()):
            self._clean_old_requests(self.ip_requests[ip], current_time, 3600)
            if not self.ip_requests[ip]:
                del self.ip_requests[ip]
        
        logger.debug(f"Rate limiter cleanup completed. Active users: {len(self.user_requests)}, Active IPs: {len(self.ip_requests)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else 'unknown'
    
    def _get_endpoint_pattern(self, path: str) -> str:
        """Get endpoint pattern for rate limiting"""
        for pattern in self.endpoint_limits.keys():
            if path.startswith(pattern):
                return pattern
        return 'default'
    
    def get_rate_limit_info(self, user_id: Optional[str] = None, ip: Optional[str] = None) -> dict:
        """Get current rate limit status for debugging"""
        current_time = time.time()
        
        info = {}
        
        if user_id and user_id in self.user_requests:
            requests = self.user_requests[user_id]
            self._clean_old_requests(requests, current_time, 3600)
            
            info['user'] = {
                'requests_last_hour': len(requests),
                'requests_last_minute': sum(1 for req_time in requests if current_time - req_time <= 60),
                'requests_last_10_seconds': sum(1 for req_time in requests if current_time - req_time <= 10)
            }
        
        if ip and ip in self.ip_requests:
            requests = self.ip_requests[ip]
            self._clean_old_requests(requests, current_time, 3600)
            
            info['ip'] = {
                'requests_last_hour': len(requests),
                'requests_last_minute': sum(1 for req_time in requests if current_time - req_time <= 60),
                'requests_last_10_seconds': sum(1 for req_time in requests if current_time - req_time <= 10)
            }
        
        return info

# Global rate limiter instance
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """
    🚀 PERFORMANCE: Rate limiting middleware for FastAPI
    """
    try:
        # Extract user ID if available (from Authorization header)
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                # You would need to decode the JWT to get the user ID
                # For now, we'll use a simplified approach
                from core.security import decode_jwt_token
                token = auth_header.split(' ')[1]
                user_info = decode_jwt_token(token)
                user_id = user_info.get('sub')
            except:
                pass  # Continue without user ID
        
        # Check rate limit
        if not await rate_limiter.check_rate_limit(request, user_id):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Continue with the request
        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Don't block requests if rate limiter fails
        return await call_next(request)

"""
Request logging middleware with correlation IDs for distributed tracing
"""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation ID to all requests
    Helps trace requests across microservices
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Add to request state
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(f"[{request_id}] {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"- {response.status_code} ({duration:.3f}s)"
        )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request_id
        
        return response


async def request_id_middleware(request: Request, call_next):
    """
    Simpler middleware function version
    """
    request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    
    return response

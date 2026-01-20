"""
Rate Limiting Middleware
Simple in-memory rate limiting for API endpoints.
For production, consider using Redis-backed solutions like slowapi.
"""
import time
from collections import defaultdict
from typing import Callable, Dict, Tuple
from functools import wraps

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    Limits requests per IP address across all endpoints.
    For more granular control, use the rate_limit decorator.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
        self.window_seconds = 60
    
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Clean old requests
        current_time = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window_seconds
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": self.window_seconds,
                }
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        # Continue with request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_ip])
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.window_seconds)
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies"""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"


class EndpointRateLimiter:
    """
    Per-endpoint rate limiter with configurable limits.
    Use as a dependency in FastAPI routes.
    
    Usage:
        auth_limiter = EndpointRateLimiter(max_requests=5, window_seconds=60)
        
        @router.post("/login")
        async def login(rate_limit: None = Depends(auth_limiter)):
            ...
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def __call__(self, request: Request):
        if not settings.RATE_LIMIT_ENABLED:
            return None
        
        client_ip = self._get_client_ip(request)
        endpoint = f"{request.method}:{request.url.path}"
        key = f"{client_ip}:{endpoint}"
        
        current_time = time.time()
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < self.window_seconds
        ]
        
        # Check limit
        if len(self.requests[key]) >= self.max_requests:
            retry_after = int(
                self.window_seconds - (current_time - self.requests[key][0])
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Record request
        self.requests[key].append(current_time)
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"


# =============================================================================
# PRE-CONFIGURED RATE LIMITERS
# =============================================================================

# Strict limiter for authentication endpoints (5 requests per minute)
auth_rate_limiter = EndpointRateLimiter(max_requests=5, window_seconds=60)

# Moderate limiter for password reset (3 requests per hour)
password_reset_limiter = EndpointRateLimiter(max_requests=3, window_seconds=3600)

# Standard limiter for API endpoints (30 requests per minute)
standard_rate_limiter = EndpointRateLimiter(max_requests=30, window_seconds=60)

# Relaxed limiter for read-only endpoints (100 requests per minute)
read_rate_limiter = EndpointRateLimiter(max_requests=100, window_seconds=60)

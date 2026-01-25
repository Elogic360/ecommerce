"""
IP Blocking and Security Monitoring
Tracks suspicious activity and blocks malicious IPs
"""
import time
from collections import defaultdict, deque
from typing import Dict, Set, Optional, Tuple
from datetime import datetime, timedelta
import logging

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class IPBlocker:
    """
    Tracks and blocks suspicious IP addresses based on failed authentication attempts.
    Implements temporary bans with automatic expiry.
    """
    
    def __init__(
        self,
        threshold: int = 10,  # Failed attempts before blocking
        window_seconds: int = 300,  # 5 minutes window
        ban_duration_minutes: int = 15,  # Ban for 15 minutes
    ):
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.ban_duration_seconds = ban_duration_minutes * 60
        
        # Track failed auth attempts: IP -> deque of timestamps
        self.failed_attempts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=threshold))
        
        # Currently banned IPs: IP -> ban_expiry_timestamp
        self.banned_ips: Dict[str, float] = {}
        
        # Whitelist of IPs that should never be blocked
        self.whitelist: Set[str] = self._load_whitelist()
        
        # Track last cleanup time
        self._last_cleanup = time.time()
    
    def _load_whitelist(self) -> Set[str]:
        """Load whitelisted IPs from environment"""
        whitelist_str = getattr(settings, 'IP_WHITELIST', '')
        if whitelist_str:
            return set(ip.strip() for ip in whitelist_str.split(',') if ip.strip())
        return set()
    
    def is_blocked(self, ip: str) -> Tuple[bool, Optional[int]]:
        """
        Check if an IP is currently blocked.
        
        Returns:
            Tuple of (is_blocked, seconds_until_unblock)
        """
        if ip in self.whitelist:
            return False, None
        
        if ip in self.banned_ips:
            expiry = self.banned_ips[ip]
            now = time.time()
            
            if now < expiry:
                # Still banned
                remaining = int(expiry - now)
                return True, remaining
            else:
                # Ban expired, remove from list
                del self.banned_ips[ip]
                return False, None
        
        return False, None
    
    def record_failed_attempt(self, ip: str, endpoint: str) -> bool:
        """
        Record a failed authentication attempt.
        
        Returns:
            True if IP should be blocked, False otherwise
        """
        if ip in self.whitelist:
            return False
        
        now = time.time()
        
        # Clean old attempts outside the window
        attempts = self.failed_attempts[ip]
        while attempts and (now - attempts[0]) > self.window_seconds:
            attempts.popleft()
        
        # Add new attempt
        attempts.append(now)
        
        # Log the attempt
        logger.warning(
            f"Failed auth attempt from IP {ip} to {endpoint}. "
            f"Count: {len(attempts)}/{self.threshold} in last {self.window_seconds}s"
        )
        
        # Check if threshold exceeded
        if len(attempts) >= self.threshold:
            self._block_ip(ip)
            return True
        
        return False
    
    def _block_ip(self, ip: str):
        """Block an IP address"""
        expiry = time.time() + self.ban_duration_seconds
        self.banned_ips[ip] = expiry
        
        logger.error(
            f"🚫 BLOCKED IP: {ip} for {self.ban_duration_seconds/60} minutes "
            f"due to {self.threshold} failed auth attempts"
        )
        
        # Clear failed attempts since we're now blocking
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]
    
    def unblock_ip(self, ip: str):
        """Manually unblock an IP (admin override)"""
        if ip in self.banned_ips:
            del self.banned_ips[ip]
            logger.info(f"Manually unblocked IP: {ip}")
    
    def cleanup_expired(self):
        """Remove expired bans and old failed attempts"""
        now = time.time()
        
        # Only cleanup every 60 seconds to reduce overhead
        if now - self._last_cleanup < 60:
            return
        
        self._last_cleanup = now
        
        # Remove expired bans
        expired = [ip for ip, expiry in self.banned_ips.items() if now >= expiry]
        for ip in expired:
            del self.banned_ips[ip]
            logger.info(f"IP ban expired: {ip}")
        
        # Remove old failed attempt records (older than 1 hour)
        stale_ips = []
        for ip, attempts in self.failed_attempts.items():
            if attempts and (now - attempts[-1]) > 3600:
                stale_ips.append(ip)
        
        for ip in stale_ips:
            del self.failed_attempts[ip]
    
    def get_stats(self) -> dict:
        """Get current blocking statistics"""
        return {
            "total_banned": len(self.banned_ips),
            "currently_banned_ips": list(self.banned_ips.keys()),
            "whitelist_size": len(self.whitelist),
            "tracked_ips_with_failures": len(self.failed_attempts),
        }


# Global IP blocker instance
ip_blocker = IPBlocker(
    threshold=getattr(settings, 'IP_BLOCK_THRESHOLD', 10),
    window_seconds=getattr(settings, 'IP_BLOCK_WINDOW_SECONDS', 300),
    ban_duration_minutes=getattr(settings, 'IP_BLOCK_DURATION_MINUTES', 15),
)


class IPBlockingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to block requests from banned IPs.
    Should be added early in the middleware stack.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check if IP blocking is enabled
        if not getattr(settings, 'IP_BLOCKING_ENABLED', True):
            return await call_next(request)
        
        # Periodic cleanup
        ip_blocker.cleanup_expired()
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check if blocked
        is_blocked, remaining = ip_blocker.is_blocked(client_ip)
        
        if is_blocked:
            logger.warning(f"Blocked request from banned IP: {client_ip} to {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Your IP has been temporarily blocked due to suspicious activity.",
                    "retry_after": remaining,
                },
                headers={"Retry-After": str(remaining)}
            )
        
        # Continue with request
        response = await call_next(request)
        
        # Track 401 responses for admin routes
        if response.status_code == 401 and "/admin/" in str(request.url.path):
            should_block = ip_blocker.record_failed_attempt(client_ip, str(request.url.path))
            if should_block:
                # Add blocking notice to response headers
                response.headers["X-Security-Notice"] = "IP blocked due to repeated auth failures"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

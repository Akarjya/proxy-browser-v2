"""
Rate Limiting Middleware
Implements rate limiting to prevent abuse
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, Deque
import asyncio
from loguru import logger


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.request_history: Dict[str, Deque[datetime]] = defaultdict(deque)
        self.blocked_until: Dict[str, datetime] = {}
        self._cleanup_task = None
        self._lock = asyncio.Lock()
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Get client identifier (IP or session)
        client_id = self._get_client_id(request)
        
        # Check if client is temporarily blocked
        async with self._lock:
            if client_id in self.blocked_until:
                if datetime.now() < self.blocked_until[client_id]:
                    remaining = (self.blocked_until[client_id] - datetime.now()).seconds
                    logger.warning(f"Rate limited: {client_id} for {remaining}s")
                    
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too many requests",
                            "retry_after": remaining
                        },
                        headers={
                            "Retry-After": str(remaining),
                            "X-RateLimit-Limit": str(self.requests_per_minute),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(self.blocked_until[client_id].timestamp()))
                        }
                    )
                else:
                    # Unblock
                    del self.blocked_until[client_id]
        
        # Check rate limit
        is_allowed, remaining = await self._check_rate_limit(client_id)
        
        if not is_allowed:
            # Block client temporarily
            async with self._lock:
                self.blocked_until[client_id] = datetime.now() + timedelta(seconds=60)
            
            logger.warning(f"Rate limit exceeded for {client_id}")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
        
        return response
    
    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """Check if request is within rate limit"""
        
        async with self._lock:
            now = datetime.now()
            history = self.request_history[client_id]
            
            # Remove old requests (older than 1 minute)
            cutoff = now - timedelta(minutes=1)
            while history and history[0] < cutoff:
                history.popleft()
            
            # Check burst limit (last 5 seconds)
            burst_cutoff = now - timedelta(seconds=5)
            burst_count = sum(1 for ts in history if ts > burst_cutoff)
            
            if burst_count >= self.burst_size:
                return False, 0
            
            # Check rate limit
            if len(history) >= self.requests_per_minute:
                return False, 0
            
            # Add current request
            history.append(now)
            
            remaining = self.requests_per_minute - len(history)
            return True, remaining
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        
        # Try to get session ID first
        session_id = request.headers.get('X-Session-ID')
        if session_id:
            return f"session:{session_id}"
        
        # Try to get from cookie
        session_cookie = request.cookies.get('session_id')
        if session_cookie:
            return f"session:{session_cookie}"
        
        # Fall back to IP
        return f"ip:{request.client.host}"
    
    async def _cleanup_loop(self):
        """Periodically clean up old data"""
        
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                await self._cleanup_old_data()
            except Exception as e:
                logger.error(f"Cleanup error: {str(e)}")
    
    async def _cleanup_old_data(self):
        """Clean up old request history"""
        
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=5)
            
            # Clean request history
            clients_to_remove = []
            for client_id, history in self.request_history.items():
                # Remove old entries
                while history and history[0] < cutoff:
                    history.popleft()
                
                # Remove empty histories
                if not history:
                    clients_to_remove.append(client_id)
            
            for client_id in clients_to_remove:
                del self.request_history[client_id]
            
            # Clean blocked list
            blocked_to_remove = []
            for client_id, blocked_until in self.blocked_until.items():
                if blocked_until < now:
                    blocked_to_remove.append(client_id)
            
            for client_id in blocked_to_remove:
                del self.blocked_until[client_id]
            
            if clients_to_remove or blocked_to_remove:
                logger.debug(f"Cleaned up {len(clients_to_remove)} histories, {len(blocked_to_remove)} blocks")
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        
        return {
            "active_clients": len(self.request_history),
            "blocked_clients": len(self.blocked_until),
            "requests_per_minute": self.requests_per_minute,
            "burst_size": self.burst_size
        }
    
    def reset_client(self, client_id: str):
        """Reset rate limit for a client"""
        
        if client_id in self.request_history:
            del self.request_history[client_id]
        
        if client_id in self.blocked_until:
            del self.blocked_until[client_id]
        
        logger.info(f"Reset rate limit for {client_id}")

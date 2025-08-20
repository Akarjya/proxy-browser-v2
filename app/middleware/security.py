"""
Security Middleware
Handles security headers, CORS, and request validation
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger
import hashlib
import time


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for the application"""
    
    def __init__(self, app):
        super().__init__(app)
        self.blocked_ips = set()
        self.request_counts = {}  # IP -> count
        self.request_timestamps = {}  # IP -> [timestamps]
        
    async def dispatch(self, request: Request, call_next):
        """Process requests with security checks"""
        
        # Get client IP
        client_ip = request.client.host
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked request from {client_ip}")
            return Response(content="Access denied", status_code=403)
        
        # Add security headers
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(self), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), "
            "accelerometer=(self), gyroscope=(self)"
        )
        
        # Content Security Policy (adjust as needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' wss: https:; "
            "frame-src 'self' https:;"
        )
        
        # Remove server header safely
        try:
            if "server" in response.headers:
                del response.headers["server"]
        except Exception:
            pass
        
        # Add custom headers
        response.headers["X-Proxy-Browser"] = "v2.0"
        
        return response
    
    def block_ip(self, ip: str):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP blocked: {ip}")
    
    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        logger.info(f"IP unblocked: {ip}")
    
    def is_suspicious_request(self, request: Request) -> bool:
        """Check if request is suspicious"""
        
        # Check for common attack patterns
        suspicious_patterns = [
            '../',  # Path traversal
            '<script',  # XSS attempt
            'SELECT * FROM',  # SQL injection
            'DROP TABLE',  # SQL injection
            'eval(',  # Code injection
            'base64_decode',  # Obfuscation
            '.exe',  # Executable files
            '.sh',  # Shell scripts
        ]
        
        # Check URL
        url = str(request.url)
        for pattern in suspicious_patterns:
            if pattern.lower() in url.lower():
                return True
        
        # Check headers
        for header, value in request.headers.items():
            for pattern in suspicious_patterns:
                if pattern.lower() in str(value).lower():
                    return True
        
        return False

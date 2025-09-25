"""Security middleware and utilities for MCP Tool Registry."""

import time
from typing import Dict, List, Optional

from fastapi import Request, Response, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none'; "
            "worker-src 'self'; "
            "child-src 'self'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "manifest-src 'self'"
        )
        
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log all API requests for audit purposes."""
    
    def __init__(self, app, log_file: str = "audit.log"):
        super().__init__(app)
        self.log_file = log_file
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Extract request info
        client_ip = get_remote_address(request)
        user_agent = request.headers.get("user-agent", "Unknown")
        auth_header = request.headers.get("authorization", "None")
        
        # Make the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log the request
        log_entry = {
            "timestamp": time.time(),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.query_params),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "auth_type": "Bearer" if auth_header.startswith("Bearer") else "None",
            "content_length": response.headers.get("content-length", "0")
        }
        
        # Write to log file (in production, use proper logging)
        with open(self.log_file, "a") as f:
            f.write(f"{log_entry}\n")
        
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize input data."""
    
    def __init__(self, app):
        super().__init__(app)
        # Define dangerous patterns
        self.dangerous_patterns = [
            r"<script.*?>.*?</script>",  # Script tags
            r"javascript:",  # JavaScript protocol
            r"on\w+\s*=",  # Event handlers
            r"data:text/html",  # Data URLs
            r"vbscript:",  # VBScript protocol
            r"expression\s*\(",  # CSS expressions
            r"url\s*\(",  # CSS url()
            r"@import",  # CSS imports
            r"eval\s*\(",  # eval() function
            r"exec\s*\(",  # exec() function
            r"system\s*\(",  # system() function
            r"shell_exec\s*\(",  # shell_exec() function
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check request body for dangerous content
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            body_str = body.decode("utf-8", errors="ignore").lower()
            
            for pattern in self.dangerous_patterns:
                import re
                if re.search(pattern, body_str, re.IGNORECASE):
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Potentially malicious content detected"}
                    )
        
        return await call_next(request)


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Secure CORS configuration."""
    
    def __init__(self, app, allowed_origins: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["http://localhost:3000", "http://localhost:8080"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        origin = request.headers.get("origin")
        
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        else:
            response.headers["Access-Control-Allow-Origin"] = "null"
            response.headers["Access-Control-Allow-Credentials"] = "false"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Custom rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, List[float]] = {}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = get_remote_address(request)
        current_time = time.time()
        
        # Clean old requests (older than 1 minute)
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                req_time for req_time in self.request_counts[client_ip]
                if current_time - req_time < 60
            ]
        else:
            self.request_counts[client_ip] = []
        
        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        
        return await call_next(request)


def get_rate_limits() -> Dict[str, str]:
    """Get rate limit configurations for different endpoints."""
    return {
        "public": "100/minute",  # Public endpoints (health, docs)
        "read": "60/minute",     # Read operations (list, get, search)
        "write": "20/minute",    # Write operations (create, update)
        "admin": "10/minute",    # Admin operations (delete, user management)
    }


def setup_security_middleware(app, config: Dict[str, any] = None):
    """Set up all security middleware."""
    config = config or {}
    
    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add audit logging
    app.add_middleware(AuditLogMiddleware, log_file=config.get("audit_log", "audit.log"))
    
    # Add input validation
    app.add_middleware(InputValidationMiddleware)
    
    # Add secure CORS
    app.add_middleware(
        CORSSecurityMiddleware,
        allowed_origins=config.get("allowed_origins", ["http://localhost:3000"])
    )
    
    # Add rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=config.get("requests_per_minute", 60)
    )
    
    # Add slowapi rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return app
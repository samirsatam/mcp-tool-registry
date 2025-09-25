# Security Guide for MCP Tool Registry

## 🔒 Security Overview

The MCP Tool Registry implements a comprehensive security system designed for production use by multiple services. This guide covers all security features, best practices, and deployment recommendations.

## 🛡️ Security Features

### 1. Authentication & Authorization

**Two Authentication Methods:**
- **User Authentication**: JWT-based login for admin users
- **API Key Authentication**: Service-to-service authentication

**Authorization Levels:**
- **Admin Users**: Full access to all operations
- **API Keys**: Granular permissions (create, read, update, delete)

### 2. Rate Limiting

**Endpoint-Specific Limits:**
- **Public endpoints**: 100 requests/minute
- **Read operations**: 60 requests/minute  
- **Write operations**: 20 requests/minute
- **Admin operations**: 10 requests/minute
- **Delete operations**: 10 requests/minute

### 3. Security Headers

**Automatically Applied:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- `Content-Security-Policy`: Comprehensive CSP policy

### 4. Input Validation & Sanitization

**Protection Against:**
- XSS attacks (script injection)
- SQL injection (via SQLAlchemy ORM)
- CSRF attacks (via CORS policy)
- Malicious content in request bodies

### 5. Audit Logging

**Logged Information:**
- Request method, path, and query parameters
- Client IP address and User-Agent
- Response status code and processing time
- Authentication type and content length
- Timestamp for all requests

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Run the security setup script
uv run python scripts/setup_security.py
```

This creates:
- **Admin user**: `admin` / `admin` (change immediately!)
- **Default API key**: `mcp_-tn1XqqtdGub5NAzzn_qSoLrvJv9gmMwB0y-kfLDsak`

### 2. Change Admin Password

```bash
# Login to get token
curl -X POST 'http://localhost:8000/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=admin'

# Use the returned token for admin operations
```

### 3. Create Service API Keys

```bash
# Create new API key (requires admin token)
curl -X POST 'http://localhost:8000/admin/api-keys' \
  -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "my-service",
    "description": "API key for my service",
    "can_create": true,
    "can_read": true,
    "can_update": false,
    "can_delete": false
  }'
```

## 🔐 Authentication Methods

### User Authentication

**Login Endpoint:**
```bash
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### API Key Authentication

**API Key Login:**
```bash
POST /auth/api-key-login
Content-Type: application/json

{
  "api_key": "mcp_-tn1XqqtdGub5NAzzn_qSoLrvJv9gmMwB0y-kfLDsak"
}
```

**Using API Key:**
```bash
# All API requests require Authorization header
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/tools
```

## 🎯 Permission System

### API Key Permissions

**Granular Control:**
- `can_create`: Register new tools
- `can_read`: List, search, and get tool details
- `can_update`: Modify existing tools
- `can_delete`: Remove tools (admin-only by default)

**Example API Key Creation:**
```json
{
  "name": "readonly-service",
  "description": "Read-only access for monitoring",
  "can_create": false,
  "can_read": true,
  "can_update": false,
  "can_delete": false,
  "expires_at": "2025-12-31T23:59:59"
}
```

### Admin Permissions

**Full Access:**
- All tool operations
- User management
- API key management
- System administration

## 🛠️ Admin Operations

### User Management

```bash
# List all users
GET /admin/users

# Create new user
POST /admin/users
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword",
  "is_admin": false
}

# Toggle user status
POST /admin/users/{user_id}/toggle
```

### API Key Management

```bash
# List all API keys
GET /admin/api-keys

# Create new API key
POST /admin/api-keys
{
  "name": "service-name",
  "description": "Description of service",
  "can_create": true,
  "can_read": true,
  "can_update": false,
  "can_delete": false
}

# Toggle API key status
POST /admin/api-keys/{key_id}/toggle

# Delete API key
DELETE /admin/api-keys/{key_id}
```

## 🔧 Configuration

### Environment Variables

```bash
# Required for production
export SECRET_KEY="your-super-secret-key-change-this"
export DATABASE_URL="sqlite:///./mcp_registry.db"

# Optional
export ALLOWED_ORIGINS="https://yourdomain.com,https://api.yourdomain.com"
export REQUESTS_PER_MINUTE="60"
export AUDIT_LOG_FILE="audit.log"
```

### Security Middleware Configuration

```python
# In api.py
app = setup_security_middleware(app, {
    "allowed_origins": ["https://yourdomain.com"],
    "requests_per_minute": 60,
    "audit_log": "audit.log"
})
```

## 🚨 Security Best Practices

### 1. Production Deployment

**Essential Steps:**
- [ ] Change default admin password
- [ ] Set strong `SECRET_KEY` environment variable
- [ ] Use HTTPS in production
- [ ] Configure proper CORS origins
- [ ] Set up proper firewall rules
- [ ] Enable database encryption
- [ ] Regular security updates

### 2. API Key Management

**Best Practices:**
- [ ] Use descriptive names for API keys
- [ ] Set appropriate expiration dates
- [ ] Grant minimal required permissions
- [ ] Rotate keys regularly
- [ ] Monitor key usage
- [ ] Revoke unused keys immediately

### 3. Monitoring & Alerting

**Recommended Monitoring:**
- [ ] Failed authentication attempts
- [ ] Rate limit violations
- [ ] Unusual access patterns
- [ ] Admin operations
- [ ] API key usage

### 4. Data Protection

**Security Measures:**
- [ ] Passwords hashed with Argon2
- [ ] API keys hashed before storage
- [ ] JWT tokens with expiration
- [ ] Input validation and sanitization
- [ ] SQL injection prevention via ORM

## 🔍 Security Monitoring

### Audit Logs

**Log File Location:** `audit.log`

**Log Format:**
```json
{
  "timestamp": 1695678901.234,
  "method": "POST",
  "path": "/tools",
  "query_params": "page=1",
  "client_ip": "192.168.1.100",
  "user_agent": "MyService/1.0",
  "status_code": 201,
  "process_time": 0.0456,
  "auth_type": "Bearer",
  "content_length": "1024"
}
```

### Rate Limit Monitoring

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1695678960
```

**Rate Limit Exceeded Response:**
```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "retry_after": 60
}
```

## 🚀 Production Deployment

### Docker Security

```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Set security headers
ENV SECRET_KEY="your-production-secret-key"
ENV ALLOWED_ORIGINS="https://yourdomain.com"
```

### Reverse Proxy Configuration

**Nginx Example:**
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    # SSL configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🆘 Incident Response

### Security Incident Checklist

1. **Immediate Response:**
   - [ ] Identify affected systems
   - [ ] Isolate compromised components
   - [ ] Preserve evidence (logs, tokens)
   - [ ] Notify stakeholders

2. **Investigation:**
   - [ ] Review audit logs
   - [ ] Check for unauthorized access
   - [ ] Identify attack vector
   - [ ] Assess data exposure

3. **Recovery:**
   - [ ] Revoke compromised credentials
   - [ ] Update security configurations
   - [ ] Patch vulnerabilities
   - [ ] Monitor for continued threats

4. **Post-Incident:**
   - [ ] Document lessons learned
   - [ ] Update security procedures
   - [ ] Conduct security review
   - [ ] Implement additional controls

## 📞 Support

For security-related questions or to report vulnerabilities:

- **Email**: security@yourdomain.com
- **Documentation**: [Security Guide](SECURITY.md)
- **API Documentation**: http://localhost:8000/docs

---

**⚠️ Important:** This security system is designed for production use but requires proper configuration and monitoring. Always follow security best practices and keep the system updated.
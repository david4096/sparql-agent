# Security Best Practices

Security guidelines for deploying SPARQL Agent in production.

## API Key Management

### Use Environment Variables

```bash
# Never hardcode API keys
export ANTHROPIC_API_KEY="sk-ant-your-key"
export OPENAI_API_KEY="sk-your-key"
```

### Use Secrets Management

```python
# Use a secrets manager
from aws_secretsmanager import get_secret

api_key = get_secret("sparql-agent/anthropic-key")
agent = SPARQLAgent(llm_provider="anthropic", api_key=api_key)
```

### Rotate Keys Regularly

```bash
# Rotate API keys every 90 days
# Use different keys for dev/staging/production
```

## Query Validation

### Validate Before Execution

```python
from sparql_agent.query import QueryValidator

validator = QueryValidator()

is_valid, errors = validator.validate(sparql)
if not is_valid:
    raise SecurityError("Invalid query")
```

### Block Dangerous Operations

```python
class SecurityValidator:
    BLOCKED_PATTERNS = [
        "DELETE",
        "INSERT",
        "DROP",
        "CLEAR",
        "CREATE",
        "LOAD"
    ]

    def validate(self, query: str) -> bool:
        query_upper = query.upper()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in query_upper:
                raise SecurityError(f"Blocked operation: {pattern}")
        return True
```

## Input Sanitization

### Sanitize User Input

```python
def sanitize_query(query: str) -> str:
    # Remove potentially malicious characters
    dangerous_chars = [";", "--", "/*", "*/"]
    for char in dangerous_chars:
        query = query.replace(char, "")
    return query

# Use sanitized input
clean_query = sanitize_query(user_input)
results = agent.query(clean_query)
```

## Rate Limiting

### Implement Rate Limits

```yaml
# config.yaml
web:
  rate_limit:
    enabled: true
    requests_per_minute: 60
    burst: 10
```

### Per-User Limits

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_api_key)

@app.post("/api/query")
@limiter.limit("60/minute")
async def query_endpoint(request: QueryRequest):
    # Process query
    pass
```

## Authentication & Authorization

### API Key Authentication

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
```

### JWT Authentication

```python
from fastapi.security import HTTPBearer
from jose import jwt

security = HTTPBearer()

async def verify_token(token: str = Depends(security)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401)
```

### Role-Based Access Control

```python
class Permissions:
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

def require_permission(permission: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Check user permission
            if not user.has_permission(permission):
                raise HTTPException(status_code=403)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.post("/api/query")
@require_permission(Permissions.READ)
async def query_endpoint():
    pass
```

## HTTPS/TLS

### Use HTTPS Only

```python
# Force HTTPS
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)
```

### Configure TLS

```python
import ssl

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

uvicorn.run(app, host="0.0.0.0", port=443, ssl_context=ssl_context)
```

## CORS Configuration

### Restrict Origins

```yaml
# config.yaml
web:
  cors:
    enabled: true
    allow_origins:
      - "https://myapp.com"
      - "https://app.example.com"
    allow_methods:
      - GET
      - POST
    allow_credentials: true
```

## Logging & Monitoring

### Log Security Events

```python
import logging

security_logger = logging.getLogger("security")

def log_security_event(event_type: str, details: dict):
    security_logger.warning(
        "Security event",
        extra={
            "type": event_type,
            "details": details,
            "timestamp": datetime.now()
        }
    )

# Log failed authentication
log_security_event("auth_failure", {"ip": request.client.host})
```

### Monitor Suspicious Activity

```python
from collections import defaultdict
from datetime import datetime, timedelta

class SecurityMonitor:
    def __init__(self):
        self.failed_attempts = defaultdict(list)

    def record_failure(self, ip: str):
        self.failed_attempts[ip].append(datetime.now())

        # Check for brute force
        recent = [
            t for t in self.failed_attempts[ip]
            if t > datetime.now() - timedelta(minutes=5)
        ]

        if len(recent) > 10:
            self.block_ip(ip)
```

## Data Protection

### Encrypt Sensitive Data

```python
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())

    def decrypt(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()
```

### Sanitize Logs

```python
def sanitize_log_data(data: dict) -> dict:
    """Remove sensitive information from logs"""
    sensitive_keys = ["api_key", "password", "token"]

    sanitized = data.copy()
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = "***REDACTED***"

    return sanitized
```

## Dependency Security

### Keep Dependencies Updated

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
uv sync --upgrade
```

### Pin Versions

```toml
# pyproject.toml
dependencies = [
    "rdflib==7.0.0",  # Pin exact version
    "SPARQLWrapper>=2.0.0,<3.0.0",  # Pin major version
]
```

## Security Headers

### Add Security Headers

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

# Trust only specific hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["sparql-agent.example.com"]
)

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

## Firewall Rules

### Configure Firewall

```bash
# Allow only specific IPs
ufw allow from 192.168.1.0/24 to any port 8000

# Block all other traffic
ufw default deny incoming
ufw enable
```

## Backup & Recovery

### Regular Backups

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf backup-$DATE.tar.gz config/ data/
aws s3 cp backup-$DATE.tar.gz s3://backups/
```

## Security Checklist

- [ ] API keys in secrets manager, not code
- [ ] HTTPS enabled with valid certificate
- [ ] Rate limiting configured
- [ ] Authentication implemented
- [ ] Query validation enabled
- [ ] CORS properly configured
- [ ] Security headers added
- [ ] Logging enabled for security events
- [ ] Regular security updates
- [ ] Firewall configured
- [ ] Backups automated
- [ ] Penetration testing performed
- [ ] Security monitoring active
- [ ] Incident response plan documented

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.org/dev/security/)

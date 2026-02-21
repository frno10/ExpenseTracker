# Security Implementation Guide

This document describes the security measures that exist in the Expense Tracker codebase. **Important: most of these features are coded but not active in the running application.** See the status column in each section.

## Status Summary

| Feature | Code Exists | Active in Running App |
|---------|:-----------:|:--------------------:|
| Supabase JWT Auth | Yes | Yes |
| Input Validation module | Yes | **No** (middleware not applied) |
| CSRF Protection | Yes | **No** (middleware not applied) |
| Security Headers | Yes | **No** (middleware not applied) |
| Rate Limiting | Yes | **No** (middleware not applied) |
| Field Encryption | Yes | **No** (not used in any active code path) |
| Audit Logging | Yes | **No** (module not imported by main.py) |
| Session Management | Yes | **No** (Redis not configured) |

### Critical Security Issue

**JWT signature verification is disabled** in `main.py:297`:
```python
jwt.decode(token, ..., options={"verify_signature": False})
```
This means **any JWT token is accepted as valid**, regardless of whether it was issued by Supabase. This must be fixed before production use.

Additionally, sensitive data is logged:
- Password lengths logged at `main.py:357`
- Token previews logged at `main.py:264`
- Supabase URL logged on requests

## Security Features (Coded but Not Active)

### 1. Authentication & Authorization
- **Active:** JWT-based authentication via Supabase Auth
- **Not active:** Role-based access control, session management with expiration
- **Issue:** JWT `verify_signature: False` bypasses all token validation

### 2. Input Validation & Sanitization
- **Code location:** `app/core/validation.py`
- **Status:** Not active - middleware not applied to the FastAPI app
- Features include: XSS prevention, SQL injection detection, file upload validation

### 3. CSRF Protection
- **Code location:** `app/core/security_middleware.py`
- **Status:** Not active - middleware not applied
- Implements double-submit cookie pattern with HMAC-SHA256

### 4. Security Headers
- **Code location:** `app/core/security_middleware.py`
- **Status:** Not active - middleware not applied
- Includes: CSP, X-Frame-Options, X-Content-Type-Options, HSTS, X-XSS-Protection

### 5. Session Security
- **Code location:** `app/core/security_middleware.py`
- **Status:** Not active - no Redis configured
- Designed for: session expiration, IP validation, hijacking detection

### 6. Data Encryption
- **Code location:** `app/core/encryption.py`
- **Status:** Not active - not imported or used by main.py
- Implements: Fernet-based field encryption, PBKDF2 key derivation

### 7. Audit Logging
- **Code location:** `app/core/audit.py`
- **Status:** Not active - not imported or used by main.py
- Includes: 30+ event types, severity levels, database storage model

### 8. Rate Limiting
- **Code location:** `app/core/security_middleware.py`
- **Status:** Not active - middleware not applied
- slowapi dependency is in requirements.txt

## What IS Active

The only security measures currently active in the running application are:
1. **CORS middleware** - Configured in main.py
2. **Supabase Auth** - JWT tokens issued by Supabase (but signature verification is disabled)
3. **HTTPS** - If deployed behind a reverse proxy that handles TLS

## Activating Security Features

To activate the disconnected security features, the middleware needs to be applied in `main.py`. The backup file `main_complex_backup.py` shows how this was previously configured. However, the middleware modules depend on SQLAlchemy database sessions which are not set up in the current `main.py`, so reconnection requires resolving the data access pattern mismatch.

### Priority Fixes

1. **Fix JWT verification** - Remove `verify_signature: False`, validate against Supabase JWT secret
2. **Remove sensitive logging** - Stop logging password lengths, token previews
3. **Apply security headers middleware** - This can work independently of database choice
4. **Enable rate limiting** - slowapi can work with the current setup
5. **Apply CSRF middleware** - Requires frontend integration for token handling

## Code Examples

The code examples below show the API of the existing (but not active) security modules.

### CSRF Protection
```python
# From app/core/security_middleware.py
from app.core.security_middleware import CSRFProtectionMiddleware

# Would need to be added to app middleware stack:
# app.add_middleware(CSRFProtectionMiddleware, secret_key=settings.SECRET_KEY)
```

### Input Validation
```python
# From app/core/validation.py
from app.core.validation import InputValidator

# Validate and sanitize user input
if not InputValidator.validate_email(email):
    raise HTTPException(400, "Invalid email format")
```

### Audit Logging
```python
# From app/core/audit.py
from app.core.audit import AuditEventType, AuditSeverity

# Requires async database session to store logs
```

### Field Encryption
```python
# From app/core/encryption.py
from app.core.encryption import FieldEncryption

encryption = FieldEncryption()
encrypted = encryption.encrypt(sensitive_data)
decrypted = encryption.decrypt(encrypted)
```

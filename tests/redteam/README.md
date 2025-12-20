# Red Team Security Tests

Adversarial and security-focused tests to identify vulnerabilities.

## Purpose

- Test authentication bypass attempts
- SQL injection prevention
- XSS prevention
- CSRF protection
- Rate limiting effectiveness
- Input validation edge cases
- Security headers

## Guidelines

- Use `@pytest.mark.redteam` decorator
- Test malicious inputs and attack vectors
- Verify security controls are effective
- Document expected security behavior

## Structure

```
redteam/
├── test_auth_security.py        # Authentication security tests
├── test_injection.py            # SQL/NoSQL injection tests
├── test_xss.py                  # Cross-site scripting tests
├── test_rate_limiting.py        # Rate limit bypass tests
└── test_input_validation.py     # Malicious input handling
```

## Example

```python
import pytest
from httpx import AsyncClient

@pytest.mark.redteam
@pytest.mark.asyncio
async def test_sql_injection_in_login(client: AsyncClient):
    """Test that SQL injection is prevented in login"""
    malicious_inputs = [
        "' OR '1'='1",
        "admin'--",
        "' OR 1=1--",
        "'; DROP TABLE users;--",
    ]

    for malicious in malicious_inputs:
        response = await client.post("/auth/login", data={
            "username": malicious,
            "password": "anything",
        })
        # Should return 401 Unauthorized, not 500 Server Error
        assert response.status_code == 401, \
            f"SQL injection may be possible with input: {malicious}"


@pytest.mark.redteam
@pytest.mark.asyncio
async def test_password_strength_enforcement(client: AsyncClient):
    """Test that weak passwords are rejected"""
    weak_passwords = [
        "password",        # Common word
        "12345678",        # Numbers only
        "abcdefgh",        # Letters only
        "Pass123",         # Too short
        "password123",     # No uppercase
        "PASSWORD123",     # No lowercase
        "Password",        # No numbers
    ]

    for weak_pass in weak_passwords:
        response = await client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": weak_pass,
        })
        # Should return 422 Validation Error
        assert response.status_code == 422, \
            f"Weak password accepted: {weak_pass}"
```

## Security Testing Checklist

- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Authentication bypass attempts
- [ ] Authorization bypass attempts
- [ ] Password strength enforcement
- [ ] Rate limiting effectiveness
- [ ] Session fixation prevention
- [ ] Sensitive data exposure
- [ ] Security headers (HSTS, CSP, etc.)
- [ ] File upload restrictions
- [ ] API endpoint enumeration
- [ ] Error message information disclosure

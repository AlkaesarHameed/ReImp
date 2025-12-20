# API Documentation

This document provides comprehensive API documentation for the Python FastAPI Starter Template.

**Base URL**: `http://localhost:8000` (development) | `https://api.yourdomain.com` (production)

**Interactive Docs**: Visit `/docs` (Swagger UI) or `/redoc` (ReDoc) for interactive API documentation.

---

## Table of Contents

- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Request/Response Format](#requestresponse-format)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Pagination](#pagination)
- [Versioning](#versioning)

---

## Authentication

### Overview

The API uses **JWT (JSON Web Tokens)** for authentication with a two-token system:

- **Access Token**: Short-lived (15 minutes), used for API requests
- **Refresh Token**: Long-lived (7 days), used to obtain new access tokens

**Flow:**

1. Login with credentials → Receive access + refresh tokens
2. Include access token in `Authorization` header for all requests
3. When access token expires → Use refresh token to get new access token
4. When refresh token expires → Re-authenticate with credentials

### Authentication Endpoints

#### 1. Login

**POST** `/auth/login`

Authenticate with username/email and password to receive JWT tokens.

**Request:**

```http
POST /auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "YourPassword123!"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:**

- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Invalid credentials
- `422 Unprocessable Entity`: Validation error

**Example (curl):**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"YourPassword123!"}'
```

**Example (Python):**

```python
import requests

response = requests.post(
    "http://localhost:8000/auth/login",
    json={"username": "user@example.com", "password": "YourPassword123!"}
)

tokens = response.json()
access_token = tokens["access_token"]
```

---

#### 2. Refresh Token

**POST** `/auth/refresh`

Obtain a new access token using a valid refresh token.

**Request:**

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:**

- `401 Unauthorized`: Invalid or expired refresh token

---

#### 3. Logout

**POST** `/auth/logout`

Invalidate the current refresh token (access token expires naturally).

**Request:**

```http
POST /auth/logout
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**

```json
{
  "message": "Successfully logged out"
}
```

---

### Using Access Tokens

Include the access token in the `Authorization` header for all protected endpoints:

```http
GET /users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Example (curl):**

```bash
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Example (Python):**

```python
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/users/me", headers=headers)
```

---

## API Endpoints

### Health Check

#### Get Health Status

**GET** `/health`

Check API and database health (unauthenticated).

**Response (200 OK):**

```json
{
  "status": "healthy",
  "database": "up",
  "redis": "up",
  "version": "1.0.0",
  "timestamp": "2025-11-14T12:00:00Z"
}
```

---

### User Management

#### 1. Register User

**POST** `/users/register`

Create a new user account (unauthenticated).

**Request:**

```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "full_name": "New User",
  "password": "SecurePassword123!"
}
```

**Password Requirements:**

- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (`!@#$%^&*()_+-=[]{}|;:,.<>?`)

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newuser@example.com",
  "username": "newuser",
  "full_name": "New User",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-11-14T12:00:00Z",
  "last_login": null
}
```

**Errors:**

- `400 Bad Request`: Email or username already exists
- `422 Unprocessable Entity`: Password doesn't meet requirements

---

#### 2. Get Current User

**GET** `/users/me`

Get the currently authenticated user's profile.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "user",
  "full_name": "John Doe",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-11-01T10:00:00Z",
  "last_login": "2025-11-14T11:30:00Z"
}
```

**Errors:**

- `401 Unauthorized`: Missing or invalid access token

---

#### 3. Update Current User

**PUT** `/users/me`

Update the currently authenticated user's profile.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Request (partial update allowed):**

```json
{
  "full_name": "John Smith",
  "email": "johnsmith@example.com"
}
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "johnsmith@example.com",
  "username": "user",
  "full_name": "John Smith",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-11-01T10:00:00Z",
  "last_login": "2025-11-14T11:30:00Z"
}
```

**Errors:**

- `400 Bad Request`: Email already taken
- `401 Unauthorized`: Missing or invalid access token

---

#### 4. Change Password

**POST** `/users/me/change-password`

Change the current user's password.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Request:**

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!"
}
```

**Response (200 OK):**

```json
{
  "message": "Password changed successfully"
}
```

**Errors:**

- `400 Bad Request`: Current password incorrect
- `422 Unprocessable Entity`: New password doesn't meet requirements

---

#### 5. List Users (Admin Only)

**GET** `/users`

List all users (requires superuser).

**Headers:**

```
Authorization: Bearer {access_token}
```

**Query Parameters:**

- `skip` (int, default: 0): Number of records to skip
- `limit` (int, default: 100, max: 100): Number of records to return

**Response (200 OK):**

```json
{
  "total": 150,
  "skip": 0,
  "limit": 100,
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user1@example.com",
      "username": "user1",
      "full_name": "User One",
      "is_active": true,
      "created_at": "2025-11-01T10:00:00Z"
    },
    ...
  ]
}
```

**Errors:**

- `403 Forbidden`: User is not a superuser

---

### Example: Full User Registration and Login Flow

**Python Example:**

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Register new user
register_response = requests.post(
    f"{BASE_URL}/users/register",
    json={
        "email": "alice@example.com",
        "username": "alice",
        "full_name": "Alice Johnson",
        "password": "SecurePassword123!"
    }
)
user = register_response.json()
print(f"Registered user: {user['id']}")

# 2. Login
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "username": "alice@example.com",
        "password": "SecurePassword123!"
    }
)
tokens = login_response.json()
access_token = tokens["access_token"]

# 3. Get current user profile
headers = {"Authorization": f"Bearer {access_token}"}
profile_response = requests.get(f"{BASE_URL}/users/me", headers=headers)
profile = profile_response.json()
print(f"Profile: {profile['full_name']}")

# 4. Update profile
update_response = requests.put(
    f"{BASE_URL}/users/me",
    headers=headers,
    json={"full_name": "Alice M. Johnson"}
)
updated_profile = update_response.json()
print(f"Updated: {updated_profile['full_name']}")
```

---

## Request/Response Format

### Content Types

- **Request**: `application/json`
- **Response**: `application/json`

### Timestamps

All timestamps use **ISO 8601** format in **UTC**:

```
2025-11-14T12:34:56Z
```

### UUIDs

All entity IDs use **UUID v4** format:

```
550e8400-e29b-41d4-a716-446655440000
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-11-14T12:34:56Z"
}
```

### HTTP Status Codes

| Code  | Meaning               | Usage                                        |
| ----- | --------------------- | -------------------------------------------- |
| `200` | OK                    | Successful GET, PUT, PATCH                   |
| `201` | Created               | Successful POST (resource created)           |
| `204` | No Content            | Successful DELETE                            |
| `400` | Bad Request           | Invalid request data or business logic error |
| `401` | Unauthorized          | Missing or invalid authentication            |
| `403` | Forbidden             | Authenticated but not authorized for action  |
| `404` | Not Found             | Resource doesn't exist                       |
| `422` | Unprocessable Entity  | Validation error (Pydantic)                  |
| `429` | Too Many Requests     | Rate limit exceeded                          |
| `500` | Internal Server Error | Unexpected server error                      |

### Common Error Codes

| Error Code                | Description                        |
| ------------------------- | ---------------------------------- |
| `INVALID_CREDENTIALS`     | Username/password incorrect        |
| `TOKEN_EXPIRED`           | JWT token has expired              |
| `TOKEN_INVALID`           | JWT token is malformed or invalid  |
| `USER_NOT_FOUND`          | User doesn't exist                 |
| `USER_INACTIVE`           | User account is deactivated        |
| `EMAIL_ALREADY_EXISTS`    | Email already registered           |
| `USERNAME_ALREADY_EXISTS` | Username already taken             |
| `WEAK_PASSWORD`           | Password doesn't meet requirements |
| `PERMISSION_DENIED`       | User lacks required permissions    |
| `RATE_LIMIT_EXCEEDED`     | Too many requests                  |

### Example Error Responses

**401 Unauthorized:**

```json
{
  "detail": "Could not validate credentials",
  "error_code": "TOKEN_INVALID",
  "timestamp": "2025-11-14T12:34:56Z"
}
```

**422 Validation Error:**

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 12 characters long",
      "type": "value_error"
    }
  ]
}
```

---

## Rate Limiting

### Limits

Default rate limits (configurable via environment variables):

- **Per Minute**: 60 requests
- **Per Hour**: 1000 requests

### Rate Limit Headers

Responses include rate limit information:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1699968000
```

### Rate Limit Exceeded Response

**429 Too Many Requests:**

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 30,
  "timestamp": "2025-11-14T12:34:56Z"
}
```

---

## Pagination

### Query Parameters

For list endpoints:

- `skip` (int, default: 0): Number of items to skip
- `limit` (int, default: 100, max: 100): Number of items to return

### Response Format

```json
{
  "total": 250,
  "skip": 0,
  "limit": 100,
  "items": [...]
}
```

### Example

```bash
# Get first 50 users
curl -X GET "http://localhost:8000/users?skip=0&limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Get next 50 users
curl -X GET "http://localhost:8000/users?skip=50&limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## Versioning

### Current Version

API Version: **v1** (default, no prefix required)

### Future Versioning

When breaking changes are introduced, versions will be prefixed:

```
/v1/users
/v2/users
```

Versioning strategy:

- **Major version**: Breaking changes
- URL-based versioning (not header-based)
- Previous versions supported for 12 months after new version release

---

## OpenAPI Specification

### Interactive Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Download OpenAPI Schema

```bash
curl http://localhost:8000/openapi.json > openapi.json
```

### Generate Client SDKs

Use [OpenAPI Generator](https://openapi-generator.tech/) to generate client libraries:

```bash
# Generate Python client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g python \
  -o ./client-python

# Generate TypeScript client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-fetch \
  -o ./client-typescript
```

---

## Testing the API

### Using cURL

```bash
# Set base URL and credentials
export API_URL="http://localhost:8000"
export USERNAME="user@example.com"
export PASSWORD="YourPassword123!"

# Login and save access token
export ACCESS_TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

# Get current user
curl -X GET "$API_URL/users/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Using Postman

1. Import OpenAPI schema: `http://localhost:8000/openapi.json`
2. Create environment with `BASE_URL` variable
3. Add authentication script to automatically use tokens

### Using HTTPie

```bash
# Login
http POST :8000/auth/login username=user@example.com password=YourPassword123!

# Authenticated request
http GET :8000/users/me Authorization:"Bearer $ACCESS_TOKEN"
```

---

## Best Practices

### Security

1. **Always use HTTPS** in production
2. **Never log tokens** or sensitive data
3. **Validate all inputs** (API does this automatically with Pydantic)
4. **Use short-lived access tokens** (15 minutes)
5. **Rotate refresh tokens** periodically

### Performance

1. **Use pagination** for large result sets
2. **Cache responses** when appropriate (Redis)
3. **Request only needed fields** (future: field selection)
4. **Respect rate limits** to avoid throttling

### Error Handling

1. **Check status codes** before parsing response
2. **Handle rate limiting** with exponential backoff
3. **Log errors** for debugging
4. **Provide user-friendly messages** to end users

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [HTTP Status Codes](https://httpstatuses.com/)

---

**Last Updated**: 2025-11-14

**Version**: 1.0.0

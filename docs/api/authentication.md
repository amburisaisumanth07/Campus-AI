# Authentication API Reference

## Endpoints

### 1. Register Student Account
- **URL**: `/api/auth/register`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:
  ```json
  {
    "name": "Jane Student",
    "email": "jane@campusai.edu",
    "password": "SecurePassword123"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": 1,
    "name": "Jane Student",
    "email": "jane@campusai.edu",
    "role": "STUDENT",
    "is_active": true,
    "created_at": "2026-08-12T19:30:00Z",
    "updated_at": "2026-08-12T19:30:00Z"
  }
  ```
- **Error Responses**:
  - `409 Conflict`: Email already registered.
  - `422 Unprocessable Entity`: Validation failure.

---

### 2. Login & Obtain JWT Token
- **URL**: `/api/auth/login`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:
  ```json
  {
    "email": "jane@campusai.edu",
    "password": "SecurePassword123"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "<jwt_string>",
    "token_type": "bearer"
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: Invalid email or password.
  - `403 Forbidden`: Account deactivated.

---

### 3. Get Current Authenticated User
- **URL**: `/api/auth/me`
- **Method**: `GET`
- **Auth Required**: Yes (`Authorization: Bearer <jwt_string>`)
- **Response** (`200 OK`):
  ```json
  {
    "id": 1,
    "name": "Jane Student",
    "email": "jane@campusai.edu",
    "role": "STUDENT",
    "is_active": true,
    "created_at": "2026-08-12T19:30:00Z",
    "updated_at": "2026-08-12T19:30:00Z"
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: Missing, expired, or invalid token.

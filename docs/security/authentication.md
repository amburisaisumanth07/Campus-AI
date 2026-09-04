# CampusAI Security & Authentication Architecture

## Overview
CampusAI implements a stateless, token-based authentication mechanism powered by FastAPI, JSON Web Tokens (JWT), and standard password hashing with bcrypt.

## Password Hashing
- **Algorithm**: `bcrypt` (salted, work factor 12)
- **Rules**: Plaintext passwords are never stored or logged anywhere in the application. Standard input truncation at 72 bytes is applied to enforce bcrypt compliance.

## Token / Session Strategy
- **Format**: JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).
- **Secret Management**: `AUTH_SECRET_KEY` is loaded from environment variables (`.env`).
- **Expiry**: Default access token lifetime is set to 60 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Frontend Storage**: For this Single Page Application (SPA) development phase, the JWT is stored in `localStorage` under `campusai_token`. 
  - *Security Consideration*: `localStorage` is accessible to JavaScript running on the origin. Production deployments should evaluate moving to HttpOnly, SameSite cookies to mitigate XSS risks, or pair localStorage with strict Content Security Policies (CSP).

## Role-Based Access Control (RBAC)
CampusAI enforces strict two-tier authorization:
1. **`STUDENT`**: Default role assigned to self-registered users.
2. **`ADMIN`**: Privileged role capable of managing system resources.

### Route Guards
- **Backend**: FastAPI dependency injection (`require_student`, `require_admin`).
- **Frontend**: React Router guard components (`<ProtectedRoute />`, `<AdminRoute />`).

## Local Admin Account Creation
Public registration strictly assigns the `STUDENT` role. Self-registering as an `ADMIN` is prohibited. Initial admin provisioning for local development is handled via a dedicated seed script reading from environment variables:
```bash
python -m scripts.create_admin
```
Reading credentials from `.env` (`ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`).

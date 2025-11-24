# Authentication Service

Centralized authentication and user management for the WithOps platform.

## Overview

The Authentication Service is responsible for:

- Auth0 JWT token validation
- User creation and profile management
- Session tracking
- Providing authentication endpoints for all microservices

## Features

- **JWT Validation**: Centralized Auth0 token verification using JWKS
- **User Management**: Create and update user profiles
- **Session Tracking**: Monitor user authentication sessions
- **Email Validation**: Sanitize and validate user email addresses
- **Monitoring**: Prometheus metrics and OpenTelemetry tracing

## Endpoints

### Authentication

- `POST /api/auth/callback` - Handle Auth0 authentication callback
- `GET /api/auth/me` - Get current user profile
- `GET /api/auth/validate` - Validate JWT token (for microservices)
- `GET /api/auth/health` - Health check

## Environment Variables

```bash
# Auth0 Configuration
AUTH0_DOMAIN=dev-sabxychpf6paj41u.us.auth0.com
AUTH0_API_AUDIENCE=https://api.withops.com

# Database Configuration
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis Configuration (optional)
REDIS_URL=redis://redis:6379

# Service Configuration
SERVICE_PORT=8006
SERVICE_NAME=auth-service
LOG_LEVEL=INFO

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
OTLP_ENDPOINT=http://jaeger:4318/v1/traces

# Environment
ENVIRONMENT=development
TEST_MODE=false
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run service
uvicorn main:app --host 0.0.0.0 --port 8006 --reload
```

## Running with Docker

```bash
# Build and run
docker-compose up auth-service

# Or build standalone
docker build -f Dockerfile -t auth-service .
docker run -p 8006:8006 auth-service
```

## Dependencies

### External Dependencies

- PostgreSQL/Supabase - User data persistence
- Auth0 - JWT authentication provider

### Internal Services

None - Auth service is independent and used by other services

## Database Schema

### Users Table

- `id` - UUID primary key
- `auth_user_id` - Auth0 user ID (unique)
- `email` - User email address
- `name` - User display name
- `avatar_url` - Profile picture URL
- `created_at` - Account creation timestamp
- `last_login` - Last login timestamp

## Usage by Other Services

Other microservices can validate tokens by:

1. **Direct JWT validation** (recommended for performance):

   - Use shared `withops-common` library
   - Validate tokens using Auth0 JWKS
   - Cache validation results

2. **Remote validation** (higher latency):
   - Call `GET /api/auth/validate` endpoint
   - Returns user ID if token is valid

## Monitoring

- **Metrics**: Prometheus metrics at `/metrics`
- **Health**: Health check at `/health`
- **Traces**: OpenTelemetry traces sent to Jaeger

## Security

- JWT tokens validated using Auth0 RS256 with JWKS
- User session tracking for security monitoring
- Email validation and sanitization
- Test mode disabled in production

## Development

### Test Mode

Set `TEST_MODE=true` to use mock token validation (development only).

### Email Handling

The service handles:

- Email validation with regex
- Common typo corrections (gamil.com → gmail.com)
- Placeholder emails for users without valid email
- Email upgrading from placeholder to real email

## Architecture

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   Kong Gateway  │
└────────┬────────┘
         │
         ▼
┌──────────────────┐       ┌──────────┐
│  Auth Service    │──────▶│  Auth0   │
│  (Port 8006)     │       │  (JWKS)  │
└────────┬─────────┘       └──────────┘
         │
         ▼
┌──────────────────┐
│   PostgreSQL     │
│   (User Data)    │
└──────────────────┘
```

## Migration from Backend

This service extracts authentication logic from:

- `backend/api/routes/auth.py`
- `backend/core/security.py`

All microservices should use this centralized auth service instead of duplicating auth code.

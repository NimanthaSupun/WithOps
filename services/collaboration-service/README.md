# Collaboration Service

Organization-based collaboration API for secure multi-user threat modeling and workspace collaboration.

## Features

- **Organization Members**: List users who have installed the app in an organization
- **Collaboration Invites**: Create and manage collaboration invitations
- **Session Management**: Track active collaboration sessions
- **Authorization**: Secure access based on GitHub organization membership

## Endpoints

### Members

- `GET /api/collaboration/organization/{org_name}/members` - Get organization members

### Invitations

- `POST /api/collaboration/invite` - Create collaboration invite
- `GET /api/collaboration/invites/pending` - Get pending invitations
- `POST /api/collaboration/invites/{invite_id}/accept` - Accept invitation
- `POST /api/collaboration/invites/{invite_id}/decline` - Decline invitation

### Sessions

- `GET /api/collaboration/organization/{org_name}/sessions` - Get collaboration sessions
- `GET /api/collaboration/session/{session_id}/status` - Get session status

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://redis:6379/0
OTLP_ENDPOINT=http://jaeger:4318/v1/traces
ENVIRONMENT=development
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn main:app --host 0.0.0.0 --port 8105 --reload
```

## Docker

```bash
# Build
docker build -t collaboration-service .

# Run
docker run -p 8105:8105 --env-file .env collaboration-service
```

## Architecture

- **FastAPI**: Web framework
- **PostgreSQL**: Database (shared with backend)
- **Redis**: Caching and real-time features
- **Prometheus**: Metrics collection
- **OpenTelemetry**: Distributed tracing

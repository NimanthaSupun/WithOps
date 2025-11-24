# WithOps Common Library

Shared Python library for WithOps microservices.

## Features

- **Pydantic Models**: Shared data models for users, organizations, events
- **Service Clients**: HTTP clients with retry logic for inter-service communication
- **Middleware**: JWT authentication, request logging with correlation IDs
- **Utilities**: Redis cache wrapper, configuration management

## Installation

### Local Development (Editable Install)

```bash
# From any service directory
pip install -e ../../shared/withops-common
```

### From Git Repository

```bash
pip install git+https://github.com/WithOps-Com/withops-common.git@v0.1.0
```

## Usage

### Models

```python
from withops_common.models import UserResponse, OrganizationResponse, RepoSyncedEvent

user = UserResponse(
    id="123",
    auth_user_id="auth0|123",
    email="user@example.com",
    created_at=datetime.utcnow()
)
```

### Service Clients

```python
from withops_common.clients import BaseServiceClient

# Create client for AI service
ai_client = BaseServiceClient(base_url="http://ai-service:8001")

# Make request with automatic retry
response = await ai_client.post("/api/ai/analyze", json={"data": "..."})
```

### Middleware

```python
from fastapi import FastAPI, Depends
from withops_common.middleware import get_current_user, request_id_middleware

app = FastAPI()

# Add request ID middleware
app.middleware("http")(request_id_middleware)

# Use authentication
@app.get("/protected")
async def protected_route(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}
```

### Cache

```python
from withops_common.utils import RedisCache

cache = RedisCache("redis://redis:6379")
await cache.connect()

# Set value with expiration
await cache.set("key", {"data": "value"}, expire=3600)

# Get value
data = await cache.get("key")

# Publish event
await cache.publish("events", {"type": "user.created", "id": "123"})
```

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest
```

## Version History

- **0.1.0**: Initial release with models, clients, middleware, and utilities

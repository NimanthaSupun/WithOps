# GitHub Service

Microservice for GitHub integration operations including:

- GitHub App installations and OAuth
- Organization/repository management
- Workflow parsing and analysis
- PR creation
- GitHub Actions auditing

## Architecture

- **FastAPI** - Web framework
- **Redis** - Caching layer
- **Prometheus** - Metrics
- **OpenTelemetry** - Distributed tracing

## Endpoints

### Organization Discovery

- `GET /api/github/organizations/discover` - Start OAuth flow
- `GET /api/github/organizations/callback` - Handle OAuth callback
- `POST /api/github/organizations/{org_name}/install` - Generate installation URL

### Workspace Operations

- `GET /api/github/workspace/{org_name}` - Get organization workspace data
- `GET /api/github/installations` - List all installations
- `GET /api/github/organizations/{org_name}/stats` - Get org statistics

### Workflow Operations

- `GET /api/github/workspace/{org_name}/workflow/{repo_name}/{workflow_path}` - Get workflow content
- `GET /api/github/workspace/{org_name}/actions/detailed` - Get all actions

### Cache Management

- `DELETE /api/github/workspace/{org_name}/cache` - Clear organization cache

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (copy from .env.example)
cp .env.example .env

# Run service
uvicorn main:app --host 0.0.0.0 --port 8002
```

## Running with Docker

```bash
# Build and run
docker-compose up github-service

# Or build standalone
docker build -f Dockerfile -t github-service .
docker run -p 8002:8002 github-service
```

## Environment Variables

See `.env.example` for required configuration:

- `GITHUB_APP_ID` - GitHub App ID
- `GITHUB_APP_CLIENT_ID` - GitHub App Client ID
- `GITHUB_APP_CLIENT_SECRET` - GitHub App Client Secret
- `GITHUB_PRIVATE_KEY_PATH` - Path to GitHub App private key
- `REDIS_URL` - Redis connection URL
- `DATABASE_URL` - PostgreSQL/Supabase connection URL

## Monitoring

- **Metrics**: `http://localhost:8002/metrics`
- **Health**: `http://localhost:8002/health`
- **Traces**: View in Jaeger UI at `http://localhost:16686`

## Development

The service follows the same pattern as the AI service with:

- Structured logging
- Prometheus metrics collection
- OpenTelemetry distributed tracing
- Redis caching for performance
- Comprehensive error handling

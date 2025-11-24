# Workspace Intelligence Service

Microservice for workspace analysis, DevSecOps maturity scoring, and repository tree management.

## Features

- **Workspace Analysis**: Comprehensive analysis of organization workspaces
- **DevSecOps Maturity Scoring**: Automated assessment of security practices
- **Repository Tree Management**: Save and manage repository folder structures
- **Security Practice Detection**: Detect SAST, SCA, DAST, secret scanning tools
- **Workflow Analysis**: Parse and analyze GitHub Actions workflows
- **Centralized Workflow Detection**: Identify reusable workflows

## Architecture

```
workspace-intelligence-service/
├── api/
│   └── routes/
│       ├── workspace_intelligence.py  # Workspace analysis endpoints
│       └── repository_tree.py         # Repository tree CRUD
├── core/
│   ├── workspace_analyzer.py          # Main analysis orchestrator
│   ├── security_practice_detector.py  # Security practice detection
│   ├── maturity_scorer.py             # DevSecOps maturity calculation
│   ├── workflow_parser.py             # GitHub Actions YAML parser
│   ├── repository_tree_manager.py     # Tree management logic
│   ├── workspace_intelligence_db.py   # Database operations
│   ├── github_service_client.py       # HTTP client for GitHub Service
│   └── redis_cache.py                 # Caching layer
├── database/
│   ├── models.py                      # SQLAlchemy models
│   └── config.py                      # Database configuration
├── main.py                            # FastAPI application
├── Dockerfile                         # Container configuration
└── requirements.txt                   # Python dependencies
```

## API Endpoints

### Workspace Intelligence

- `POST /api/workspace-intelligence/analyze-workspace` - Analyze entire workspace
- `POST /api/workspace-intelligence/analyze-project` - Analyze specific project
- `GET /api/workspace-intelligence/analysis/{id}` - Get analysis results
- `GET /api/workspace-intelligence/practices` - Get security practices

### Repository Tree

- `GET /api/repository-tree/{org_login}` - Get repository tree
- `POST /api/repository-tree/save` - Save repository tree
- `DELETE /api/repository-tree/{org_login}` - Delete repository tree
- `GET /api/repository-tree/{org_login}/statistics` - Get tree statistics

### Health & Metrics

- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics

## Dependencies

### Internal Services

- **GitHub Service** (port 8002) - Fetches organization/repository data
- **Redis** - Caching and performance optimization

### External Dependencies

- PostgreSQL/Supabase - Data persistence
- Redis - Caching layer

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run service
uvicorn main:app --host 0.0.0.0 --port 8104 --reload
```

## Running with Docker

```bash
# Build and run
docker-compose up workspace-intelligence-service

# Or build standalone
docker build -f Dockerfile -t workspace-intelligence-service .
docker run -p 8104:8104 workspace-intelligence-service
```

## Environment Variables

See `.env.example` for all configuration options.

Required variables:

- `DATABASE_URL` - PostgreSQL connection URL
- `REDIS_URL` - Redis connection URL
- `GITHUB_SERVICE_URL` - GitHub Service URL

## Monitoring

- **Metrics**: Prometheus metrics at `/metrics`
- **Health**: Health check at `/health`
- **Traces**: OpenTelemetry traces sent to Jaeger

## Database Models

- `repository_trees` - Saved repository folder structures
- `workspace_analyses` - Complete workspace analysis results
- `project_analyses` - Individual project analysis results

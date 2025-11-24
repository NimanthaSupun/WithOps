# Threat Modeling Service

Microservice for managing threat models, STRIDE/LINDDUN analysis, and security assessments.

## Features

- **Threat Model Management**: Create, update, delete threat models
- **STRIDE/LINDDUN Analysis**: Comprehensive threat analysis methodologies
- **AI-Powered Analysis**: Integration with AI Service for intelligent threat detection
- **Document Context**: Upload documents (PDF/DOCX) for enhanced threat analysis
- **Collaboration**: Multi-user collaboration with permissions
- **Version Control**: Track changes and maintain version history
- **Visual Canvas**: Store and manage threat model diagrams
- **Threat Library**: Predefined threat patterns and mitigations

## Architecture

```
threat-modeling-service/
├── app/
│   ├── routes/          # API endpoints
│   ├── services/        # Business logic
│   ├── models/          # Pydantic models
│   └── core/            # Core utilities
├── database/            # Database config and models
├── migrations/          # Database migrations
├── tests/               # Unit and integration tests
└── main.py             # Service entry point
```

## API Endpoints

### Threat Models

- `POST /api/v1/models` - Create threat model
- `GET /api/v1/models` - List threat models
- `GET /api/v1/models/{id}` - Get threat model
- `PUT /api/v1/models/{id}` - Update threat model
- `DELETE /api/v1/models/{id}` - Delete threat model

### Analysis

- `POST /api/v1/models/{id}/comprehensive-analysis` - Perform comprehensive analysis
- `GET /api/v1/models/{id}/analyses` - Get analysis history
- `POST /api/v1/models/{id}/analyses` - Save new analysis
- `DELETE /api/v1/models/{id}/analysis/{analysis_id}` - Delete analysis

### Documents

- `POST /api/v1/models/{id}/upload-document` - Upload context document

### Reference Data

- `GET /api/v1/library` - Get threat library
- `GET /api/v1/dashboard` - Get dashboard overview

## Dependencies

### Internal Services

- **AI Service** (port 8001) - Threat analysis and recommendations
- **Authentication Service** - JWT token validation

### External Dependencies

- PostgreSQL - Data persistence
- Redis - Caching layer

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start service
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

## Running with Docker

```bash
docker build -t threat-modeling-service .
docker run -p 8003:8003 --env-file .env threat-modeling-service
```

## Environment Variables

See `.env.example` for all configuration options.

## Monitoring

- **Metrics**: Prometheus metrics at `/metrics`
- **Health**: Health check at `/health`
- **Tracing**: OpenTelemetry traces exported to Jaeger

## Development

```bash
# Run tests
pytest

# Format code
black .

# Lint
flake8 .
```

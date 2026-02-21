# WithOps Microservices Architecture

## Overview

WithOps is a comprehensive DevSecOps platform built on a modern microservices architecture. The platform provides intelligent workspace analysis, AI-powered security recommendations, threat modeling, GitHub integration, and collaborative features to help development teams build secure applications.

## Architecture Principles

- **Service Isolation**: Each microservice owns its domain and can be deployed independently
- **Event-Driven Communication**: Services communicate via Redis pub/sub event bus for loose coupling
- **API Gateway Pattern**: Kong gateway provides unified entry point for all client requests
- **Observability First**: Built-in distributed tracing, metrics, and centralized logging
- **Security by Design**: Centralized authentication with Auth0 JWT validation

## System Architecture

```
┌─────────────┐
│   Clients   │
│ (Frontend)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│          Kong API Gateway (9000)            │
│  Routes: /api/ai, /api/github, /api/auth    │
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
┌──────▼──────┐         ┌──────▼──────────┐
│   Services  │         │  Events Hub     │
│             │◄────────┤ (Backend:9100)  │
│             │  Events │  WebSocket      │
└─────────────┘         └─────────────────┘
       │
       │
┌──────┴──────────────────────────────────────┐
│                                             │
▼                 ▼                 ▼         ▼
┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Redis │   │PostgreSQL│   │ Ollama   │   │  Auth0   │
│(16379) │   │(Supabase)│   │ (11434)  │   │   JWT    │
└────────┘   └──────────┘   └──────────┘   └──────────┘
```

## Microservices

### 1. AI Service (Port 8001)

**Purpose**: Intelligent code analysis and security recommendations using AI models

**Key Features**:

- AI-powered code analysis and vulnerability detection
- Security best practices recommendations
- Integration with Ollama for local LLM inference
- Caching layer for performance optimization

**Technology Stack**:

- FAST API for REST API
- Claude 3 Opus, Groq (Llama 3), GPT-4, and Ollama integration
- Redis for caching
- Prometheus metrics on port 9101

**Key Endpoints**:

- `POST /api/ai/analyze` - Analyze code for security issues
- `POST /api/ai/chat` - Interactive AI assistance
- `GET /api/ai/suggestions` - Get security recommendations

---

### 2. GitHub Service (Port 8002)

**Purpose**: GitHub integration for repository management and workflow automation

**Key Features**:

- GitHub repository analysis and metrics
- Organization and team management
- Pull request automation
- Workflow file parsing and validation
- Repository tree management with intelligent caching

**Technology Stack**:

- FastAPI with async/await patterns
- GitHub API v3/v4 integration
- Redis caching for API rate limiting
- Background task processing
- Prometheus metrics on port 9102

**Key Endpoints**:

- `GET /api/github/organizations` - List user organizations
- `GET /api/github/repositories` - Repository listing with filters
- `GET /api/github/workspace/{org_name}` - Workspace analysis
- `POST /api/github/create-pr` - Automated PR creation

**Performance**: Handles 700+ requests with optimized caching and rate limiting

---

### 3. Threat Modeling Service (Port 8003)

**Purpose**: Automated threat modeling and security risk assessment

**Key Features**:

- STRIDE, CIA, and LINDDUN threat analysis
- Attack surface mapping
- Risk scoring and prioritization
- Threat mitigation recommendations
- Integration with OWASP threat libraries and MITRE ATT&CK mapping

**Technology Stack**:

- FastAPI
- SQLAlchemy for threat model storage
- AI integration for intelligent threat detection
- Prometheus metrics on port 9103

**Key Endpoints**:

- `POST /api/threats/analyze` - Analyze system for threats
- `GET /api/threats/models` - List threat models
- `GET /api/threats/risks` - Risk assessment results

---

### 4. Workspace Intelligence Service (Port 8004)

**Purpose**: Deep workspace analysis and insights generation

**Key Features**:

- Repository structure analysis
- Dependency mapping and vulnerability scanning
- Code quality metrics
- Security posture assessment
- Technology stack detection

**Technology Stack**:

- FastAPI
- File system analysis engines
- Dependency parsers (npm, pip, maven, etc.)
- Prometheus metrics on port 9104

**Key Endpoints**:

- `POST /api/workspace/analyze` - Full workspace analysis
- `GET /api/workspace/insights` - Get workspace insights
- `GET /api/workspace/dependencies` - Dependency tree

---

### 5. Collaboration Service (Port 8105)

**Purpose**: Team collaboration and real-time communication

**Key Features**:

- Real-time messaging
- Team workspace sharing
- Collaborative threat modeling sessions
- Activity tracking and notifications

**Technology Stack**:

- FastAPI
- WebSocket for real-time communication
- Redis pub/sub for message broadcasting
- Prometheus metrics on port 9105

**Key Endpoints**:

- `WS /api/collab/ws` - WebSocket connection
- `GET /api/collab/teams` - Team management
- `POST /api/collab/share` - Share workspace

---

### 6. Auth Service (Port 8006)

**Purpose**: Centralized authentication and authorization

**Key Features**:

- Auth0 JWT token validation
- User session management
- Role-based access control (RBAC)
- API key management for service-to-service auth

**Technology Stack**:

- FastAPI
- Auth0 integration
- JWT (RS256) validation
- Prometheus metrics on port 9106

**Key Endpoints**:

- `POST /api/auth/validate` - Validate JWT tokens
- `GET /api/auth/user` - Get authenticated user info
- `POST /api/auth/refresh` - Refresh access token

**Security**:

- Auth0 domain: `dev-sabxychpf6paj41u.us.auth0.com`
- RS256 algorithm for JWT signing
- Token expiration and refresh handling

---

### 7. Workflow Orchestration Service (Port 8007)

**Purpose**: CI/CD workflow management and security scan orchestration

**Key Features**:

- GitHub Actions workflow analysis
- Security scan orchestration (Gitleaks, TruffleHog)
- Workflow optimization recommendations
- CI/CD pipeline security checks

**Technology Stack**:

- FastAPI
- YAML parsing for workflow files
- Integration with security scanning tools
- Prometheus metrics on port 9107

**Key Endpoints**:

- `POST /api/workflow/analyze` - Analyze workflow files
- `POST /api/workflow/scan` - Trigger security scans
- `GET /api/workflow/results` - Get scan results

---

### 8. AI RAG Service (Port 9108)

**Purpose**: Conversational AI for DevSecOps intelligence using Retrieval-Augmented Generation

**Key Features**:
- Natural language queries about security best practices
- Context-aware responses using vectorized knowledge base
- Auto-indexing of documents and analysis results
- Persistent conversation history

**Technology Stack**:
- FastAPI
- Qdrant for vector storage
- Ollama for embeddings
- Redis for caching

---

### 9. Events Hub (Backend - Port 9100)

**Purpose**: Central event bus and WebSocket manager for real-time notifications

**Key Features**:
- Redis pub/sub event bus
- WebSocket connection management
- Real-time event broadcasting to clients
- Service-to-service event coordination
- Event routing and filtering

**Technology Stack**:
- FastAPI with WebSocket support
- Redis for pub/sub messaging
- Async event processing
- Prometheus metrics on port 9100

**Event Types**:
- `threat.analysis.completed` - Threat analysis finished
- `threat_detected` - New security threat identified
- `pr_created` - Pull request created
- `scan_complete` - Security scan finished

---

## Infrastructure Components

### Kong API Gateway (Port 8000)

**Purpose**: Unified API entry point and request routing

**Features**:

- Declarative configuration via YAML
- Route-based service discovery
- Request/response transformation
- Rate limiting and throttling
- CORS handling

**Configuration**: `infra/kong/kong.yml`

---

### Prometheus (Port 9090)

**Purpose**: Metrics collection and time-series database

**Features**:

- Scraping all services every 15 seconds
- Custom metrics: request rate, latency, errors
- PromQL query language
- Data retention and aggregation

**Metrics Collected**:

- `http_requests_total` - Total HTTP requests by endpoint, method, status
- `http_request_duration_seconds` - Request latency histograms
- `process_resident_memory_bytes` - Memory usage
- `process_start_time_seconds` - Service uptime

**Configuration**: `infra/monitoring/prometheus.yml`

---

### Grafana (Port 3000)

**Purpose**: Metrics visualization and dashboarding

**Features**:

- Auto-provisioned dashboards for all services
- Real-time monitoring with 5-second refresh
- Custom panels: request rate, latency, errors, memory
- Alert visualization

**Dashboards**:

- Backend Events Hub
- AI Service
- GitHub Service
- Threat Modeling Service
- Workspace Intelligence Service
- Auth Service
- Collaboration Service
- Workflow Orchestration Service

**Access**: `http://localhost:3000`

---

### Jaeger (Port 16686)

**Purpose**: Distributed tracing and request flow visualization

**Features**:

- OpenTelemetry integration
- Trace collection via OTLP HTTP (port 4318)
- Service dependency mapping
- Latency analysis across services

**Technology**:

- OTLP HTTP exporter from all services
- Trace context propagation via HTTP headers

---

### Loki (Port 3100)

**Purpose**: Centralized log aggregation

**Features**:

- Log collection from all containers
- Label-based log filtering
- Integration with Grafana
- Log retention policies

---

### Redis (Port 16379)

**Purpose**: Event bus and caching layer

**Features**:

- Pub/sub for event-driven architecture
- Caching for API responses and rate limiting
- Session storage
- Message queue for async tasks

**Internal Port**: 6379

---

### PostgreSQL (Supabase)

**Purpose**: Primary database for structured data

**Features**:

- User data and profiles
- Threat models and analysis results
- Workspace metadata
- API usage tracking

**Connection**: `aws-0-ap-south-1.pooler.supabase.com:5432`

---

### Ollama (Port 11434)

**Purpose**: Local LLM inference for AI features

**Features**:

- Local model hosting
- Privacy-preserving AI analysis
- Custom model support
- GPU acceleration

---

## Technology Stack

### Backend Services

- **Framework**: FastAPI (Python 3.11)
- **ASGI Server**: Uvicorn with auto-reload
- **Database ORM**: SQLAlchemy
- **Authentication**: Auth0 JWT (RS256)
- **HTTP Client**: httpx for async requests

### Communication

- **API Gateway**: Kong 3.0
- **Event Bus**: Redis pub/sub
- **WebSocket**: FastAPI WebSocket support
- **Service Discovery**: Docker Compose DNS

### Observability

- **Metrics**: Prometheus + Grafana
- **Tracing**: Jaeger + OpenTelemetry
- **Logging**: Loki + Promtail
- **Instrumentation**: prometheus-client, opentelemetry-sdk

### Infrastructure

- **Containerization**: Docker + Docker Compose
- **Base Image**: python:3.11-slim
- **Networking**: Docker bridge networks
- **Volumes**: Named volumes for persistence

### Frontend

- **Framework**: Svelte/SvelteKit
- **Build Tool**: Vite
- **Deployment**: Vercel-ready configuration

---

## Communication Patterns

### Synchronous (REST API)

```
Client → Kong Gateway → Service → Database/Cache
```

**Use Cases**:

- CRUD operations
- Real-time queries
- Authentication/authorization

### Asynchronous (Event-Driven)

```
Service A → Redis Pub → Redis Sub → Service B
           ↓
    Events Hub → WebSocket → Client
```

**Use Cases**:

- Notifications (analysis complete, threat detected)
- Long-running operations (workspace analysis)
- Multi-service workflows (PR creation after analysis)

### Real-Time (WebSocket)

```
Client ←→ Events Hub (Backend) ←→ Redis Pub/Sub
```

**Use Cases**:

- Live dashboard updates
- Real-time collaboration
- Progress tracking for long operations

---

## Security Architecture

### Authentication Flow

```
1. User logs in via Auth0
2. Client receives JWT token
3. Client includes token in Authorization header
4. Kong validates token or forwards to Auth Service
5. Service validates JWT signature and claims
6. Request processed if authorized
```

### Service-to-Service Authentication

- Currently: Trusted internal network
- **Planned**: API keys or mutual TLS for production

### Data Security

- JWT tokens with RS256 signing
- Environment variable secrets
- PostgreSQL connection encryption
- HTTPS for production (Kong SSL termination)

---

## Deployment

### Development (Current)

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f [service-name]

# Rebuild after code changes
docker compose up -d --build [service-name]
```

### Production (Planned)

- Kubernetes orchestration
- Horizontal pod autoscaling
- Service mesh (Istio/Linkerd)
- External secrets management (Vault)
- Cloud-native databases (RDS, Cloud SQL)

---

## Monitoring & Observability

### Metrics (Prometheus)

All services expose `/metrics` endpoint with:

- Request count and rate
- Response time histograms (p50, p95, p99)
- Error rates by status code
- Memory and CPU usage
- Custom business metrics

### Dashboards (Grafana)

Each service has dedicated dashboard showing:

- Request rate graphs
- Latency percentiles
- Error rate tracking
- Memory usage
- Service uptime
- Top endpoints by traffic

### Tracing (Jaeger)

Distributed traces show:

- Request flow across services
- Service dependencies
- Latency breakdown
- Error propagation

### Logging (Loki)

Centralized logs with:

- Structured JSON logging
- Service/container labels
- Error tracking
- Request correlation IDs

---

## Performance Characteristics

### GitHub Service

- **Throughput**: 700+ requests handled
- **Memory**: ~124 MiB under load
- **Uptime**: 1.36+ hours continuous operation
- **Caching**: Redis-backed for GitHub API rate limiting

### AI Service

- **Model**: Ollama with local LLM
- **Response Time**: Varies by model size
- **Concurrency**: Async request handling
- **Optimization**: Response caching for repeated queries

### Events Hub (Backend)

- **WebSocket Connections**: Multi-client support
- **Event Throughput**: Redis pub/sub scalability
- **Metrics Path**: `/metrics/` with GZip compression disabled

---

## Shared Libraries

### withops-common (Planned Integration)

Located at: `shared/withops-common/`

**Purpose**: Common utilities and models across services

**Planned Components**:

- Shared data models (User, Organization, Repository)
- Common middleware (logging, error handling)
- Utility functions (date parsing, validation)
- API clients for inter-service communication

**Status**: Created but not yet integrated into services

---

## Future Enhancements

### Priority 1: Code Deduplication

- Integrate `withops-common` library across all services
- Remove duplicate `security.py` files
- Centralize JWT validation through Auth Service
- Shared middleware and error handlers

### Priority 2: Service Mesh

- Implement service-to-service authentication
- Add mutual TLS for internal communication
- API key management for service accounts

### Priority 3: Advanced Monitoring

- Prometheus alert rules (service down, high error rate, high latency)
- Alertmanager with Slack/email notifications
- SLA/SLO tracking dashboards
- Unified overview dashboard

### Priority 4: Testing

- Integration tests for each service
- Contract testing between services
- End-to-end tests through Kong gateway
- Load testing and performance benchmarking

### Priority 5: Resilience

- Circuit breaker pattern
- Retry logic with exponential backoff
- Bulkhead isolation
- Graceful degradation

---

## API Documentation

Each service exposes interactive API documentation:

- **Swagger UI**: `http://localhost:[port]/docs`
- **ReDoc**: `http://localhost:[port]/redoc`
- **OpenAPI Schema**: `http://localhost:[port]/openapi.json`

### Service URLs (Development)

- AI Service: http://localhost:8001/docs
- GitHub Service: http://localhost:8002/docs
- Threat Modeling: http://localhost:8003/docs
- Workspace Intelligence: http://localhost:8004/docs
- Collaboration: http://localhost:8105/docs
- Auth Service: http://localhost:8006/docs
- Workflow Orchestration: http://localhost:8007/docs
- Events Hub: http://localhost:8000/docs

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Auth0 account and credentials
- GitHub personal access token
- Supabase account and database

### Environment Setup

```bash
# Clone repository
git clone https://github.com/NimanthaSupun/WithOps.git
cd WithOps

# Configure environment variables
# Set AUTH0_DOMAIN, AUTH0_AUDIENCE, GITHUB_TOKEN, etc.

# Start infrastructure
docker compose up -d redis postgres prometheus grafana

# Start services
docker compose up -d

# Verify services
docker compose ps

# Access Grafana
open http://localhost:3000
```

### Accessing Services

- **API Gateway**: http://localhost:8000
- **Grafana Dashboards**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Jaeger UI**: http://localhost:16686
- **Individual Services**: http://localhost:800[1-7]

---

## Development Guidelines

### Adding a New Service

1. Create service directory under `services/`
2. Add `Dockerfile` with python:3.11-slim base
3. Implement FastAPI app with `/health` endpoint
4. Add Prometheus metrics middleware
5. Configure OpenTelemetry tracing
6. Update `docker-compose.yml` with service definition
7. Add Prometheus scrape config
8. Create Grafana dashboard JSON
9. Update Kong routes in `infra/kong/kong.yml`
10. Document API endpoints

### Code Standards

- Python 3.11+ with type hints
- FastAPI for all HTTP APIs
- Async/await for I/O operations
- Structured logging with correlation IDs
- Comprehensive error handling
- Environment-based configuration

### Observability Requirements

- Expose `/metrics` endpoint (Prometheus format)
- Add `/health` and `/ready` endpoints
- Implement OpenTelemetry tracing
- Use structured JSON logging
- Include request correlation IDs

---

## Maintenance

### Monitoring Health

```bash
# Check all service status
docker compose ps

# View service logs
docker compose logs -f [service-name]

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify metrics
curl http://localhost:900[1-7]/metrics
```

### Troubleshooting

- **Service not starting**: Check logs with `docker compose logs`
- **Metrics not showing**: Verify Prometheus scrape config and service `/metrics` endpoint
- **Dashboard empty**: Ensure Grafana has restarted after adding dashboard JSON
- **Auth failures**: Verify Auth0 credentials and JWT token validity
- **High latency**: Check Jaeger traces for bottlenecks

---

## Contributing

When contributing to the microservices:

1. Follow existing service patterns
2. Add comprehensive tests
3. Update API documentation
4. Add Prometheus metrics for new endpoints
5. Create/update Grafana dashboards
6. Document configuration changes
7. Test with Docker Compose locally

---

## License

[Your License Here]

---

## Contact & Support

- **Repository**: https://github.com/NimanthaSupun/WithOps
- **Issues**: GitHub Issues
- **Documentation**: This file and `/docs`

---

**Last Updated**: November 27, 2025
docker exec withops-ollama ollama pull nomic-embed-text
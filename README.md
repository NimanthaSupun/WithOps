# WithOps DevSecOps Platform

**Everything After Code** — Intelligent AI-driven security automation for modern development teams.

WithOps is an enterprise-grade DevSecOps platform that automates security analysis, threat modeling, CI/CD governance, and workspace intelligence across GitHub organizations. Built with production-ready architecture, comprehensive monitoring, and event-driven microservices.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
  - [Local Development](#local-development)
  - [Docker Compose (Production)](#docker-compose-production)
  - [Kubernetes](#kubernetes)
- [Configuration](#configuration)
- [Microservices](#microservices)
- [Monitoring & Observability](#monitoring--observability)
- [Development](#development)
- [Contributing](#contributing)

---

## Overview

WithOps provides DevOps and security teams with actionable intelligence across their GitHub organizations. The platform integrates AI-powered analysis, automated threat modeling, CI/CD governance audits, and real-time collaboration features into a unified dashboard.

### Target Users

- **DevOps Engineers** — Automate security compliance and CI/CD governance
- **Architecture Engineers** — Assess DevSecOps maturity and identify improvement areas
- **Security Teams** — Detect threats, vulnerabilities, and misconfigurations
- **Development Leads** — Ensure code quality and security best practices

### Core Capabilities

- **Threat Modeling Canvas** — AI-powered DFD analysis with STRIDE/LINDDUN/CIA threat detection
- **Workspace Intelligence** — OWASP DSOMM maturity framework assessment (L0-L4)
- **Action Audit** — GitHub Actions governance with automated upgrade PRs
- **AI-Powered Code Analysis** — Vulnerability detection and security recommendations
- **Real-Time Monitoring** — WebSocket-powered event feed with instant notifications
- **Collaborative Sessions** — Multi-user threat modeling with Liveblocks

---

## Architecture

WithOps uses a distributed microservices architecture with event-driven communication, centralized API gateway routing, and comprehensive observability.

### System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         Clients (Frontend)                      │
│                    SvelteKit + Auth0 (5173)                    │
└──────────────────────────────────────────────────────────────┬─┘
                                                                 │
                          ┌─────────────────────────────┐
                          │   Kong API Gateway (9000)   │
                          │  • Route requests           │
                          │  • CORS handling            │
                          │  • Rate limiting            │
                          └──────────────┬──────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         │                              │                              │
    ┌────▼────────┐            ┌────────▼────────┐          ┌─────────▼────────┐
    │ Microservices│            │  Events Hub     │          │ External Services │
    │   (8 total)  │            │   (WebSocket)   │          │                  │
    │              │◄───────────┤  • Event Bus    │          │ • GitHub API     │
    │ • AI Service │    Events  │  • Broadcasts   │          │ • Auth0 JWT      │
    │ • GitHub Svc │            │  • Broadcasting │          │ • Claude/Ollama  │
    │ • Threat Mdl │            │                 │          │ • Groq/GPT-4     │
    │ • Workspace  │            └─────────────────┘          └──────────────────┘
    │ • Collab     │                   ▲
    │ • Workflow   │                   │
    │ • RAG        │          ┌────────┴────────┐
    │ • Pipeline   │          │  Redis Pub/Sub   │
    └──────────────┘          │  (Event Channel) │
         │                    └──────────────────┘
         │
    ┌────┴────────────────────────────────────┐
    │                                         │
┌───▼──────┐              ┌────────────┐  ┌──▼─────────┐
│ PostgreSQL│              │ Redis Cache│  │ Qdrant VDB │
│(Supabase) │              │  (16379)   │  │ (Embeddings)
│ • Users   │              │            │  │            │
│ • Orgs    │              │ • Sessions │  │ • Knowledge│
│ • Models  │              │ • Workflows│  │ • Vectors  │
│ • Scans   │              │ • Settings │  └────────────┘
└───────────┘              └────────────┘

    ┌───────────────────────────────────────────────┐
    │        Monitoring & Observability Stack        │
    │ • Prometheus (metrics)  • Grafana (dashboards) │
    │ • Jaeger (tracing)      • OpenTelemetry        │
    └───────────────────────────────────────────────┘
```

### Communication Flow

1. **REST API Calls** — Frontend → Kong Gateway → Microservice
2. **Async Events** — Microservice → Redis pub/sub → Events Hub → WebSocket → Frontend
3. **Database** — All services use shared PostgreSQL (Supabase) for persistence
4. **Caching** — Redis layer for performance optimization and rate limiting
5. **Monitoring** — OpenTelemetry/Prometheus metrics to Grafana, traces to Jaeger

---

## Technology Stack

### Frontend

| Component        | Technology          |
| ---------------- | ------------------- |
| Framework        | SvelteKit (Vite)    |
| Styling          | Tailwind CSS        |
| Visualization    | Three.js, D3.js     |
| Real-Time Collab | Liveblocks          |
| Authentication   | Auth0 (JWT)         |
| Testing          | Vitest + Playwright |
| Node Version     | 20.x LTS            |

**Package.json Dependencies:**

- `@auth0/auth0-spa-js` — Auth0 integration
- `@liveblocks/react` — Collaborative features
- `d3`, `three` — Data visualization
- `svelte`, `vite` — Build tools

### Backend & Microservices

| Component  | Technology                                 |
| ---------- | ------------------------------------------ |
| Framework  | FastAPI (Python 3.11+)                     |
| Web Server | Uvicorn (async ASGI)                       |
| Async      | asyncio, asyncpg, aiohttp                  |
| Database   | PostgreSQL (via Supabase)                  |
| ORM        | SQLAlchemy 2.0                             |
| Cache      | Redis (async)                              |
| AI Models  | Claude 3 Opus, GPT-4, Groq Llama 3, Ollama |
| Vector DB  | Qdrant (embeddings/RAG)                    |
| Monitoring | Prometheus, OpenTelemetry                  |
| Job Queue  | Background workers                         |

**Key Dependencies:**

- `fastapi==0.104.1`, `uvicorn[standard]`
- `sqlalchemy==2.0.23`, `asyncpg==0.29.0`
- `redis[asyncio]==5.0.1`
- `httpx[http2]==0.25.0` — GitHub API calls
- `python-jose[cryptography]` — JWT validation
- `opentelemetry-*` — Distributed tracing
- `prometheus-client` — Metrics export

### Infrastructure

| Component  | Role                                  |
| ---------- | ------------------------------------- |
| Kong       | API Gateway, routing, CORS            |
| Redis      | Cache, pub/sub event bus (port 16379) |
| PostgreSQL | Data persistence (Supabase managed)   |
| Ollama     | Local LLM inference (port 11434)      |
| Qdrant     | Vector database (port 6333-6334)      |
| Prometheus | Metrics collection (port 9091)        |
| Grafana    | Metrics dashboards (port 3001)        |
| Jaeger     | Distributed tracing (port 16686)      |
| Docker     | Containerization                      |
| Kubernetes | Orchestration (production)            |

### DevOps & CI/CD

| Tool                      | Purpose                            |
| ------------------------- | ---------------------------------- |
| Docker                    | Container images for all services  |
| Docker Compose            | Local development orchestration    |
| Kubernetes                | Production orchestration (1.24+)   |
| GitHub Actions            | CI/CD pipeline (test, build, scan) |
| GitHub Container Registry | Docker image registry              |
| Gitleaks                  | Secret scanning in CI              |
| Ruff                      | Python linting (all services)      |
| Prometheus                | Metrics scraping                   |
| OpenTelemetry             | Instrumentation standard           |
| OTLP                      | Trace export to Jaeger             |

---

## Key Features

### 1. Threat Modeling Canvas

Collaborate in real-time to design Data Flow Diagrams (DFDs) with AI-powered threat analysis.

- **Visual Design** — Draw DFD components (processes, data stores, external entities, trust boundaries)
- **AI Analysis** — Automatic threat detection using STRIDE, LINDDUN, or CIA frameworks
- **Real-Time Collab** — Multiple users on same model with cursor tracking (Liveblocks)
- **Export** — Save threat models as JSON or diagrams
- **Audit Trail** — Session recording for compliance

**Endpoint:** `POST /api/threat-modeling/models`

### 2. Workspace Intelligence Dashboard

Assess organization-wide DevSecOps maturity using OWASP DSOMM framework.

- **Maturity Scoring** — 0-100 scale across 5 dimensions (Build, Implementation, Test, Info Gathering, Culture)
- **Tool Detection** — Identify CodeQL, SonarQube, Dependabot, Gitleaks, SAST/DAST tools
- **Practice Assessment** — Detect security practices (secret scanning, dependency checks, SAST)
- **AI Chat** — Ask why scores are low and get improvement recommendations
- **Benchmarking** — Compare against industry standards

**Endpoint:** `POST /api/workspace-intelligence/analyze`

### 3. Action Audit (GitHub Actions Governance)

Audit all GitHub Actions across repositories and auto-upgrade outdated versions.

- **Crawl Workflows** — Scan `.github/workflows/*.yml` files organization-wide
- **Version Tracking** — List all actions with versions (e.g., `actions/checkout@v2.4.1`)
- **Status Classification** — Up-to-Date, Outdated, Upgrade Recommended, Major Upgrade Needed
- **Auto-Fix via PR** — Generate PRs to upgrade actions to latest versions
- **Audit Reports** — Track which actions need attention

**Endpoint:** `GET /api/workflows/analyze`, `POST /api/workflows/security/create-upgrade-prs`

### 4. AI-Powered Code Analysis

Analyze repositories for vulnerabilities and security misconfigurations.

- **Vulnerability Detection** — Identify common OWASP Top 10, secrets, insecure dependencies
- **PR Description Generation** — Auto-generate security-focused PR descriptions
- **Recommendations** — Best practices based on code patterns
- **Model Selection** — Claude 3 Opus, GPT-4, Groq Llama 3, or Ollama
- **Caching** — Optimized for performance with Redis

**Endpoint:** `POST /api/ai/analyze`, `POST /api/ai/chat`

### 5. Real-Time Monitoring

Live event feed with instant notifications for threats, scans, and activities.

- **WebSocket Events** — Push-based updates (not polling)
- **Event Types** — `threat.analysis.completed`, `threat_detected`, `pr_created`, `scan_complete`
- **Multi-User** — All connected clients receive updates instantly
- **Activity Streams** — Per-organization activity tracking

**Endpoint:** `WebSocket /ws/events/{user_id}`

### 6. Collaborative Threat Sessions

Multiple team members work on threat models simultaneously.

- **Cursor Tracking** — See other users' cursor positions in real-time
- **Shape Editing** — Collaborative DFD creation with conflict resolution
- **Comments** — Threaded discussions on specific threats
- **Mitigations** — Assign and track mitigation tasks
- **History** — Maintain session recording for audit compliance

**Technology:** Liveblocks real-time collaboration

---

## Prerequisites

### System Requirements

- **OS** — Windows 10+, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Docker** — 20.10+ (with Docker Compose 2.0+)
- **Kubernetes** — 1.24+ (for production deployments)
- **Memory** — 8GB minimum (16GB recommended)
- **Disk** — 20GB available space

### Required Accounts & Credentials

1. **GitHub**
   - GitHub App (or OAuth application)
   - Organization access for installing the app
   - GitHub Container Registry (GHCR) access

2. **Auth0**
   - Auth0 account (https://auth0.com)
   - Configured API and SPA application
   - Domain, Client ID, Client Secret

3. **LLM Services** (at least one)
   - **Anthropic** — Claude 3 API key (recommended)
   - **OpenAI** — GPT-4 API key (optional)
   - **Groq** — Groq API key (optional)
   - **Ollama** — Local inference (included in docker-compose)

4. **Cloud Database** (recommended for production)
   - **Supabase** — PostgreSQL + Auth service
   - Alternatively: Self-hosted PostgreSQL

### Environment Configuration

Create `.env` files before deployment:

```bash
# backend/.env (local development)
GITHUB_APP_ID=YOUR_GITHUB_APP_ID
GITHUB_APP_CLIENT_ID=YOUR_CLIENT_ID
GITHUB_APP_CLIENT_SECRET=YOUR_CLIENT_SECRET
GITHUB_PRIVATE_KEY_PATH=/app/config/keys/withops-devsecops-platform-local.2026-01-22.private-key.pem

AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.withops.com

SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

REDIS_URL=redis://localhost:16379
OLLAMA_URL=http://localhost:11434
QDRANT_URL=http://localhost:6333

FRONTEND_URL=http://localhost:5173
ENVIRONMENT=local
```

See `/doc/CONFIGURATION-STATUS.md` and `/k8s/SECRETS_MANAGEMENT.md` for complete configuration details.

---

## Quick Start

### Option A: Docker Compose (Recommended for Development)

Start the entire stack locally in ~30 seconds:

```bash
# Clone and navigate to project
cd d:\project\dev-testing\DevSecOps

# Start all services (Kong, Redis, Ollama, PostgreSQL via Supabase, all microservices)
docker-compose up --build

# Frontend will be available at: http://localhost:5173
# Kong Gateway at: http://localhost:9000
# Prometheus at: http://localhost:9091
# Grafana at: http://localhost:3001
# Jaeger at: http://localhost:16686
```

### Option B: Manual Microservices (Development with Hot-Reload)

Start backend services individually for faster iteration:

```powershell
# 1. Start infrastructure services
docker-compose up -d kong redis ollama

# 2. Start Python backend (requires Python 3.11+)
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Start microservices (in separate terminals)
cd services/ai-service
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

cd services/github-service
uvicorn main:app --host 0.0.0.0 --port 8002 --reload

# 4. Start frontend (in another terminal)
cd frontend
npm install
npm run dev    # Vite dev server with hot-reload
```

### Option C: Kubernetes (Production)

Deploy to a Kubernetes cluster:

```bash
# 1. Build production images
.\k8s\BUILD-PRODUCTION-IMAGES.ps1

# 2. Create namespace and secrets
kubectl create namespace withops
kubectl create secret generic app-secrets -n withops \
  --from-literal=SUPABASE_ANON_KEY='YOUR_KEY' \
  --from-literal=ANTHROPIC_API_KEY='sk-ant-YOUR_KEY'

# 3. Deploy manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/

# 4. Verify deployment
kubectl get pods -n withops
kubectl logs -n withops -f deployment/backend

# 5. Access via port-forward (or configure Ingress)
kubectl port-forward -n withops svc/kong 8000:8000
```

---

## Deployment

### Local Development

**File:** `docker-compose.yml`

Starts all services with local environment variables:

```bash
docker-compose up --build
docker-compose down -v        # Clean up volumes
docker-compose logs -f        # View logs
```

**Environment:** Uses `backend/.env` and `services/github-service/.env`

**Ports:**

- Frontend: 5173
- Kong Gateway: 9000
- Microservices: 8001-8009
- Redis: 16379
- Ollama: 11434
- Qdrant: 6333, 6334
- Prometheus: 9091
- Grafana: 3001
- Jaeger: 16686

### Docker Compose (Production)

**File:** `docker-compose.yml` with `--env-file` flag

Deploys with production environment variables:

```bash
# Method 1: Use .env.production (Recommended)
docker-compose --env-file backend/.env.production up -d --build

# Method 2: Copy production config temporarily
Copy-Item backend\.env.production backend\.env -Force
docker-compose up -d --build
```

**Environment:** Uses `backend/.env.production` and `services/github-service/.env.production`

**Key Differences from Local:**

- Production Auth0 credentials
- Production GitHub App configuration
- Production Supabase database
- Production URLs (app.withops.com, api.withops.com)
- HTTPS enabled (via reverse proxy/load balancer)

### Kubernetes (Production-Grade)

**Files:** `k8s/*.yaml` manifests

Kubernetes deployment with proper scaling, health checks, and observability.

#### Prerequisites

```bash
kubectl cluster-info
kubectl get nodes
```

#### Deployment Steps

```bash
# 1. Create namespace
kubectl create namespace withops

# 2. Create secrets (CRITICAL before deploying)
kubectl create secret generic app-secrets -n withops \
  --from-literal=SUPABASE_ANON_KEY='YOUR_KEY' \
  --from-literal=SUPABASE_SERVICE_ROLE_KEY='YOUR_KEY' \
  --from-literal=SUPABASE_DATABASE_URL='postgresql://...' \
  --from-literal=ANTHROPIC_API_KEY='sk-ant-...' \
  --from-literal=GITHUB_APP_ID='YOUR_ID' \
  --from-literal=GITHUB_APP_CLIENT_SECRET='YOUR_SECRET'

# 3. Verify secrets
kubectl get secrets -n withops

# 4. Deploy services
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/kong-gateway.yaml
kubectl apply -f k8s/backend-events-hub.yaml
kubectl apply -f k8s/github-service.yaml
kubectl apply -f k8s/ai-service.yaml
# ... deploy remaining services

# 5. Verify deployment
kubectl get pods -n withops
kubectl get svc -n withops

# 6. Check logs
kubectl logs -n withops -f deployment/backend

# 7. Access application
# Configure DNS for app.withops.com → Load Balancer IP
# Or use port-forward for testing:
kubectl port-forward -n withops svc/kong 8000:8000
```

#### Kubernetes Features

- **Deployments** — One per service with replicasets for scaling
- **Services** — ClusterIP for inter-service communication, NodePort/LoadBalancer for external access
- **ConfigMaps** — Kong routing rules, Prometheus scrape config
- **Secrets** — Encrypted secret management for credentials
- **RBAC** — Role-based access control for pod permissions
- **Probes** — Liveness and readiness checks for health monitoring
- **Resource Limits** — CPU and memory requests/limits per service
- **StatefulSets** — Redis, PostgreSQL persistence (if not using managed services)

**See:** `/k8s/PRODUCTION-DEPLOYMENT.md` and `/k8s/SECRETS_MANAGEMENT.md` for detailed K8s deployment guide.

---

## Configuration

### Environment Variables

#### Core Configuration

| Variable       | Purpose                | Local                   | Production                |
| -------------- | ---------------------- | ----------------------- | ------------------------- |
| `ENVIRONMENT`  | Deployment environment | `local`                 | `production`              |
| `FRONTEND_URL` | Frontend origin        | `http://localhost:5173` | `https://app.withops.com` |
| `BACKEND_URL`  | Backend API            | `http://localhost:8000` | `https://api.withops.com` |
| `CORS_ORIGINS` | Allowed CORS origins   | `http://localhost:5173` | `https://app.withops.com` |

#### Database

| Variable                    | Purpose                         |
| --------------------------- | ------------------------------- |
| `SUPABASE_URL`              | Supabase project URL            |
| `SUPABASE_ANON_KEY`         | Public anon key (frontend)      |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (backend)      |
| `DATABASE_URL`              | PostgreSQL connection string    |
| `DATABASE_ENCRYPTION_KEY`   | Field-level encryption (base64) |

#### GitHub Integration

| Variable                     | Purpose                                 |
| ---------------------------- | --------------------------------------- |
| `GITHUB_APP_ID`              | GitHub App ID (from app settings)       |
| `GITHUB_APP_CLIENT_ID`       | GitHub App Client ID                    |
| `GITHUB_APP_CLIENT_SECRET`   | GitHub App Client Secret (confidential) |
| `GITHUB_PRIVATE_KEY_PATH`    | Path to private key PEM file            |
| `GITHUB_OAUTH_CLIENT_ID`     | OAuth app Client ID (for discovery)     |
| `GITHUB_OAUTH_CLIENT_SECRET` | OAuth app Client Secret                 |

#### Authentication (Auth0)

| Variable              | Purpose                         |
| --------------------- | ------------------------------- |
| `AUTH0_DOMAIN`        | Auth0 tenant domain             |
| `AUTH0_API_AUDIENCE`  | Auth0 API identifier            |
| `AUTH0_CLIENT_ID`     | Auth0 application Client ID     |
| `AUTH0_CLIENT_SECRET` | Auth0 application Client Secret |
| `JWT_SECRET_KEY`      | Fallback JWT secret (optional)  |

#### AI/LLM Services

| Variable            | Purpose                     |
| ------------------- | --------------------------- |
| `ANTHROPIC_API_KEY` | Claude API key              |
| `OPENAI_API_KEY`    | OpenAI GPT-4 key (optional) |
| `GROQ_API_KEY`      | Groq Llama 3 key (optional) |
| `OLLAMA_URL`        | Local Ollama endpoint       |
| `QDRANT_URL`        | Qdrant vector database URL  |

#### Infrastructure

| Variable         | Purpose                                         |
| ---------------- | ----------------------------------------------- |
| `REDIS_URL`      | Redis connection string                         |
| `REDIS_PASSWORD` | Redis auth password (if enabled)                |
| `ENABLE_METRICS` | Enable Prometheus metrics export                |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing                    |
| `OTLP_ENDPOINT`  | Jaeger OTLP HTTP endpoint                       |
| `LOG_LEVEL`      | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

### File Locations

```
backend/
├── .env                    # Local dev configuration
├── .env.production         # Production configuration
├── config/
│   └── keys/
│       ├── withops-devsecops-platform-local.2026-01-22.private-key.pem
│       └── withops-devsecops-platform-production.private-key.pem

services/github-service/
├── .env                    # Local dev
├── .env.production         # Production

frontend/
├── .env                    # Vite environment
├── vite.config.js          # Build configuration
└── src/lib/config.js       # Runtime config utilities

infra/
├── kong/kong.yml           # API Gateway routing
├── monitoring/
│   ├── prometheus.yml      # Metrics scrape config
│   └── grafana/dashboards/ # Grafana dashboard definitions
└── ollama/
    └── init-models.sh      # Ollama model initialization

k8s/
├── namespace.yaml          # Kubernetes namespace
├── redis.yaml              # Redis deployment
├── kong-gateway.yaml       # Kong deployment
├── backend-events-hub.yaml # Backend deployment
├── secrets.yaml            # Secret template
└── *.yaml                  # Other microservice deployments
```

### Dynamic URL Configuration

The platform supports environment-based dynamic URLs:

**Frontend Vite Build:**

```javascript
// Build-time variables (vite.config.js)
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=http://localhost:9100
VITE_AUTH0_DOMAIN=dev-sabxychpf6paj41u.us.auth0.com
VITE_AUTH0_CLIENT_ID=YOUR_CLIENT_ID
VITE_AUTH0_CALLBACK_URL=http://localhost:5173/callback
```

**Backend Runtime:**

```python
# Runtime configuration (backend/core/config.py)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
GITHUB_SERVICE_URL = os.getenv('GITHUB_SERVICE_URL', 'http://localhost:8002')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
```

---

## Microservices

WithOps comprises 9+ independent microservices, each with specific domain responsibilities:

### 1. Backend Events Hub (Port 8000)

**Purpose:** Central WebSocket manager and real-time event coordinator

**Key Features:**

- WebSocket connection management
- Redis pub/sub subscription
- Event broadcasting to connected clients
- Channel-based routing for multi-user sessions

**Event Types:**

- `threat.analysis.completed` — Threat analysis finished
- `threat_detected` — New threat identified
- `pr_created` — Pull request automatically created
- `scan_complete` — Security scan finished
- `github.refresh` — GitHub data refreshed

**Endpoints:**

- `WebSocket /ws/events/{user_id}` — Real-time event stream
- `GET /api/health` — Health check

**Monitoring:** Prometheus on port 9100

---

### 2. AI Service (Port 8001)

**Purpose:** AI-powered code analysis and security recommendations

**Key Features:**

- Code vulnerability analysis
- Security best practices recommendations
- Integration with Claude 3 Opus, GPT-4, Groq Llama 3, Ollama
- Background worker for async threat analysis
- Response caching with Redis

**Endpoints:**

- `POST /api/ai/analyze` — Analyze code for security issues
- `POST /api/ai/chat` — Interactive AI assistance
- `GET /api/ai/suggestions` — Security recommendations
- `POST /api/ai/analyze-async` — Async analysis with event callback

**Technology:** FastAPI, httpx (async HTTP), Redis cache

**Monitoring:** Prometheus on port 9101

**Models:**

```python
# Model selection priority
1. Claude 3 Opus (via Anthropic API) — Primary
2. Groq Llama 3 (via Groq API) — Fallback
3. GPT-4 (via OpenAI API) — Alternative
4. Ollama (Local) — Offline capability
```

---

### 3. GitHub Service (Port 8002)

**Purpose:** GitHub integration for repository management and workflow automation

**Key Features:**

- GitHub App and OAuth integration
- Organization and repository discovery
- Workflow file parsing and validation
- Repository tree management with intelligent caching
- GitHub Actions version tracking and audit
- Automated PR creation for action upgrades

**Endpoints:**

- `GET /api/github/organizations` — List user orgs
- `GET /api/github/repositories` — Repository listing
- `GET /api/github/workspace/{org}` — Workspace analysis
- `GET /api/github/workflows` — Workflow listing
- `POST /api/github/create-pr` — Create PR for upgrades
- `GET /api/github/actions-audit` — Action version audit

**Technology:** FastAPI, httpx with connection pooling, GitHub App auth

**Cache Strategy:** Redis with 1-2 hour TTLs for workspace/workflow data

**Rate Limiting:** Token bucket via Redis

**Monitoring:** Prometheus on port 9102

---

### 4. Threat Modeling Service (Port 8003)

**Purpose:** STRIDE/LINDDUN/CIA security threat analysis engine

**Key Features:**

- Automated threat generation from DFDs
- STRIDE methodology (default)
- LINDDUN methodology (privacy-focused)
- CIA framework (confidentiality/integrity/availability)
- OWASP Top 10 mapping
- MITRE ATT&CK framework integration
- Threat severity scoring

**Endpoints:**

- `POST /api/v1/models` — Create threat model
- `GET /api/v1/models/{id}` — Retrieve model
- `POST /api/v1/models/{id}/analyze` — Generate threats
- `POST /api/v1/models/{id}/comprehensive-analysis` — Deep analysis
- `GET /api/v1/models/{id}/threats` — List identified threats

**Technology:** FastAPI, threat analysis algorithms, knowledge base

**Monitoring:** Prometheus on port 9103

---

### 5. Workspace Intelligence Service (Port 8004)

**Purpose:** Organization-wide DevSecOps maturity assessment

**Key Features:**

- OWASP DSOMM framework assessment
- 5 dimensions analysis: Build, Implementation, Test, Info Gathering, Culture
- Maturity levels: L0-L4 (None → Basic → Advanced → Mature → Optimized)
- Security tool detection (CodeQL, SonarQube, Dependabot, Gitleaks, etc.)
- AI chat for insights and recommendations
- Practice detection: SAST, SCA, DAST, secret scanning
- Benchmarking against industry standards

**Endpoints:**

- `POST /api/workspace-intelligence/analyze` — Analyze workspace
- `GET /api/workspace-intelligence/{org_id}/assessment` — Get assessment
- `POST /api/workspace-intelligence/{org_id}/chat` — AI chat for insights
- `GET /api/workspace-intelligence/{org_id}/practices` — List detected practices

**Technology:** FastAPI, maturity assessment algorithms, knowledge base

**Monitoring:** Prometheus on port 9104

---

### 6. Collaboration Service (Port 8105)

**Purpose:** Team collaboration and workspace sharing

**Key Features:**

- Organization member management
- Collaboration invites and permissions
- Activity tracking
- Workspace sharing and access control
- Real-time notifications for collaborators

**Endpoints:**

- `GET /api/collaboration/teams` — List teams
- `POST /api/collaboration/share` — Share workspace
- `GET /api/collaboration/{org_id}/members` — List members
- `POST /api/collaboration/invite` — Send invite

**Technology:** FastAPI, PostgreSQL relationships

**Monitoring:** Prometheus on port 9105

---

### 7. Workflow Orchestration Service (Port 8007)

**Purpose:** CI/CD workflow management and security scan orchestration

**Key Features:**

- GitHub Actions version management
- Workflow analysis and audit
- Automated action upgrade PR creation
- Security scan orchestration
- Workflow health checks

**Endpoints:**

- `GET /api/workflows/analyze` — Analyze workflows
- `POST /api/workflows/scan` — Scan for issues
- `POST /api/workflows/security/create-upgrade-prs` — Create upgrade PRs
- `GET /api/workflows/{org}/actions-audit` — Action version audit

**Technology:** FastAPI, GitHub API integration

**Monitoring:** Prometheus on port 9107

---

### 8. AI RAG Service (Port 8008)

**Purpose:** Conversational AI with Retrieval-Augmented Generation

**Key Features:**

- Natural language queries about DevSecOps best practices
- Context-aware responses from knowledge base
- Automatic document indexing and embedding
- Multi-turn conversations with memory
- Knowledge base from Qdrant vector store

**Endpoints:**

- `POST /api/conversations/start` — Start conversation
- `POST /api/conversations/{id}/message` — Send message
- `GET /api/conversations/{id}` — Get conversation
- `POST /api/rag/index` — Index documents
- `POST /api/rag/query` — Query knowledge base

**Technology:** FastAPI, Qdrant, Ollama embeddings, Redis for session management

**Monitoring:** Prometheus on port 9108

---

### 9. Pipeline Prediction Service (Port 8009)

**Purpose:** ML-based CI/CD failure prediction and anomaly detection

**Key Features:**

- Historical pipeline data analysis
- Failure forecasting for workflows
- Anomaly detection in pipeline patterns
- Performance trend analysis
- Recommendations for improvement

**Endpoints:**

- `POST /api/pipeline-prediction/analyze` — Predict failures
- `GET /api/pipeline-prediction/{org_id}/trends` — Pipeline trends
- `POST /api/pipeline-prediction/train` — Train model

**Technology:** FastAPI, ML models (scikit-learn or TensorFlow)

**Monitoring:** Prometheus on port 9109

---

### Service Communication

**REST API:**

- Frontend ↔ Kong Gateway ↔ Microservices
- Service-to-service calls via Kong for consistency

**Async Events:**

- Microservices publish to Redis channels
- Events Hub subscribes and broadcasts via WebSocket
- Example: AI Service publishes `threat.analysis.completed` → Events Hub → Frontend

**Authentication:**

- Auth0 JWT validation middleware on all services
- Centralized JWT verification in `core/auth.py`
- Service-to-service calls use internal tokens

---

## Monitoring & Observability

WithOps includes production-grade monitoring, observability, and distributed tracing.

### Metrics (Prometheus)

**Collection:** Prometheus scrapes metrics on port 9091

**Service Metrics:**

```
http_requests_total{service="backend", endpoint="/api/threat-modeling", status="200"}
http_request_duration_seconds{service="github-service", endpoint="/api/github/organizations"}
websocket_connections_active{service="events-hub", user_count=42}
redis_commands_total{service="cache", command="get", status="hit"}
database_queries_total{service="backend", query_type="select"}
ai_analysis_duration_seconds{service="ai-service", model="claude-3-opus"}
```

**Retention:** 15 days (configurable in `infra/monitoring/prometheus.yml`)

### Dashboards (Grafana)

**Access:** http://localhost:3001 (default admin/admin)

**Pre-built Dashboards:**

1. **System Overview** — Request rates, latency, errors, uptime
2. **Service Health** — Per-service metrics and availability
3. **Database Performance** — Query counts, connection pool, slowest queries
4. **Cache Efficiency** — Hit rates, evictions, memory usage
5. **AI Service Analysis** — Model usage, analysis duration, success rates
6. **GitHub Integration** — API rate limits, workflow analysis, PR creation rates

**See:** `infra/monitoring/grafana/dashboards/` directory

### Distributed Tracing (Jaeger)

**Access:** http://localhost:16686

**Traces:** OpenTelemetry exports to Jaeger via OTLP HTTP

**Instrumentation:**

- FastAPI middleware
- Database queries
- Redis operations
- HTTP client calls
- WebSocket connections

**Trace Flow Example:**

```
HTTP POST /api/threat-modeling/analyze
├── [FastAPI] Request received
│   └── [Auth] JWT validation
├── [Service] Threat analysis logic
│   ├── [Database] Query threat model
│   ├── [AI Service] Call Claude API
│   └── [Redis] Cache result
├── [EventBus] Publish analysis.completed
│   └── [Jaeger] Export span
└── HTTP 200 OK
```

**View Trace:** Jaeger UI with timeline, span details, logs, and error messages

### Structured Logging

**Format:** JSON (for ELK Stack or Loki integration)

```json
{
  "timestamp": "2026-01-15T10:23:45.123Z",
  "level": "INFO",
  "service": "github-service",
  "request_id": "abc-123-def",
  "user_id": "user_12345",
  "message": "Fetched 42 repositories for organization github",
  "duration_ms": 234,
  "status": "success"
}
```

**Log Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL

**See:** `backend/core/logging_config.py`

### Health Checks

**Liveness Probe** — Service is running

```bash
GET /api/health
GET /api/health/live
```

**Readiness Probe** — Service is ready to accept traffic

```bash
GET /api/health/ready
```

**Full Health Check** — All dependencies

```bash
GET /api/health/full
# Checks: database, redis, external APIs
```

---

## Development

### Local Development Setup

#### Prerequisites

- Python 3.11+
- Node.js 20.x LTS
- Docker & Docker Compose
- Git

#### Initial Setup

```bash
# Clone repository
git clone https://github.com/your-org/withops.git
cd withops

# Copy environment files
cp backend/.env.example backend/.env
cp services/github-service/.env.example services/github-service/.env
cp frontend/.env.example frontend/.env

# Start infrastructure
docker-compose up -d kong redis ollama
```

#### Backend Development

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest

# Lint with Ruff
ruff check .
```

#### Frontend Development

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start dev server with hot-reload
npm run dev
# Open http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Lint & format
npm run lint
npm run format
```

#### Adding a New Microservice

```bash
# 1. Create service directory
mkdir -p services/my-service
cd services/my-service

# 2. Copy template structure
# Copy main.py, requirements.txt, Dockerfile from existing service

# 3. Create main.py with FastAPI app
# app = FastAPI()
# @app.get("/health")
# async def health(): return {"status": "ok"}

# 4. Add to docker-compose.yml
# my-service:
#   build: ./services/my-service
#   ports:
#     - "8010:8000"

# 5. Add Kong routing (infra/kong/kong.yml)

# 6. Add Kubernetes deployment (k8s/my-service.yaml)
```

### Project Structure

```
withops/
├── backend/                    # Events Hub + core utilities
│   ├── main.py                 # WebSocket server & event coordinator
│   ├── core/                   # Shared utilities
│   │   ├── event_bus.py        # Redis pub/sub manager
│   │   ├── websocket_manager.py # WebSocket connections
│   │   ├── auth.py             # JWT validation
│   │   ├── github_client.py    # GitHub integration
│   │   └── ai_helper.py        # AI model selection
│   ├── database/               # ORM models & queries
│   ├── config/keys/            # GitHub App private keys
│   └── requirements.txt
│
├── services/                   # 9+ microservices
│   ├── ai-service/
│   │   ├── main.py             # FastAPI app
│   │   ├── api/                # Route handlers
│   │   ├── core/               # Service logic
│   │   └── Dockerfile
│   ├── github-service/         # GitHub integration
│   ├── threat-modeling-service/
│   ├── workspace-intelligence-service/
│   ├── ai-rag-service/
│   ├── collaboration-service/
│   ├── workflow-orchestration-service/
│   ├── auth-service/
│   └── pipeline-prediction-service/
│
├── frontend/                   # SvelteKit application
│   ├── src/
│   │   ├── routes/             # Pages (SvelteKit routing)
│   │   │   ├── dashboard/
│   │   │   ├── github/
│   │   │   └── [org]/          # Dynamic routes
│   │   ├── lib/                # Shared components & utilities
│   │   │   ├── auth.js         # Auth0 setup
│   │   │   ├── api/            # API client functions
│   │   │   └── stores/         # Svelte stores (state management)
│   │   └── app.html            # Root template
│   ├── package.json
│   └── Dockerfile
│
├── infra/                      # Infrastructure configs
│   ├── kong/
│   │   └── kong.yml            # API Gateway routing rules
│   ├── monitoring/
│   │   ├── prometheus.yml      # Metrics scrape config
│   │   └── grafana/
│   │       └── dashboards/     # Dashboard JSON definitions
│   └── ollama/
│       └── init-models.sh      # Model initialization
│
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml
│   ├── redis.yaml
│   ├── kong-gateway.yaml
│   ├── backend-events-hub.yaml
│   ├── *-service.yaml          # Microservice deployments
│   ├── monitoring.yaml         # Prometheus & Grafana
│   ├── secrets.yaml            # Secret template
│   ├── PRODUCTION-DEPLOYMENT.md
│   └── SECRETS_MANAGEMENT.md
│
├── doc/                        # Documentation
│   ├── MICROSERVICES-ARCHITECTURE.md
│   ├── CONFIGURATION-STATUS.md
│   ├── DEPLOYMENT-CHECKLIST.txt
│   ├── QUICK-START-CHECKLIST.md
│   └── TEST-VALIDATION-GUIDE.md
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml           # GitHub Actions pipeline
│
├── docker-compose.yml          # Local development
├── docker-compose.prod.yml     # Production overrides
├── ruff.toml                   # Python linting config
└── README.md                   # This file
```

### Code Standards

**Python (Backend & Services)**

- Python 3.11+ with type hints
- PEP 8 style guide (enforced by Ruff)
- Async/await for I/O-bound operations
- SQLAlchemy for ORM queries
- FastAPI for HTTP endpoints

**Configuration:**

```toml
# ruff.toml (project root)
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "N", "UP"]  # Error, Flake8, Warning, Import, Naming, Upgrade
ignore = ["E501"]  # Line too long (handled by formatter)
```

**JavaScript/SvelteKit (Frontend)**

- Node.js 20+ with strict mode
- ES6+ modules
- Prettier formatting
- ESLint for code quality
- Vitest for unit tests

**Configuration:**

```javascript
// eslint.config.js
export default [
  {
    languageOptions: { globals: { browser: true, node: true } },
    rules: { "no-unused-vars": "error" },
  },
];
```

### Testing

**Backend (Python)**

```bash
# Unit tests
pytest

# With coverage
pytest --cov=services/ai-service tests/

# Specific test
pytest tests/test_ai_analysis.py::test_threat_detection
```

**Frontend (JavaScript)**

```bash
# Unit tests (Vitest)
npm test

# Watch mode
npm test -- --watch

# With coverage
npm test -- --coverage

# Browser tests (Playwright)
npm test -- --browser
```

**Integration Tests**

```bash
# Start full stack
docker-compose up -d

# Run integration suite
./test-validation.ps1 -Mode full -Org test-org

# Clean up
docker-compose down
```

### CI/CD Pipeline

**GitHub Actions:** `.github/workflows/ci-cd.yml`

**Stages:**

1. **Secret Scanning** (Gitleaks)
   - Scans full git history for leaked credentials
   - Fails build if secrets detected

2. **Frontend CI** (Node 20)
   - Install dependencies (`npm ci`)
   - Lint with Prettier + ESLint
   - Run Vitest unit tests
   - Install Playwright browsers

3. **Backend CI** (Python 3.11)
   - 10 services in parallel matrix
   - Install dependencies
   - Lint with Ruff
   - (Optional: Unit tests)

4. **Build & Push** (Docker)
   - Requires all CI stages to pass
   - Build all images with matrix
   - Tag with `sha-<short-sha>` and `latest`
   - Push to GitHub Container Registry (GHCR)

**Matrix Services:**

```yaml
- backend
- ai-service
- ai-rag-service
- auth-service
- collaboration-service
- github-service
- threat-modeling-service
- workflow-orchestration-service
- workspace-intelligence-service
- pipeline-prediction-service
```

**On Success:**

- Images pushed to `ghcr.io/your-org/withops/{service}:latest`
- Images ready for Kubernetes deployment

---

## Contributing

### Before You Start

1. Read [doc/MICROSERVICES-ARCHITECTURE.md](doc/MICROSERVICES-ARCHITECTURE.md)
2. Understand the event-driven architecture
3. Review existing service patterns
4. Check open issues for known limitations

### Workflow

1. **Create a branch**

   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make changes** following code standards
   - Lint before committing: `ruff check .` (backend), `npm run lint` (frontend)
   - Write tests for new logic
   - Update documentation

3. **Commit with clear messages**

   ```bash
   git commit -m "feat: Add threat severity scoring"
   ```

4. **Push and create Pull Request**

   ```bash
   git push origin feature/new-feature
   ```

5. **CI/CD Pipeline Runs**
   - Secret scan
   - Lint & tests
   - Docker build
   - Image push to GHCR

6. **Code Review** — Team reviews and approves
7. **Merge** — Squash commits to main

### Adding a New API Endpoint

**Backend Example:**

```python
# services/ai-service/api/v1/ai.py
from fastapi import APIRouter, Depends
from core.auth import verify_token

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.post("/analyze-code")
async def analyze_code(
    code: str,
    user_id: str = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Analyze code for vulnerabilities."""
    # Implementation
    return {"vulnerabilities": [...]}
```

**Frontend Example:**

```svelte
<!-- frontend/src/routes/analyze/+page.svelte -->
<script>
  import { onMount } from 'svelte';
  import { getApiBaseUrl } from '$lib/config';

  let results = [];
  let loading = false;

  async function analyzeCode() {
    loading = true;
    const response = await fetch(`${getApiBaseUrl()}/api/ai/analyze-code`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ code })
    });
    results = await response.json();
    loading = false;
  }
</script>

<button on:click={analyzeCode} disabled={loading}>
  {loading ? 'Analyzing...' : 'Analyze'}
</button>
```

### Adding a New Microservice

1. Copy service template directory
2. Update `main.py` with FastAPI app
3. Add `Dockerfile`
4. Add to `docker-compose.yml`
5. Add Kong routing in `infra/kong/kong.yml`
6. Add Kubernetes manifest in `k8s/`
7. Add to GitHub Actions matrix in `.github/workflows/ci-cd.yml`
8. Document endpoints in [doc/MICROSERVICES-ARCHITECTURE.md](doc/MICROSERVICES-ARCHITECTURE.md)

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs -f <service-name>

# Verify network connectivity
docker network ls
docker network inspect withops_default

# Restart from scratch
docker-compose down -v
docker-compose up --build
```

### Database Connection Issues

```bash
# Check Supabase credentials
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check PostgreSQL from container
docker-compose exec backend psql $DATABASE_URL -c "SELECT 1"
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return "PONG"

# Check Redis URL
echo $REDIS_URL
```

### Auth0 Configuration

1. Go to https://manage.auth0.com
2. Applications → Your App → Settings
3. Add to **Allowed Callback URLs**:
   - `http://localhost:5173/callback` (dev)
   - `https://app.withops.com/callback` (prod)
4. Click **Save Changes**

### GitHub App Configuration

1. Go to https://github.com/settings/apps
2. Edit your GitHub App
3. Update **Webhook URL** and **Callback URL**
4. Regenerate **Client Secret** if needed
5. Download new **Private Key** if expired

### Secret Scanning Failures

```bash
# Check for hardcoded secrets
git log -S "sk-ant" --oneline
git log -p -S "YOUR_SECRET"

# Use gitleaks locally
gitleaks detect --source . --verbose
```

---

## Support & Resources

### Documentation

- [Microservices Architecture](doc/MICROSERVICES-ARCHITECTURE.md) — Service specifications
- [Kubernetes Deployment](k8s/PRODUCTION-DEPLOYMENT.md) — K8s setup guide
- [Secrets Management](k8s/SECRETS_MANAGEMENT.md) — Secret best practices
- [Configuration Status](doc/CONFIGURATION-STATUS.md) — Environment setup status
- [Deployment Checklist](doc/DEPLOYMENT-CHECKLIST.txt) — Production deployment steps

### External References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SvelteKit Guide](https://kit.svelte.dev/)
- [Kong API Gateway](https://konghq.com/kong/)
- [PostgreSQL / Supabase](https://supabase.com/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [OpenTelemetry](https://opentelemetry.io/)

### Getting Help

1. Check documentation in `/doc` directory
2. Review existing GitHub issues
3. Consult `.github/workflows/ci-cd.yml` for CI/CD examples
4. Review service examples in `/services` for patterns

---

## License

This project is proprietary. Unauthorized use, distribution, or modification is prohibited.

---

## Version

**WithOps DevSecOps Platform v2.0**

- **Release Date:** January 2026
- **Status:** Production-Ready
- **Python Version:** 3.11+
- **Node Version:** 20.x LTS
- **Kubernetes:** 1.24+

---

## Summary

WithOps is a comprehensive, production-grade DevSecOps platform designed for enterprises. With 9+ microservices, enterprise-grade monitoring, Kubernetes support, and AI-powered security analysis, it provides teams with intelligent automation for DevSecOps maturity assessment, threat modeling, and CI/CD governance.

Built with industry-standard technologies (FastAPI, SvelteKit, PostgreSQL, Redis, Kubernetes), the platform scales to support large organizations while maintaining security, observability, and ease of deployment.

**Key Strengths:**

- ✅ Event-driven microservices architecture
- ✅ Comprehensive monitoring and observability
- ✅ Production-ready Kubernetes deployment
- ✅ AI-powered security recommendations
- ✅ Real-time collaboration features
- ✅ Enterprise authentication (Auth0)
- ✅ Multiple LLM integration
- ✅ Automated CI/CD governance

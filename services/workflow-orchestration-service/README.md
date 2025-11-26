# Workflow Orchestration Service

A dedicated microservice for managing workflow trees, execution orchestration, and security scanning in the DevSecOps platform.

## 🎯 Purpose

This service handles:

- **Workflow Tree Management** - User-customized workflow organization and persistence
- **Workflow Execution** - Orchestration and monitoring of workflow runs
- **Security Scanning** - Workflow-level, repository-level, and organization-level security analysis
- **Visual Canvas** - Workflow design and relationship mapping
- **Analytics** - Workflow performance metrics and execution history

## 📁 Project Structure

```
workflow-orchestration-service/
├── main.py                    # FastAPI application entry point
├── Dockerfile                 # Container configuration
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── api/
│   └── routes/               # API route handlers (to be implemented)
│       ├── workflow_tree.py
│       ├── workflow_execution.py
│       ├── security_scanning.py
│       └── canvas.py
├── core/                     # Business logic (to be implemented)
│   ├── workflow_parser.py
│   ├── execution_engine.py
│   ├── security_scanner.py
│   └── stream_manager.py
└── database/                 # Data layer
    ├── config.py            # Database connection management
    ├── models.py            # SQLAlchemy models
    └── operations.py        # CRUD operations
```

## 🗄️ Database Schema

Uses PostgreSQL with `workflow_orchestration` schema:

### Tables

1. **workflow_trees** - User-customized workflow organization

   - Stores tree structure as JSON
   - Tracks node counts (workflows, folders, files)
   - Version control for tree updates

2. **workflow_executions** - Execution history

   - Detailed step-by-step execution data
   - GitHub Actions integration
   - Parameters, inputs, and results
   - Performance metrics (duration, status)

3. **workflow_security_scans** - Security scan results

   - Risk scoring and categorization
   - Finding details and recommendations
   - Tracks secrets, unsafe actions, permissions, injection risks

4. **workflow_canvas_designs** - Visual workflow designs

   - Canvas data and relationships
   - Version control
   - User collaboration tracking

5. **workflow_metrics** - Analytics and performance
   - Success rates and averages
   - Execution statistics
   - Performance trends

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL (Supabase)
- Redis (for caching and pub/sub)

### Environment Setup

1. Copy `.env.example` to `.env`
2. Configure database connection:
   ```
   DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```
3. Set service URLs:
   ```
   GITHUB_SERVICE_URL=http://github-service:8002
   AUTH_SERVICE_URL=http://auth-service:8001
   ```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py
```

Service will be available at `http://localhost:8007`

### Docker Deployment

```bash
# Build image
docker build -t workflow-orchestration-service .

# Run container
docker run -p 8007:8007 --env-file .env workflow-orchestration-service
```

## 📊 API Endpoints (Planned)

### Workflow Tree Management

- `GET /api/project-tree/{org_name}` - Load workflow tree
- `POST /api/project-tree/{org_name}` - Save workflow tree

### Workflow Execution

- `POST /api/workflows/{workflow_id}/trigger` - Execute workflow
- `GET /api/workflows/{workflow_id}/history` - Get execution history
- `GET /api/workflows/{workflow_id}/stream` - Real-time execution stream (SSE)

### Security Scanning

- `POST /api/workflows/{workflow_id}/security/scan` - Scan workflow
- `POST /api/repositories/{repo_name}/security/scan` - Scan repository
- `POST /api/organizations/{org_name}/security/scan` - Scan organization
- `GET /api/security/overview` - Security dashboard

### Canvas/Visual Editor

- `POST /api/canvas/save-workflow` - Save canvas design
- `GET /api/canvas/workflow-relationships` - Get dependency graph
- `GET /api/canvas/predefined-actions` - Get GitHub Actions library

### Monitoring

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## 🔧 Integration

### Calls to Other Services

- **GitHub Service** - Get workflows, trigger executions, fetch content
- **Auth Service** - Verify user permissions, organization access
- **AI Service** (optional) - Generate descriptions, security recommendations

### Called By

- **Backend/Gateway** - All treeview operations from frontend
- **Frontend** - Direct SSE/WebSocket connections for real-time updates

## 📈 Monitoring

- **Prometheus Metrics**: Available at `/metrics`
- **OpenTelemetry Tracing**: Integrated with Jaeger
- **Health Check**: `/health` endpoint

## 🛠️ Development Status

**Phase 1 Complete:**

- ✅ Service structure created
- ✅ Database models defined
- ✅ Database operations implemented
- ✅ Basic FastAPI setup with monitoring

**Next Steps:**

- ⏳ Implement API routes
- ⏳ Build workflow parser
- ⏳ Implement execution engine
- ⏳ Create security scanner
- ⏳ Add real-time streaming (SSE/WebSocket)

## 📝 License

Part of the DevSecOps platform - WithOps

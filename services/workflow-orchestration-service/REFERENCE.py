"""
WORKFLOW ORCHESTRATION SERVICE - QUICK REFERENCE
=================================================

SERVICE INFORMATION
-------------------
Name: Workflow Orchestration Service
Port: 8007 (internal), 8107 (external via Docker)
Gateway: http://localhost:8000 (via Kong)
Direct: http://localhost:8107
Docs: http://localhost:8107/docs
Metrics: http://localhost:8107/metrics

SETUP & DEPLOYMENT
------------------
1. Initialize database:
   python init_db.py init

2. Start service (Docker):
   docker-compose up -d workflow-orchestration-service

3. Start service (Local):
   python main.py

4. View logs:
   docker-compose logs -f workflow-orchestration-service

5. Run tests:
   pytest test_service.py -v

6. Test basic functionality:
   python test_service.py

7. Run examples:
   python example_usage.py


API ENDPOINTS
-------------

PROJECT TREE MANAGEMENT
  GET    /api/project-tree/{org_name}
  POST   /api/project-tree/{org_name}
  DELETE /api/project-tree/{org_name}

WORKFLOW EXECUTION
  POST   /api/workflows/{org_name}/{repo_name}/{workflow_id}/trigger
  GET    /api/workflows/{org_name}/{repo_name}/{workflow_id}/history
  GET    /api/workflows/{execution_id}/status
  GET    /api/workflows/{execution_id}/stream  (SSE)
  POST   /api/workflows/{execution_id}/cancel
  GET    /api/workflows/{org_name}/{repo_name}/{workflow_id}/content
  GET    /api/workflows/{org_name}/{repo_name}/{workflow_id}/parameters

SECURITY SCANNING
  POST   /api/security/scan/workflow
  POST   /api/security/scan/repository/{org_name}/{repo_name}
  POST   /api/security/scan/organization/{org_name}
  GET    /api/security/scans/{org_name}
  GET    /api/security/scans/{scan_id}/details
  GET    /api/security/overview/{org_name}

CANVAS DESIGN
  POST   /api/canvas/save-workflow
  GET    /api/canvas/{org_name}/{repo_name}
  GET    /api/canvas/workflow-relationships/{org_name}/{repo_name}
  GET    /api/canvas/predefined-actions
  DELETE /api/canvas/{org_name}/{repo_name}


CORE COMPONENTS
---------------
1. WorkflowParser (core/workflow_parser.py)
   - Parse GitHub Actions YAML
   - Extract triggers, jobs, steps
   - Detect secrets and dependencies

2. ExecutionEngine (core/execution_engine.py)
   - Trigger workflows via GitHub Service
   - Poll execution status
   - Track run history

3. SecurityScanner (core/security_scanner.py)
   - Scan for hardcoded secrets
   - Detect unsafe actions
   - Check permissions
   - Identify injection risks
   - Calculate risk scores

4. StreamManager (core/stream_manager.py)
   - SSE streaming for real-time updates
   - WebSocket support
   - Connection management


DATABASE SCHEMA
---------------
Schema: workflow_orchestration

Tables:
- workflow_trees: Project tree structures
- workflow_executions: Execution history
- workflow_security_scans: Security scan results
- workflow_canvas_designs: Visual workflow designs
- workflow_metrics: Performance analytics


DEPENDENCIES
------------
External Services:
- GitHub Service (http://github-service:8002) - GitHub API operations
- Auth Service (http://auth-service:8006) - Authentication
- AI Service (http://ai-service:8001) - Optional AI features
- Redis (redis:6379) - Caching and pub/sub
- Supabase PostgreSQL - Database

Infrastructure:
- Kong Gateway (8000) - API routing
- Prometheus (9090) - Metrics collection
- Jaeger (16686) - Distributed tracing


ENVIRONMENT VARIABLES
---------------------
SERVICE_PORT=8007
SERVICE_NAME=workflow-orchestration-service
SERVICE_VERSION=1.0.0

DATABASE_URL=postgresql://...
REDIS_URL=redis://redis:6379

GITHUB_SERVICE_URL=http://github-service:8002
AUTH_SERVICE_URL=http://auth-service:8006
AI_SERVICE_URL=http://ai-service:8001

ENABLE_METRICS=true
ENABLE_TRACING=true
ENABLE_SECURITY_SCANNING=true
ENABLE_SSE=true
ENABLE_WEBSOCKET=true

OTLP_ENDPOINT=http://jaeger:4318/v1/traces


MONITORING
----------
Health Check: GET /health
Metrics: GET /metrics (Prometheus format)
OpenTelemetry traces sent to Jaeger

Prometheus Scrape Config:
  job_name: workflow-orchestration-service
  targets: [workflow-orchestration-service:8007]
  metrics_path: /metrics


SECURITY SCAN RISK LEVELS
--------------------------
Critical (75-100): Immediate action required
High (50-74): Fix soon
Medium (25-49): Review and improve
Low (10-24): Minor concerns
Minimal (0-9): Secure


COMMON ISSUES & SOLUTIONS
--------------------------
1. Service won't start
   - Check DATABASE_URL is set
   - Verify PostgreSQL is accessible
   - Run: python init_db.py verify

2. Database errors
   - Initialize schema: python init_db.py init
   - Check Supabase connection
   - Verify schema exists

3. Connection refused
   - Ensure service is running
   - Check port 8107 is available
   - Verify Docker networking

4. SSE stream not working
   - Check ENABLE_SSE=true
   - Verify execution_id exists
   - Test with: curl -N http://localhost:8107/api/workflows/{id}/stream


EXAMPLE USAGE
-------------
See example_usage.py for complete examples

Quick test:
  curl http://localhost:8107/health
  curl http://localhost:8107/metrics
  curl http://localhost:8107/api/canvas/predefined-actions

Scan workflow:
  curl -X POST http://localhost:8107/api/security/scan/workflow \
    -H "Content-Type: application/json" \
    -H "X-User-Id: test-user" \
    -d '{"workflow_content": "...", "workflow_name": "test.yml"}'


DEVELOPMENT
-----------
Run locally:
  1. Set environment variables in .env
  2. python main.py
  3. Access http://localhost:8007

Hot reload enabled with uvicorn --reload

Database migrations:
  - Models in database/models.py
  - Run init_db.py to apply changes


ARCHITECTURE
------------
Microservice extracting CI/CD workflow orchestration from monolith
Autonomous service with own database schema, caching, and monitoring
Communicates with GitHub Service for GitHub API operations
Provides real-time execution monitoring via SSE/WebSocket
Comprehensive security scanning with risk scoring
Visual workflow design and relationship management


FILE STRUCTURE
--------------
workflow-orchestration-service/
├── main.py                 - FastAPI application
├── Dockerfile             - Container definition
├── requirements.txt       - Python dependencies
├── .env.example          - Environment template
├── init_db.py            - Database initialization
├── test_service.py       - Integration tests
├── example_usage.py      - Usage examples
├── START.sh              - Quick start script
├── api/
│   └── routes/
│       ├── workflow_tree.py
│       ├── workflow_execution.py
│       ├── security_scanning.py
│       └── canvas.py
├── core/
│   ├── workflow_parser.py
│   ├── execution_engine.py
│   ├── security_scanner.py
│   └── stream_manager.py
└── database/
    ├── models.py
    ├── config.py
    └── operations.py
"""

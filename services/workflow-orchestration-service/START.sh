# Workflow Orchestration Service - Quick Start

# Build and start the service
docker-compose up -d workflow-orchestration-service

# View logs
docker-compose logs -f workflow-orchestration-service

# Check health
# curl http://localhost:8107/health

# Access API docs
# http://localhost:8107/docs

# Stop service
# docker-compose stop workflow-orchestration-service

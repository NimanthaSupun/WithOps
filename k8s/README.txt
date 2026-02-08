===========================================
WithOps Kubernetes Production Deployment
===========================================

OVERVIEW
--------
Deploy the WithOps DevSecOps Platform to Kubernetes for production.
For local development, use Docker Compose instead (simpler and faster).

PREREQUISITES
-------------
✅ Kubernetes cluster running (local or cloud)
✅ kubectl installed and configured
✅ Docker installed for building images
✅ Domain names configured (app.withops.com, api.withops.com)

QUICK START
-----------

1. Build Production Images:
   > .\BUILD-PRODUCTION-IMAGES.ps1

2. Deploy to Kubernetes:
   > kubectl apply -f namespace.yaml
   > kubectl apply -f redis.yaml
   > kubectl apply -f qdrant.yaml
   > kubectl apply -f ollama.yaml
   > kubectl apply -f monitoring.yaml
   > kubectl apply -f backend-events-hub.yaml
   > kubectl apply -f auth-service.yaml
   > kubectl apply -f github-service.yaml
   > kubectl apply -f ai-service.yaml
   > kubectl apply -f threat-modeling-service.yaml
   > kubectl apply -f collaboration-service.yaml
   > kubectl apply -f workspace-intelligence-service.yaml
   > kubectl apply -f workflow-orchestration-service.yaml
   > kubectl apply -f ai-rag-service.yaml
   > kubectl apply -f frontend.yaml
   > kubectl apply -f kong-gateway.yaml

   Or deploy all at once:
   > kubectl apply -f .

3. Check Status:
   > kubectl get pods -n withops
   > kubectl get svc -n withops

SERVICES DEPLOYED
-----------------
✅ Frontend - SvelteKit app at app.withops.com
✅ Backend - FastAPI Events Hub (WebSocket + Event Bus)
✅ Auth Service - Authentication and authorization
✅ Redis - Caching and session storage
✅ Qdrant - Vector database for RAG (AI embeddings)
✅ Ollama - Embedding model 'nomic-embed-text' (768d)
✅ GitHub Service - GitHub integration microservice
✅ AI Service - Claude API integration for AI/ML
✅ Threat Modeling Service - Security threat analysis
✅ Collaboration Service - Team collaboration and invites
✅ Workspace Intelligence Service - Workspace analysis and maturity scoring
✅ Workflow Orchestration Service - CI/CD workflow management
✅ AI RAG Service - Conversational AI with RAG
✅ Kong Gateway - API routing and CORS
✅ Redis - Caching and Pub/Sub
✅ Prometheus + Grafana - Monitoring

ARCHITECTURE
------------
Frontend (app.withops.com)
    ↓
Kong Gateway (api.withops.com)
    ├→ /api/auth/* → Auth Service (8006)
    ├→ /api/github/* → GitHub Service (8002)
    ├→ /api/ai/* → AI Service (8001)
    ├→ /api/threat-modeling/* → Threat Modeling Service (8003)
    ├→ /api/collaboration/* → Collaboration Service (8105)
    ├→ /api/workspace-intelligence/* → Workspace Intelligence Service (8004)
    ├→ /api/repository-tree/* → Workspace Intelligence Service (8004)
    ├→ /api/workflows/* → Workflow Orchestration Service (8007)
    ├→ /api/project-tree/* → Workflow Orchestration Service (8007)
    ├→ /api/canvas/* → Workflow Orchestration Service (8007)
    ├→ /api/security/* → Workflow Orchestration Service (8007)
    ├→ /api/rag/* → AI RAG Service (8008)
    └→ /api/conversations/* → AI RAG Service (8008)

Backend (9100) → WebSocket /ws/{user_id} for real-time events

USEFUL COMMANDS
---------------

View logs:
> kubectl logs -f deployment/backend -n withops
> kubectl logs -f deployment/frontend -n withops

Port forward for testing:
> kubectl port-forward svc/frontend 3000:5173 -n withops
> kubectl port-forward svc/kong 8000:9000 -n withops

Scale services:
> kubectl scale deployment/github-service --replicas=3 -n withops

Delete all:
> kubectl delete namespace withops

CHECK HEALTH
------------
> kubectl get pods -n withops
> kubectl top pods -n withops
> kubectl describe pod <pod-name> -n withops

TROUBLESHOOTING
---------------
If pods not starting:
> kubectl describe pod <pod-name> -n withops
> kubectl logs <pod-name> -n withops

If connection issues:
> kubectl get endpoints -n withops
> kubectl exec -it <pod-name> -n withops -- /bin/sh

DOCUMENTATION
-------------
For detailed deployment guide, see:
→ PRODUCTION-DEPLOYMENT.md
- Production-ready
- Better resource management
- Built-in service discovery

MONITORING
----------
After deployment:
1. Grafana: http://localhost:3001 (admin/admin)
2. Jaeger: http://localhost:16686
3. Prometheus: kubectl port-forward svc/prometheus 9090:9090 -n withops

NEXT STEPS
----------
1. Add remaining services (threat-modeling, workspace-intelligence, etc.)
2. Configure persistent storage for databases
3. Set up ingress for external access
4. Configure SSL/TLS certificates
5. Set up CI/CD for automatic deployments
6. Deploy to cloud (AWS EKS, Azure AKS, Google GKE)

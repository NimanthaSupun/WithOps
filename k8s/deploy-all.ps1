# Complete deployment script for all WithOps microservices

Write-Host "🚀 Building and Deploying ALL WithOps Services to Kubernetes..." -ForegroundColor Cyan

# Build all Docker images
Write-Host "`n📦 Building all Docker images..." -ForegroundColor Yellow
docker-compose build

# Tag images for Kubernetes
Write-Host "`n🏷️ Tagging images for Kubernetes..." -ForegroundColor Yellow
docker tag devsecops-frontend:latest withops-frontend:latest
docker tag devsecops-backend:latest withops-backend:latest
docker tag devsecops-ai-service:latest withops-ai-service:latest
docker tag devsecops-github-service:latest withops-github-service:latest
docker tag devsecops-auth-service:latest withops-auth-service:latest
docker tag devsecops-threat-modeling-service:latest withops-threat-modeling-service:latest
docker tag devsecops-workspace-intelligence-service:latest withops-workspace-intelligence-service:latest
docker tag devsecops-collaboration-service:latest withops-collaboration-service:latest
docker tag devsecops-workflow-orchestration-service:latest withops-workflow-orchestration-service:latest
docker tag devsecops-ai-rag-service:latest withops-ai-rag-service:latest

# Deploy infrastructure
Write-Host "`n🔧 Deploying infrastructure services..." -ForegroundColor Yellow
kubectl apply -f redis.yaml
kubectl apply -f monitoring.yaml

Write-Host "`n⏳ Waiting for infrastructure to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Deploy Kong Gateway
Write-Host "`n🌐 Deploying Kong API Gateway..." -ForegroundColor Yellow
kubectl apply -f kong-gateway.yaml

# Deploy all application services
Write-Host "`n🎯 Deploying all application services..." -ForegroundColor Yellow
kubectl apply -f backend-events-hub.yaml
kubectl apply -f ai-service.yaml
kubectl apply -f github-service.yaml
kubectl apply -f all-services.yaml
kubectl apply -f frontend.yaml

# Wait for deployments
Write-Host "`n⏳ Waiting for all deployments to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=available deployment --all -n withops --timeout=300s

# Show status
Write-Host "`n📊 Deployment Status:" -ForegroundColor Cyan
kubectl get all -n withops

# Get service URLs
Write-Host "`n🌍 Service URLs:" -ForegroundColor Cyan
$frontendPort = kubectl get svc frontend -n withops -o jsonpath='{.spec.ports[0].nodePort}'
if ($frontendPort) {
    Write-Host "Frontend: http://localhost:$frontendPort" -ForegroundColor Green
} else {
    Write-Host "Frontend: Check LoadBalancer external IP" -ForegroundColor Yellow
}

Write-Host "Grafana: http://localhost:3001 (admin/admin)" -ForegroundColor Green
Write-Host "Jaeger UI: http://localhost:16686" -ForegroundColor Green

Write-Host "`n✅ Complete deployment finished!" -ForegroundColor Green
Write-Host "`n📋 Deployed Services:" -ForegroundColor Yellow
Write-Host "  ✓ Frontend (Svelte)" -ForegroundColor Green
Write-Host "  ✓ Backend (Events Hub)" -ForegroundColor Green
Write-Host "  ✓ Kong API Gateway" -ForegroundColor Green
Write-Host "  ✓ AI Service" -ForegroundColor Green
Write-Host "  ✓ GitHub Service" -ForegroundColor Green
Write-Host "  ✓ Auth Service" -ForegroundColor Green
Write-Host "  ✓ Threat Modeling Service" -ForegroundColor Green
Write-Host "  ✓ Workspace Intelligence Service" -ForegroundColor Green
Write-Host "  ✓ Collaboration Service" -ForegroundColor Green
Write-Host "  ✓ Workflow Orchestration Service" -ForegroundColor Green
Write-Host "  ✓ AI RAG Service" -ForegroundColor Green
Write-Host "  ✓ Redis, Prometheus, Grafana, Jaeger" -ForegroundColor Green

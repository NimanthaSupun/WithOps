# PowerShell script to deploy WithOps to Kubernetes
# Run this after enabling Kubernetes in Docker Desktop

Write-Host "🚀 Deploying WithOps to Kubernetes..." -ForegroundColor Cyan

# Check if kubectl is available
if (!(Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ kubectl not found. Please enable Kubernetes in Docker Desktop" -ForegroundColor Red
    exit 1
}

# Check if Kubernetes is running
kubectl cluster-info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Kubernetes is not running. Enable it in Docker Desktop Settings" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Kubernetes cluster is running" -ForegroundColor Green

# Build Docker images
Write-Host "`n📦 Building Docker images..." -ForegroundColor Yellow
docker-compose build

# Create namespace
Write-Host "`n🏗️ Creating namespace..." -ForegroundColor Yellow
kubectl apply -f k8s/namespace.yaml

# Deploy infrastructure services
Write-Host "`n🔧 Deploying infrastructure..." -ForegroundColor Yellow
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/monitoring.yaml

Write-Host "`n⏳ Waiting for Redis to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=redis -n withops --timeout=120s

# Deploy Kong API Gateway
Write-Host "`n🌐 Deploying Kong Gateway..." -ForegroundColor Yellow
kubectl apply -f k8s/kong-gateway.yaml

# Deploy application services
Write-Host "`n🎯 Deploying application services..." -ForegroundColor Yellow
kubectl apply -f k8s/ai-service.yaml
kubectl apply -f k8s/github-service.yaml

# Wait for deployments
Write-Host "`n⏳ Waiting for deployments to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=available deployment --all -n withops --timeout=300s

# Show status
Write-Host "`n📊 Deployment Status:" -ForegroundColor Cyan
kubectl get all -n withops

# Get service URLs
Write-Host "`n🌍 Service URLs:" -ForegroundColor Cyan
Write-Host "Kong API Gateway: http://localhost:9000" -ForegroundColor Green
Write-Host "Kong Admin: http://localhost:9001" -ForegroundColor Green
Write-Host "Grafana: http://localhost:3001 (admin/admin)" -ForegroundColor Green
Write-Host "Jaeger UI: http://localhost:16686" -ForegroundColor Green
Write-Host "Prometheus: Available via port-forward" -ForegroundColor Green

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "`n💡 Useful commands:" -ForegroundColor Yellow
Write-Host "  kubectl get pods -n withops          # View all pods"
Write-Host "  kubectl logs -f <pod-name> -n withops # View logs"
Write-Host "  kubectl describe pod <name> -n withops # Pod details"
Write-Host "  kubectl get hpa -n withops            # Auto-scaling status"
Write-Host "  kubectl top pods -n withops           # Resource usage"

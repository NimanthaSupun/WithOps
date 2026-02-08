# ============================================================================
# Build Production Docker Images for Kubernetes Deployment
# ============================================================================
# These images include all production environment variables baked in at build time
# After building, push to your container registry (Docker Hub, AWS ECR, etc.)
# ============================================================================

Write-Host "🏗️  Building Production Docker Images for Kubernetes..." -ForegroundColor Cyan
Write-Host ""

# Change to project root
Set-Location "d:\project\dev-testing\DevSecOps"

# ============================================================================
# 1. BUILD FRONTEND IMAGE WITH PRODUCTION CONFIG
# ============================================================================
Write-Host "📦 Building Frontend Image..." -ForegroundColor Yellow

docker build `
  -f frontend/Dockerfile `
  --build-arg VITE_API_BASE_URL=https://api.withops.com `
  --build-arg VITE_WS_BASE_URL=api.withops.com `
  --build-arg VITE_AUTH0_DOMAIN=dev-sabxychpf6paj41u.us.auth0.com `
  --build-arg VITE_AUTH0_CLIENT_ID=KDsPl6bF0ngW5Y2lyk7EqaE0t3fAPDR7 `
  --build-arg VITE_AUTH0_CALLBACK_URL=https://app.withops.com/callback `
  --build-arg VITE_AUTH0_AUDIENCE=https://api.withops.com `
  --build-arg VITE_FRONTEND_URL=https://app.withops.com `
  -t withops-frontend:latest `
  -t withops-frontend:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Frontend image built successfully!" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 2. BUILD BACKEND IMAGE
# ============================================================================
Write-Host "📦 Building Backend Image..." -ForegroundColor Yellow

docker build `
  -f backend/Dockerfile `
  -t withops-backend:latest `
  -t withops-backend:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  backend/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Backend image built successfully!" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 3. BUILD MICROSERVICES IMAGES
# ============================================================================

# Auth Service
Write-Host "📦 Building Auth Service..." -ForegroundColor Yellow
docker build `
  -f services/auth-service/Dockerfile `
  -t withops-auth-service:latest `
  -t withops-auth-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/auth-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Auth Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Auth Service built!" -ForegroundColor Green
Write-Host ""

# GitHub Service
Write-Host "📦 Building GitHub Service..." -ForegroundColor Yellow
docker build `
  -f services/github-service/Dockerfile `
  -t withops-github-service:latest `
  -t withops-github-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/github-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ GitHub Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ GitHub Service built!" -ForegroundColor Green
Write-Host ""

# AI Service
Write-Host "📦 Building AI Service..." -ForegroundColor Yellow
docker build `
  -f services/ai-service/Dockerfile `
  -t withops-ai-service:latest `
  -t withops-ai-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/ai-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ AI Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ AI Service built!" -ForegroundColor Green
Write-Host ""

# Threat Modeling Service
Write-Host "📦 Building Threat Modeling Service..." -ForegroundColor Yellow
docker build `
  -f services/threat-modeling-service/Dockerfile `
  -t withops-threat-modeling-service:latest `
  -t withops-threat-modeling-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/threat-modeling-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Threat Modeling Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Threat Modeling Service built!" -ForegroundColor Green
Write-Host ""

# Collaboration Service
Write-Host "📦 Building Collaboration Service..." -ForegroundColor Yellow
docker build `
  -f services/collaboration-service/Dockerfile `
  -t withops-collaboration-service:latest `
  -t withops-collaboration-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/collaboration-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Collaboration Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Collaboration Service built!" -ForegroundColor Green
Write-Host ""

# Workspace Intelligence Service
Write-Host "📦 Building Workspace Intelligence Service..." -ForegroundColor Yellow
docker build `
  -f services/workspace-intelligence-service/Dockerfile `
  -t withops-workspace-intelligence-service:latest `
  -t withops-workspace-intelligence-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/workspace-intelligence-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Workspace Intelligence Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Workspace Intelligence Service built!" -ForegroundColor Green
Write-Host ""

# Workflow Orchestration Service
Write-Host "📦 Building Workflow Orchestration Service..." -ForegroundColor Yellow
docker build `
  -f services/workflow-orchestration-service/Dockerfile `
  -t withops-workflow-orchestration-service:latest `
  -t withops-workflow-orchestration-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/workflow-orchestration-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Workflow Orchestration Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Workflow Orchestration Service built!" -ForegroundColor Green
Write-Host ""

# AI RAG Service
Write-Host "📦 Building AI RAG Service..." -ForegroundColor Yellow
docker build `
  -f services/ai-rag-service/Dockerfile `
  -t withops-ai-rag-service:latest `
  -t withops-ai-rag-service:prod-$(Get-Date -Format "yyyyMMdd-HHmmss") `
  services/ai-rag-service/

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ AI RAG Service build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ AI RAG Service built!" -ForegroundColor Green
Write-Host ""

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ ALL IMAGES BUILT SUCCESSFULLY!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Built Images:" -ForegroundColor Yellow
docker images | Select-String "withops-"
Write-Host ""
Write-Host "Built components:" -ForegroundColor Cyan
Write-Host "  ✅ Frontend" -ForegroundColor Green
Write-Host "  ✅ Backend (Events Hub)" -ForegroundColor Green
Write-Host "  ✅ Auth Service" -ForegroundColor Green
Write-Host "  ✅ GitHub Service" -ForegroundColor Green
Write-Host "  ✅ AI Service" -ForegroundColor Green
Write-Host "  ✅ Threat Modeling Service" -ForegroundColor Green
Write-Host "  ✅ Collaboration Service" -ForegroundColor Green
Write-Host "  ✅ Workspace Intelligence Service" -ForegroundColor Green
Write-Host "  ✅ Workflow Orchestration Service" -ForegroundColor Green
Write-Host "  ✅ AI RAG Service" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Cyan
Write-Host "1. (Optional) Tag and push to registry:"
Write-Host "   docker tag withops-frontend:latest your-registry/withops-frontend:latest"
Write-Host "   docker push your-registry/withops-frontend:latest"
Write-Host ""
Write-Host "2. Deploy to Kubernetes:"
Write-Host "   kubectl apply -f k8s/"
Write-Host ""
Write-Host "3. Check deployment status:"
Write-Host "   kubectl get pods -n withops"
Write-Host ""
Write-Host "4. View services:"
Write-Host "   kubectl get svc -n withops"
Write-Host ""

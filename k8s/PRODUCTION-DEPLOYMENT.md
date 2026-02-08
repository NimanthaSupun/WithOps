# WithOps DevSecOps Platform - Kubernetes Production Deployment

## 🎯 Overview

This guide covers deploying the WithOps DevSecOps Platform to Kubernetes with **production configuration**.

### Architecture
- **Frontend**: SvelteKit app at `app.withops.com`
- **Backend**: FastAPI Events Hub (WebSocket + Event Bus) at `api.withops.com`
- **Microservices**: 
  - Auth Service (8006) - Authentication and authorization
  - GitHub Service (8002) - GitHub integration
  - AI Service (8001) - Claude AI/ML operations
  - Threat Modeling Service (8003) - Security threat analysis
  - Collaboration Service (8105) - Team collaboration
  - Workspace Intelligence Service (8004) - Workspace analysis
  - Workflow Orchestration Service (8007) - CI/CD management
  - AI RAG Service (8008) - Conversational AI with RAG
- **API Gateway**: Kong Gateway for routing and CORS
- **Data**: Redis cache, Supabase PostgreSQL
- **Monitoring**: Prometheus + Grafana

---

## 📋 Prerequisites

1. **Kubernetes Cluster** running and accessible
   ```powershell
   kubectl cluster-info
   kubectl get nodes
   ```

2. **Docker** installed for building images
   ```powershell
   docker --version
   ```

3. **Domain DNS** configured:
   - `app.withops.com` → Your cluster IP/load balancer
   - `api.withops.com` → Your cluster IP/load balancer

4. **SSL Certificates** (for production HTTPS)
   - Use cert-manager or manual certificates
   - Configure in Kong Gateway or Ingress Controller

---

## 🏗️ Step 1: Build Production Docker Images

Run the build script to create all images with production configuration baked in:

```powershell
cd d:\project\dev-testing\DevSecOps
.\k8s\BUILD-PRODUCTION-IMAGES.ps1
```

This builds:
- ✅ `withops-frontend:latest` - With Auth0 and API URLs
- ✅ `withops-backend:latest` - With Supabase and GitHub App config
- ✅ `withops-auth-service:latest` - Authentication service
- ✅ `withops-github-service:latest` - GitHub integration service
- ✅ `withops-ai-service:latest` - AI/Claude service
- ✅ `withops-threat-modeling-service:latest` - Threat modeling service
- ✅ `withops-collaboration-service:latest` - Collaboration service
- ✅ `withops-workspace-intelligence-service:latest` - Workspace intelligence service
- ✅ `withops-workflow-orchestration-service:latest` - Workflow orchestration service
- ✅ `withops-ai-rag-service:latest` - AI RAG service

### 🔄 (Optional) Push to Container Registry

If deploying to remote cluster, push images:

```powershell
# Tag for your registry
docker tag withops-frontend:latest your-registry.io/withops-frontend:latest
docker tag withops-backend:latest your-registry.io/withops-backend:latest
docker tag withops-github-service:latest your-registry.io/withops-github-service:latest
docker tag withops-ai-service:latest your-registry.io/withops-ai-service:latest

# Push to registry
docker push your-registry.io/withops-frontend:latest
docker push your-registry.io/withops-backend:latest
docker push your-registry.io/withops-github-service:latest
docker push your-registry.io/withops-ai-service:latest
```

**Then update image names in k8s YAML files:**
```yaml
image: your-registry.io/withops-frontend:latest
```

---

## 🚀 Step 2: Deploy to Kubernetes

### 2.1 Create Namespace
```powershell
kubectl apply -f k8s/namespace.yaml
```

### 2.2 Deploy Infrastructure (Redis, Monitoring)
```powershell
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/monitoring.yaml  # Prometheus + Grafana
```

### 2.3 Deploy Application Services
```powershell
# Backend (Events Hub)
kubectl apply -f k8s/backend-events-hub.yaml

# Microservices
kubectl apply -f k8s/auth-service.yaml
kubectl apply -f k8s/github-service.yaml
kubectl apply -f k8s/ai-service.yaml
kubectl apply -f k8s/threat-modeling-service.yaml
kubectl apply -f k8s/collaboration-service.yaml
kubectl apply -f k8s/workspace-intelligence-service.yaml
kubectl apply -f k8s/workflow-orchestration-service.yaml
kubectl apply -f k8s/ai-rag-service.yaml

# Frontend
kubectl apply -f k8s/frontend.yaml

# API Gateway
kubectl apply -f k8s/kong-gateway.yaml
```

### 2.4 Deploy All at Once (Alternative)
```powershell
kubectl apply -f k8s/
```

---

## ✅ Step 3: Verify Deployment

### Check Pods Status
```powershell
kubectl get pods -n withops
```

Expected output:
```
NAME                              READY   STATUS    RESTARTS   AGE
backend-xxx                       1/1     Running   0          2m
frontend-xxx                      1/1     Running   0          2m
github-service-xxx                1/1     Running   0          2m
ai-service-xxx                    1/1     Running   0          2m
kong-xxx                          1/1     Running   0          2m
redis-xxx                         1/1     Running   0          3m
```

### Check Services
```powershell
kubectl get svc -n withops
```

### View Logs
```powershell
# Backend logs
kubectl logs -f deployment/backend -n withops

# Frontend logs
kubectl logs -f deployment/frontend -n withops

# GitHub service logs
kubectl logs -f deployment/github-service -n withops
```

### Test Health Endpoints
```powershell
# Port-forward to test locally
kubectl port-forward svc/backend 8000:9100 -n withops
# Then visit: http://localhost:8000/health

kubectl port-forward svc/frontend 3000:5173 -n withops
# Then visit: http://localhost:3000
```

---

## 🌐 Step 4: Configure External Access

### Option A: LoadBalancer (Cloud Provider)

If using AWS/GCP/Azure, the LoadBalancer services will automatically get external IPs:

```powershell
kubectl get svc -n withops
```

Look for EXTERNAL-IP, then update your DNS:
- `app.withops.com` → Frontend EXTERNAL-IP
- `api.withops.com` → Kong Gateway EXTERNAL-IP

### Option B: Ingress Controller (Recommended)

Create an Ingress resource for routing:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: withops-ingress
  namespace: withops
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.withops.com
    - api.withops.com
    secretName: withops-tls
  rules:
  - host: app.withops.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 5173
  - host: api.withops.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kong
            port:
              number: 8000
```

Apply:
```powershell
kubectl apply -f k8s/ingress.yaml
```

---

## 🔧 Configuration Details

### Environment Variables

All configured in k8s YAML files:

**Frontend** (`k8s/frontend.yaml`):
```yaml
env:
  - name: VITE_API_BASE_URL
    value: "https://api.withops.com"
  - name: VITE_WS_BASE_URL
    value: "api.withops.com"
  - name: VITE_AUTH0_DOMAIN
    value: "dev-sabxychpf6paj41u.us.auth0.com"
  - name: VITE_AUTH0_CLIENT_ID
    value: "KDsPl6bF0ngW5Y2lyk7EqaE0t3fAPDR7"
```

**Backend** (`k8s/backend-events-hub.yaml`):
```yaml
env:
  - name: FRONTEND_URL
    value: "https://app.withops.com"
  - name: GITHUB_APP_ID
    value: "2710627"  # Production GitHub App
  - name: SUPABASE_URL
    value: "https://fcmcsbmsntmpeyjltqbi.supabase.co"
```

### GitHub App Configuration

**Production GitHub App** (ID: 2710627):
- Name: `WithOps-DevSecOps-Platform`
- Callback URL: `https://app.withops.com/callback`
- Webhook URL: `https://api.withops.com/webhooks/github`
- Permissions: See GitHub App setup guide

---

## 📊 Monitoring

### Access Grafana Dashboard
```powershell
kubectl port-forward svc/grafana 3001:3000 -n withops
```
Visit: http://localhost:3001
- Username: `admin`
- Password: Check `k8s/monitoring.yaml` for configured password

### Access Prometheus
```powershell
kubectl port-forward svc/prometheus 9090:9090 -n withops
```
Visit: http://localhost:9090

### View Metrics
```powershell
# CPU and Memory usage
kubectl top pods -n withops

# Auto-scaling status
kubectl get hpa -n withops
```

---

## 🔄 Updates and Rollbacks

### Update an Image
```powershell
# Rebuild image
.\k8s\BUILD-PRODUCTION-IMAGES.ps1

# Restart deployment to pull new image
kubectl rollout restart deployment/frontend -n withops
kubectl rollout restart deployment/backend -n withops
```

### Rollback to Previous Version
```powershell
kubectl rollout undo deployment/frontend -n withops
kubectl rollout history deployment/frontend -n withops
```

### Scale Services
```powershell
# Manual scaling
kubectl scale deployment/github-service --replicas=5 -n withops

# Auto-scaling is configured in YAML files (HPA)
```

---

## 🐛 Troubleshooting

### Pods Not Starting
```powershell
kubectl describe pod <pod-name> -n withops
kubectl logs <pod-name> -n withops --previous  # Previous container logs
```

### Connection Refused Errors
1. Check service endpoints:
   ```powershell
   kubectl get endpoints -n withops
   ```

2. Verify DNS resolution inside pod:
   ```powershell
   kubectl exec -it <pod-name> -n withops -- nslookup backend
   ```

### Auth0 Redirect Issues
- Verify `FRONTEND_URL` in backend is set to `https://app.withops.com`
- Check Auth0 Application settings:
  - Allowed Callback URLs: `https://app.withops.com/callback`
  - Allowed Logout URLs: `https://app.withops.com`
  - Allowed Web Origins: `https://app.withops.com`

### CORS Errors
- Verify Kong Gateway CORS configuration in `k8s/kong-gateway.yaml`
- Check backend `CORS_ORIGINS` includes `https://app.withops.com`

---

## 🗑️ Cleanup

### Remove All Resources
```powershell
kubectl delete namespace withops
```

### Remove Specific Services
```powershell
kubectl delete -f k8s/frontend.yaml
kubectl delete -f k8s/backend-events-hub.yaml
```

---

## 📚 Key Differences: Docker Compose vs Kubernetes

| Feature | Docker Compose | Kubernetes |
|---------|---------------|------------|
| **Scaling** | Manual only | Auto-scaling (HPA) |
| **Load Balancing** | Single instance | Multiple replicas |
| **Self-Healing** | No | Yes (restarts pods) |
| **Updates** | Stop/Start | Rolling updates |
| **Monitoring** | External tools | Built-in metrics |
| **Multi-Node** | No | Yes |

---

## 🎯 Quick Commands Reference

```powershell
# View all resources
kubectl get all -n withops

# Check pod logs
kubectl logs -f deployment/backend -n withops

# Execute command in pod
kubectl exec -it <pod-name> -n withops -- /bin/sh

# Port forward to service
kubectl port-forward svc/backend 8000:9100 -n withops

# Describe resource for details
kubectl describe pod <pod-name> -n withops

# Get events
kubectl get events -n withops --sort-by='.lastTimestamp'
```

---

## ✅ Production Checklist

- [ ] All Docker images built with production config
- [ ] Images pushed to container registry (if remote cluster)
- [ ] Kubernetes cluster accessible
- [ ] DNS records configured (`app.withops.com`, `api.withops.com`)
- [ ] SSL certificates configured
- [ ] Auth0 callback URLs updated
- [ ] GitHub App webhook URL set to production
- [ ] Supabase connection working
- [ ] All pods in `Running` state
- [ ] Frontend accessible at `https://app.withops.com`
- [ ] API accessible at `https://api.withops.com`
- [ ] GitHub OAuth redirect working
- [ ] WebSocket connections working
- [ ] Monitoring dashboards accessible

---

## 🆘 Support

For issues:
1. Check logs: `kubectl logs -f deployment/<service> -n withops`
2. Check events: `kubectl get events -n withops`
3. Verify configuration: `kubectl describe deployment/<service> -n withops`
4. Review this guide's Troubleshooting section

---

**🎉 Your production deployment is ready!**

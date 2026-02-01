===========================================
WithOps Kubernetes Deployment Guide
===========================================

WHY KUBERNETES?
---------------
✅ Auto-scaling: Automatically scale services based on CPU/memory
✅ Self-healing: Restart failed containers automatically
✅ Load balancing: Distribute traffic across multiple instances
✅ Zero-downtime deployments: Update services without stopping
✅ Resource management: Set CPU/memory limits per service
✅ Production-ready: Industry standard for microservices

SETUP STEPS
-----------

1. Enable Kubernetes in Docker Desktop:
   - Open Docker Desktop
   - Go to Settings → Kubernetes
   - Check "Enable Kubernetes"
   - Click "Apply & Restart"
   - Wait 2-3 minutes for Kubernetes to start

2. Verify Kubernetes is running:
   > kubectl cluster-info
   > kubectl get nodes

3. Update secrets in k8s/github-service.yaml:
   - Replace "your-supabase-url" with actual values
   - Replace "your-github-app-id" with actual values

4. Deploy to Kubernetes:
   > .\k8s\deploy.ps1

WHAT GETS DEPLOYED?
-------------------
✅ Redis (1 pod) - Caching & Pub/Sub
✅ Kong Gateway (2 pods) - API Gateway with load balancing
✅ GitHub Service (2-10 pods) - Auto-scales based on load
✅ AI Service (2-15 pods) - Auto-scales based on load
✅ Prometheus - Metrics collection
✅ Grafana - Dashboards (http://localhost:3001)
✅ Jaeger - Distributed tracing (http://localhost:16686)

AUTO-SCALING EXAMPLE
--------------------
GitHub Service:
- Minimum: 2 pods (always running)
- Maximum: 10 pods
- Scales up when CPU > 70% or Memory > 80%
- Scales down when usage decreases

AI Service:
- Minimum: 2 pods
- Maximum: 15 pods (AI needs more capacity)
- Scales up when CPU > 75%

USEFUL COMMANDS
---------------

View all services:
> kubectl get all -n withops

View pods:
> kubectl get pods -n withops

View logs:
> kubectl logs -f <pod-name> -n withops

View auto-scaling status:
> kubectl get hpa -n withops

See resource usage:
> kubectl top pods -n withops

Scale manually:
> kubectl scale deployment github-service --replicas=5 -n withops

Delete everything:
> kubectl delete namespace withops

Port-forward to a service:
> kubectl port-forward svc/prometheus 9090:9090 -n withops

Execute command in pod:
> kubectl exec -it <pod-name> -n withops -- /bin/sh

DIFFERENCES FROM DOCKER COMPOSE
--------------------------------

Docker Compose:
- Single machine only
- Manual scaling
- No self-healing
- Good for development

Kubernetes:
- Multi-node clusters
- Auto-scaling
- Self-healing
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

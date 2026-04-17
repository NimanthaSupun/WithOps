# Frontend UI Enhancement - Test & Validation Guide

## Docker Microservice Architecture

**Project**: WithOps DevSecOps Platform  
**Component**: Pipeline Predictor Dashboard (Phase 3 UI Enhancement)  
**Date**: April 2026

---

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              Frontend (5173)                         │
│           Svelte 5 + Vite SPA                        │
│  - Updated: Predictor Page UI Patterns               │
└────────────────┬────────────────────────────────────┘
                 │ HTTP/WebSocket
┌────────────────▼────────────────────────────────────┐
│         Kong Gateway (Port 9000)                     │
│         API Router & Request Distributor             │
└──┬──┬──┬──┬──┬──┬──┬──┬──────────────────────────────┘
   │  │  │  │  │  │  │  │
   │  │  │  │  │  │  │  └─→ Pipeline Prediction (9109)
   │  │  │  │  │  │  └────→ AI RAG Service (9108)
   │  │  │  │  │  └───────→ Workflow Orchestration (9107)
   │  │  │  │  └──────────→ Auth Service (9106)
   │  │  │  └─────────────→ Collaboration (9105)
   │  │  └────────────────→ Threat Modeling (9103)
   │  └─────────────────→ GitHub Service (9102)
   └──────────────────→ AI Service (9101)

Infrastructure:
- Redis (16379) - Cache & Queue
- PostgreSQL (Supabase) - Database
- Ollama (11434) - LLM Models
- Qdrant (6333) - Vector DB for RAG
- Prometheus (9091) - Metrics
- Grafana (3001) - Monitoring
- Jaeger (16686) - Distributed Tracing
```

---

## 🚀 Quick Start (5 minutes)

### **Option 1: Test with Existing Built Images**

```powershell
# 1. Navigate to project root
cd d:\project\dev-testing\DevSecOps

# 2. Start all services
docker-compose up -d

# 3. Wait for services to be ready (30-60 seconds)
docker-compose ps

# 4. Access frontend
# Open browser: http://localhost:5173

# 5. View logs for any issues
docker-compose logs frontend
docker-compose logs kong
```

### **Option 2: Test with Hot-Reload (Dev Mode - Recommended)**

Use this to see UI changes in real-time without rebuilding Docker image.

```powershell
# 1. Start backend microservices only
docker-compose up -d kong redis ollama qdrant prometheus
docker-compose up -d github-service threat-modeling-service
docker-compose up -d ai-service workspace-intelligence-service
docker-compose up -d pipeline-prediction-service auth-service

# 2. Wait for Kong & services to be ready
Start-Sleep -Seconds 10
docker-compose logs kong

# 3. In separate terminal, start frontend with hot-reload
cd frontend
npm install  # if dependencies changed
npm run dev

# Frontend will be at: http://localhost:5173 (with hot-reload enabled)

# 4. Edit predictor page - changes reflect instantly
# File: frontend/src/routes/github/workspace/[org]/predictor/+page.svelte
```

---

## 🧪 Test Scenarios

### **Test 1: UI Element Visibility**

**Objective**: Verify all new UI components render correctly

**Steps**:

1. Open Browser DevTools (F12)
2. Navigate to: `http://localhost:5173/github/workspace/[your-org]/predictor`
3. Check Elements Inspector → Search for:

```html
<!-- NEW: Header Actions -->
<div class="header-actions">
  <a href="..." class="btn btn-secondary">Model Accuracy</a>
  <button class="btn btn-secondary" aria-label="Refresh predictions">
    ...
  </button>
</div>

<!-- NEW: Stats Panel -->
<div class="stats-panel">
  <div class="stat-cell">
    <svg>...</svg>
    <div class="stat-info">
      <span class="stat-val">5</span>
      <span class="stat-lbl">Repositories</span>
    </div>
  </div>
</div>

<!-- NEW: Loading State -->
<div class="center-state">
  <img src="/icons/excellence_17274210.png" class="loader-icon" />
  <div class="loader-text">ANALYZING PIPELINES...</div>
</div>

<!-- NEW: Empty State -->
<div class="center-state">
  <svg class="empty-icon">...</svg>
  <h3>No repositories found</h3>
</div>

<!-- NEW: Error State -->
<div class="center-state">
  <svg class="error-icon">...</svg>
  <h3>Failed to load predictions</h3>
</div>
```

**Validation Checklist**:

- [ ] Header actions visible with proper spacing
- [ ] "Model Accuracy" button shows chart icon + text
- [ ] Refresh button shows refresh icon only
- [ ] Stats panel displays 3 stat cells with icons
- [ ] Each stat shows value + label correctly
- [ ] All buttons have proper styling (`.btn .btn-secondary` classes)
- [ ] Text is uppercase where required (ANALYZING PIPELINES...)

**Failed?** → Check browser console for errors (F12 → Console tab)

---

### **Test 2: Loading State**

**Objective**: Verify loading animation and branded icon appear during data fetch

**Steps**:

```powershell
# 1. Throttle network in DevTools for slow loading
# DevTools → Network tab → Throttling: "Slow 3G"

# 2. Reload page: http://localhost:5173/github/workspace/[org]/predictor

# 3. Observe for 2-3 seconds before data loads

# 4. Check what you see:
```

**Expected Behavior**:

✅ Icon with pulse animation appears  
✅ Text reads "ANALYZING PIPELINES..." (uppercase)  
✅ Centered on screen  
✅ Icon fades in/out smoothly (pulse animation)

**Validation**:

```javascript
// Open DevTools Console and run:
document.querySelector(".center-state"); // Should exist
document.querySelector(".loader-icon"); // Should exist
document.querySelector(".loader-text"); // Should contain "ANALYZING PIPELINES..."

// Check CSS animation
getComputedStyle(document.querySelector(".loader-icon")).animation;
// Should show: pulse 2s ease-in-out infinite
```

---

### **Test 3: Empty State**

**Objective**: Verify empty state displays when organization has no repositories

**Steps**:

```powershell
# 1. Access dashboard with empty organization
# http://localhost:5173/github/workspace/[org-without-repos]/predictor

# 2. Observe page content
```

**Expected Behavior**:

✅ Repository icon displays  
✅ Heading: "No repositories found"  
✅ Description text visible  
✅ Centered layout with proper spacing

**Test with Docker Network**:

```powershell
# Check if backend services are accessible
docker-compose exec frontend curl http://github-service:8002/api/organizations

# If connection fails
docker-compose logs github-service
```

---

### **Test 4: Error State**

**Objective**: Verify error handling and retry button

**Steps**:

1. Stop GitHub service:

   ```powershell
   docker-compose stop github-service
   ```

2. Refresh page: `http://localhost:5173/github/workspace/[org]/predictor`

3. Observe error display

**Expected Behavior**:

✅ Error icon displays (warning symbol)  
✅ Title: "Failed to load predictions"  
✅ Error message visible from API  
✅ Red "Retry" button present

4. Test retry:

   ```powershell
   docker-compose start github-service
   ```

5. Click "Retry" button → Data should load

**Validation Checklist**:

- [ ] Error layout is centered with proper spacing
- [ ] Error message is readable
- [ ] Retry button is clickable
- [ ] Button has correct styling (`.btn .btn-primary`)
- [ ] After retry, data loads successfully

---

### **Test 5: Dark/Light Mode Toggle**

**Objective**: Verify UI adapts to theme changes

**Steps**:

1. Open page: `http://localhost:5173/github/workspace/[org]/predictor`

2. Click theme toggle (moon/sun icon) in header

3. Observe changes:

**Expected Behavior**:

- [ ] **Dark Mode**:
  - Background turns black
  - Text turns light gray
  - Icons remain visible with proper contrast
  - Stats panel has dark background
  - Borders are subtle (light gray)

- [ ] **Light Mode**:
  - Background turns white
  - Text turns dark
  - Stats panel has light gray background
  - Proper contrast throughout

**CSS Verification**:

```javascript
// In DevTools Console
const darkVars = {
  "--bg-app": getComputedStyle(document.documentElement).getPropertyValue(
    "--bg-app",
  ),
  "--text-primary": getComputedStyle(document.documentElement).getPropertyValue(
    "--text-primary",
  ),
  "--accent": getComputedStyle(document.documentElement).getPropertyValue(
    "--accent",
  ),
};
console.log(darkVars);
```

---

### **Test 6: Responsive Design**

**Objective**: Verify layout adapts to different screen sizes

**Steps**:

1. Open DevTools (F12) → Device Toolbar (Ctrl+Shift+M)

2. Test on different viewport sizes:

**Mobile (375px)**:

```powershell
# Expected:
- [ ] Header buttons stack vertically
- [ ] Stats panel shows 1 column
- [ ] Sidebar collapses to icons only
- [ ] Text remains readable
- [ ] No horizontal scroll
```

**Tablet (768px)**:

```powershell
# Expected:
- [ ] Header buttons in single row
- [ ] Stats panel shows 2 columns
- [ ] Sidebar expanded/collapsible
- [ ] All content visible
```

**Desktop (1440px)**:

```powershell
# Expected:
- [ ] Full layout with sidebars
- [ ] Stats panel shows 3 columns
- [ ] Proper spacing and alignment
```

**Test Breakpoints**:

```javascript
// DevTools Console:
// At 640px
window.matchMedia("(max-width: 640px)").matches; // true

// At 1024px
window.matchMedia("(max-width: 1024px)").matches; // true
```

---

### **Test 7: Button Interactions**

**Objective**: Verify buttons are clickable and navigate correctly

**Steps**:

1. **Model Accuracy Button**:

   ```
   Click → Should navigate to /github/workspace/[org]/predictor/accuracy
   Expected: Dashboard with 8 metric sections loads
   ```

2. **Refresh Button**:

   ```
   Click → Data re-fetches from backend
   Expected: Loading state appears briefly, then updates
   ```

3. **Retry Button** (after error):
   ```
   Click → Attempts to reload data
   Expected: Calls API again, displays results or error
   ```

**Validation**:

```javascript
// DevTools Console - Test button classes
document.querySelectorAll(".btn").forEach((btn) => {
  console.log(btn.className, btn.textContent);
});
```

**Expected Output**:

```
btn btn-secondary Model Accuracy
btn btn-secondary  (refresh icon)
btn btn-primary Retry (only visible after error)
```
---

### **Test 8: API Integration**

**Objective**: Verify frontend correctly calls backend microservices

**Steps**:

1. Open DevTools → Network tab

2. Navigate to predictor page

3. Watch network requests:

**Expected Calls** (to Kong Gateway port 9000):

```
GET /api/pipelines/predictions
  - Source: pipeline-prediction-service
  - Response: Prediction data for each workflow

GET /api/pipelines/metrics
  - Source: pipeline-prediction-service
  - Response: Accuracy metrics

GET /api/github/organizations/[org]
  - Source: github-service
  - Response: Repositories list
```

**Check Response Times**:

```powershell
# Network tab should show:
- (pipeline predictions): ~200-500ms
- (metrics): ~200-500ms
- (org data): ~100-300ms

# If times are slow, check:
docker-compose logs pipeline-prediction-service
docker-compose logs github-service
```

---

### **Test 9: Accessibility**

**Objective**: Verify WCAG compliance for UI components

**Steps**:

1. Install axe DevTools Chrome extension

2. Run audit on predictor page:
   ```
   DevTools → AxeDevTools → Scan page
   ```

**Expected Results**:

- [ ] No critical issues
- [ ] All buttons have aria-labels
- [ ] Images have alt text
- [ ] Color contrast is sufficient
- [ ] Keyboard navigation works (Tab key)

**Manual Keyboard Test**:

```
1. Press Tab to navigate through buttons
2. Press Enter to activate focused button
3. Expected: All interactive elements accessible
```

---

### **Test 10: Performance**

**Objective**: Verify UI renders efficiently

**Steps**:

1. Open DevTools → Performance tab

2. Click record → Navigate to predictor page → Stop recording

3. Analyze results:

**Expected Metrics**:

- [ ] First Contentful Paint (FCP): < 2s
- [ ] Largest Contentful Paint (LCP): < 3s
- [ ] Cumulative Layout Shift (CLS): < 0.1
- [ ] Time to Interactive (TTI): < 4s

**Memory Check**:

```javascript
// DevTools Console:
console.memory.usedJSHeapSize / 1048576 + " MB";
// Should be < 50MB for initial load
```

---

## 🔍 Troubleshooting

### **Frontend Won't Connect to Backend**

```powershell
# 1. Check Kong gateway is running
docker-compose ps kong

# 2. Test Kong connectivity
curl http://localhost:9000/api/health

# 3. Check individual services
docker-compose ps

# 4. View Kong logs
docker-compose logs kong

# 5. Verify network connectivity
docker-compose exec frontend curl http://kong:8000/api/health
```

### **UI Components Not Rendering**

```powershell
# 1. Clear browser cache
# DevTools → Application → Clear Storage → Clear All

# 2. Check console errors
docker-compose logs frontend

# 3. Check Vite build
docker-compose build --no-cache frontend

# 4. Restart frontend
docker-compose restart frontend
```

### **Hot-Reload Not Working (Dev Mode)**

```powershell
# 1. Verify file permissions
icacls d:\project\dev-testing\DevSecOps\frontend

# 2. Stop npm dev server
Ctrl+C

# 3. Clear node_modules
rm -r frontend/node_modules

# 4. Reinstall & start
cd frontend
npm install
npm run dev
```

### **Services Timing Out**

```powershell
# 1. Increase Docker resource limits
# Edit docker-compose.yml and add:
# deploy:
#   resources:
#     limits:
#       memory: 2G

# 2. Restart all services
docker-compose restart

# 3. Monitor resource usage
docker stats
```

---

## 📊 Monitoring During Tests

### **Real-Time Logs**

```powershell
# Frontend logs (shows build & runtime errors)
docker-compose logs -f frontend

# Backend services
docker-compose logs -f pipeline-prediction-service
docker-compose logs -f github-service

# Kong gateway
docker-compose logs -f kong

# All services
docker-compose logs -f
```

### **Service Health Dashboard**

```powershell
# Access Grafana monitoring
# http://localhost:3001
# Username: admin
# Password: admin

# Check dashboards:
# - Kong API Gateway
# - Services Performance
# - Error Rates
```

### **Distributed Tracing**

```powershell
# Access Jaeger for request traces
# http://localhost:16686

# Search by:
# - Service: frontend
# - Operation: HTTP requests
# - See request flow through microservices
```

---

## ✅ Final Validation Checklist

Before declaring UI changes complete:

```
[ ] All UI components render without errors
[ ] Loading state displays with branded icon
[ ] Error state shows proper error handling
[ ] Empty state appears when no data
[ ] Dark/light mode toggle works
[ ] Responsive design works on mobile/tablet/desktop
[ ] Header buttons (Model Accuracy, Refresh) navigate correctly
[ ] Stats panel displays all metrics with icons
[ ] All buttons have proper styling and hierarchy
[ ] Accessibility score is 90+ (no critical issues)
[ ] Network requests complete within timeout
[ ] Performance metrics are acceptable
[ ] No console errors or warnings
[ ] Docker services all healthy (docker-compose ps)
[ ] Hot-reload works in dev mode
```

---

## 🚀 Next Steps

After validation passes:

1. **Commit changes**:

   ```powershell
   git add frontend/src/routes/github/workspace/[org]/predictor/+page.svelte
   git commit -m "feat(ui): enhance predictor page with design patterns

   - Add header actions (accuracy link + refresh button)
   - Replace stats panel with icon grid layout
   - Implement branded loading state
   - Add error and empty states
   - Ensure dark/light mode support
   - Make fully responsive
   "
   ```

2. **Build production image**:

   ```powershell
   docker-compose build frontend
   ```

3. **Push to registry** (if deploying):

   ```powershell
   docker tag withops-frontend:latest registry.withops.com/frontend:latest
   docker push registry.withops.com/frontend:latest
   ```

4. **Deploy to production** (via K8s):
   ```powershell
   kubectl apply -f k8s/frontend.yaml
   ```

---

## 📞 Support & Questions

- **Frontend Issues**: Check `docker-compose logs frontend`
- **Backend Issues**: Check `docker-compose logs [service-name]`
- **Network Issues**: Verify Kong gateway with `curl http://localhost:9000/api/health`
- **Build Issues**: Rebuild with `docker-compose build --no-cache frontend`

---

**Version**: 1.0  
**Last Updated**: April 10, 2026  
**Status**: Ready for Testing

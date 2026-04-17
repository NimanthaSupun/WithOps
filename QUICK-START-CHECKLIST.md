# Quick Start - Test & Validation Checklist

## 🚀 Fastest Path (Choose One)

### **Option A: Automated Script (Easiest - 2 minutes)**

```powershell
# Navigate to project root
cd d:\project\dev-testing\DevSecOps

# Quick test - starts core services only
.\test-validation.ps1 -Mode quick -Org your-org

# OR: Dev mode with hot-reload (best for iteration)
.\test-validation.ps1 -Mode dev -Org your-org

# OR: Full environment with all services
.\test-validation.ps1 -Mode full -Org your-org

# Clean up when done
.\test-validation.ps1 -Mode cleanup
```

---

### **Option B: Manual Docker Commands (More Control)**

#### **1️⃣ Start Background Services**

```powershell
cd d:\project\dev-testing\DevSecOps

# Start core backend services
docker-compose up -d kong redis
docker-compose up -d github-service pipeline-prediction-service
docker-compose up -d auth-service

# Wait ~10 seconds for startup
Start-Sleep -Seconds 10

# Verify services running
docker-compose ps
# Look for "Up" status on these services

# Check Kong is ready
curl http://localhost:9000/api/health
# Should return 200 OK
```

#### **2️⃣ Start Frontend**

**Option 2A: Production Build (Docker)**

```powershell
# Build and start frontend container
docker-compose up -d frontend

# Wait for startup
Start-Sleep -Seconds 10

# Open browser
start http://localhost:5173/github/workspace/your-org/predictor
```

**Option 2B: Dev Mode with Hot-Reload (Best for Testing)**

```powershell
# In new terminal, start frontend dev server
cd frontend

# Install dependencies (if needed)
npm install

# Start with hot-reload
npm run dev

# Frontend will be at: http://localhost:5173
# (Changes auto-refresh as you edit files)
```

#### **3️⃣ View Logs**

```powershell
# Frontend logs (real-time)
docker-compose logs -f frontend

# Microservice logs
docker-compose logs -f github-service
docker-compose logs -f pipeline-prediction-service

# Kong gateway logs
docker-compose logs -f kong

# All services
docker-compose logs -f
```

---

## ✅ Validation Checklist

### **Test 1: Load Page**

- [ ] Open: `http://localhost:5173/github/workspace/your-org/predictor`
- [ ] Page loads without errors (check F12 console)
- [ ] Header, sidebar, and main content visible

### **Test 2: UI Elements Present**

- [ ] Header has two buttons: "Model Accuracy" + "Refresh" button
- [ ] Stats panel visible with 3 stat cells (icon + value + label)
- [ ] All icons render correctly
- [ ] Text is properly formatted

### **Test 3: Loading State**

- [ ] Throttle network in DevTools (F12 → Network → fast 3G)
- [ ] Reload page
- [ ] See branded loader icon with "ANALYZING PIPELINES..." text (for 2-3 seconds)
- [ ] Icon pulses smoothly
- [ ] Text is centered

### **Test 4: Button Interactions**

- [ ] Click "Model Accuracy" → Navigates to accuracy dashboard
- [ ] Click Refresh button → Data reloads (loading state appears briefly)
- [ ] Buttons have hover effects (change color/background)

### **Test 5: Dark/Light Mode**

- [ ] Click theme toggle (moon/sun icon) in header
- [ ] **Dark mode**: Background black, text light gray
- [ ] **Light mode**: Background white, text dark
- [ ] All UI elements visible in both modes
- [ ] Proper contrast throughout

### **Test 6: Responsive Design**

Open DevTools (F12) → Device Toolbar (Ctrl+Shift+M)

- [ ] **Mobile (375px)**: Single column layout, buttons stack
- [ ] **Tablet (768px)**: 2-column stats, buttons side by side
- [ ] **Desktop (1440px)**: Full layout with all elements visible
- [ ] No horizontal scrolling on any size
- [ ] Text remains readable

### **Test 7: Error State**

- [ ] Stop GitHub service: `docker-compose stop github-service`
- [ ] Reload page
- [ ] See error icon + "Failed to load predictions" message
- [ ] "Retry" button visible and clickable
- [ ] Start service: `docker-compose start github-service`
- [ ] Click Retry → Data loads successfully

### **Test 8: Empty State**

- [ ] Access org with no repositories
- [ ] See repository icon + "No repositories found" message
- [ ] Center layout with proper spacing
- [ ] Description text visible

### **Test 9: Network Requests**

Open DevTools → Network tab

- [ ] See requests to Kong gateway (port 9000)
- [ ] Requests complete successfully (HTTP 200)
- [ ] Response times reasonable (< 1 second)
- [ ] No CORS errors

### **Test 10: Console Check**

Open DevTools (F12) → Console tab

- [ ] No red error messages
- [ ] No warnings related to UI components
- [ ] No "undefined" or type errors

---

## 📊 Monitoring Dashboard URLs

While testing, you can monitor backend services:

| Dashboard      | URL                    | Purpose                           |
| -------------- | ---------------------- | --------------------------------- |
| **Frontend**   | http://localhost:5173  | Application UI                    |
| **Kong Admin** | http://localhost:9001  | API Gateway config                |
| **Grafana**    | http://localhost:3001  | Services monitoring (admin:admin) |
| **Jaeger**     | http://localhost:16686 | Distributed tracing               |
| **Prometheus** | http://localhost:9091  | Metrics collection                |

---

## 🔧 Common Issues & Fixes

### **"Cannot connect to localhost:5173"**

```powershell
# 1. Check frontend is running
docker-compose ps frontend

# 2. Check logs
docker-compose logs frontend

# 3. Restart frontend
docker-compose restart frontend

# 4. Or start in dev mode instead:
cd frontend && npm run dev
```

### **"API calls failing (Kong errors)"**

```powershell
# 1. Check Kong is running
docker-compose ps kong

# 2. Test Kong directly
curl http://localhost:9000/api/health

# 3. Check Kong logs
docker-compose logs kong

# 4. Restart Kong
docker-compose restart kong
```

### **"Microservices returning 500 errors"**

```powershell
# Check specific service logs
docker-compose logs github-service    # Shows service errors
docker-compose logs pipeline-prediction-service

# Restart failing service
docker-compose restart github-service
```

### **"UI looks broken / styling not applied"**

```powershell
# Clear browser cache
# DevTools → Application → Clear Storage → Clear All

# Hard refresh
Ctrl + Shift + R  (Windows/Linux)
Cmd + Shift + R   (Mac)

# Or restart frontend
docker-compose restart frontend
```

### **"Hot-reload not working in dev mode"**

```powershell
# Stop dev server
Ctrl+C

# Clear and reinstall
cd frontend
rm -r node_modules
npm install

# Start again
npm run dev
```

---

## 📈 What to Look For (Success Indicators)

✅ **All Services Healthy**

```powershell
docker-compose ps
# All services show "Up" status
```

✅ **Frontend Loading**

```
HTTP 200 response from localhost:5173
Page renders without console errors
```

✅ **API Connectivity**

```
Network tab shows requests to Kong (9000)
Responses include repository/workflow data
No CORS or timeout errors
```

✅ **UI Components**

```
- Header buttons visible with icons
- Stats panel displays icon + value + label
- Loading state shows branded icon
- Error/empty states display correctly
- Dark/light mode toggle works
- Responsive layout adapts to screen size
```

---

## ⏱️ Timeline

| Step                  | Time        | Notes               |
| --------------------- | ----------- | ------------------- |
| Start Docker services | 30s         | Services initialize |
| Frontend starts       | 20s         | App compiles        |
| Page loads            | 3-5s        | Initial API calls   |
| **Total**             | **1-2 min** | Ready to test       |

---

## 🧪 Advanced Testing

### **Test Specific States**

```powershell
# Simulate slow network (DevTools)
F12 → Network → Throttling: "Slow 3G"
# Now reload - see loading state longer

# Simulate backend error
docker-compose stop github-service
# Now reload - see error state
docker-compose start github-service
# Click Retry - see recovery

# Test empty organization
# Access: /predictor with org that has no repos
```

### **Performance Testing**

```powershell
# DevTools → Lighthouse
# Run audit on predictor page
# Should score 90+ on performance

# Check memory
F12 → Memory → Take snapshot
# Should be < 50MB for initial page
```

### **Accessibility Testing**

```powershell
# Install axe DevTools extension
# Run scan on predictor page
# Should have 0 critical issues
```

---

## ✨ Final Sign-Off

When all checkboxes are complete, UI enhancement is **VALIDATED** ✅

Time to next phase:

- **Phase 5**: Advanced Monitoring & Drift Detection
- Or commit changes and deploy to production

---

## 📞 Quick Help

```powershell
# View all running services
docker-compose ps

# Real-time logs
docker-compose logs -f

# Restart everything
docker-compose restart

# Stop everything
docker-compose down

# Clean up (remove volumes)
docker-compose down -v

# Check specific service
docker-compose logs github-service

# Execute command in container
docker-compose exec frontend npm list

# Access container shell
docker-compose exec frontend sh
```

---

**Created**: April 10, 2026  
**For**: Pipeline Prediction Service UI Enhancement  
**Status**: Ready for Testing

# WebSocket Testing Script for WithOps Events Hub
# Tests real-time features: threat analysis notifications, GitHub events, collaboration

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  WebSocket Real-Time Features Testing" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$testsPassed = 0
$testsFailed = 0

# Test 1: Events Hub Health Check
Write-Host "`n[TEST 1] Events Hub Health Check" -ForegroundColor Cyan
Write-Host "  URL: http://localhost:9100/health" -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "http://localhost:9100/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "  PASS - Events Hub is running" -ForegroundColor Green
        $content = $response.Content | ConvertFrom-Json
        Write-Host "  Service: $($content.service)" -ForegroundColor Gray
        Write-Host "  Role: $($content.role)" -ForegroundColor Gray
        $testsPassed++
    } else {
        Write-Host "  FAIL - Unexpected status: $($response.StatusCode)" -ForegroundColor Red
        $testsFailed++
    }
} catch {
    Write-Host "  FAIL - Events Hub not accessible" -ForegroundColor Red
    $testsFailed++
}

# Test 2: Check WebSocket Endpoint Exists
Write-Host "`n[TEST 2] WebSocket Endpoint Check" -ForegroundColor Cyan
Write-Host "  Checking if /ws/{user_id} route is configured..." -ForegroundColor Gray

# We can't directly test WebSocket from PowerShell without special libraries,
# but we can check the service logs and configuration
Write-Host "  INFO: WebSocket endpoint should be at ws://localhost:9100/ws/{user_id}" -ForegroundColor Yellow
Write-Host "  MANUAL: Check browser console for WebSocket connections" -ForegroundColor Yellow

# Test 3: Check Redis Connection (Event Bus)
Write-Host "`n[TEST 3] Redis Event Bus Health" -ForegroundColor Cyan
Write-Host "  Testing Redis connection on port 16379..." -ForegroundColor Gray

try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("localhost", 16379)
    $tcpClient.Close()
    Write-Host "  PASS - Redis is accessible" -ForegroundColor Green
    $testsPassed++
} catch {
    Write-Host "  FAIL - Redis not accessible on port 16379" -ForegroundColor Red
    $testsFailed++
}

# Test 4: Check Event Bus Subscription
Write-Host "`n[TEST 4] Event Bus Subscription Check" -ForegroundColor Cyan
Write-Host "  Checking Events Hub logs for event subscriptions..." -ForegroundColor Gray

try {
    $logs = docker logs withops-events-hub --tail 50 2>&1
    
    $hasEventBus = $logs | Select-String -Pattern "Event bus connected|Event Bus|threat.analysis.completed"
    
    if ($hasEventBus) {
        Write-Host "  PASS - Event bus subscriptions detected in logs" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host "  WARN - No event bus subscriptions found in logs" -ForegroundColor Yellow
        Write-Host "  Check: docker logs withops-events-hub" -ForegroundColor Gray
    }
} catch {
    Write-Host "  WARN - Could not check logs (container may not be running)" -ForegroundColor Yellow
}

# Test 5: Frontend WebSocket Configuration
Write-Host "`n[TEST 5] Frontend WebSocket Configuration" -ForegroundColor Cyan
Write-Host "  Checking if frontend is configured to connect to port 9100..." -ForegroundColor Gray

try {
    $frontendFile = "frontend/src/routes/github/workspace/[org]/threat-modeling/[model_id]/+page.svelte"
    
    if (Test-Path $frontendFile) {
        $content = Get-Content $frontendFile -Raw
        
        if ($content -match "localhost:9100/ws" -or $content -match ":9100/ws") {
            Write-Host "  PASS - Frontend configured for port 9100" -ForegroundColor Green
            $testsPassed++
        } elseif ($content -match "localhost:9100/ws") {
            Write-Host "  FAIL - Frontend still using old port 9100" -ForegroundColor Red
            $testsFailed++
        } else {
            Write-Host "  WARN - Could not determine WebSocket port in frontend" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  WARN - Frontend file not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARN - Could not check frontend configuration" -ForegroundColor Yellow
}

# Test 6: Collaboration Service Check
Write-Host "`n[TEST 6] Collaboration Service (Y.js)" -ForegroundColor Cyan
Write-Host "  Testing collaboration service for real-time canvas updates..." -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8105/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "  PASS - Collaboration service is running" -ForegroundColor Green
        $testsPassed++
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode) {
        Write-Host "  WARN - Collaboration service returned: $statusCode" -ForegroundColor Yellow
    } else {
        Write-Host "  WARN - Collaboration service not accessible" -ForegroundColor Yellow
    }
}

# Test 7: Check Docker Container Status
Write-Host "`n[TEST 7] Events Hub Container Status" -ForegroundColor Cyan
Write-Host "  Checking Docker container health..." -ForegroundColor Gray

try {
    $container = docker ps --filter "name=withops-events-hub" --format "{{.Status}}" 2>$null
    
    if ($container -match "Up") {
        Write-Host "  PASS - Container is running: $container" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host "  FAIL - Container not running" -ForegroundColor Red
        $testsFailed++
    }
} catch {
    Write-Host "  WARN - Could not check container status" -ForegroundColor Yellow
}

# Manual Testing Instructions
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  MANUAL TESTING REQUIRED" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`nTo fully test WebSocket real-time features:" -ForegroundColor White
Write-Host ""
Write-Host "1. THREAT MODEL COLLABORATION:" -ForegroundColor Cyan
Write-Host "   - Open frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "   - Navigate to a threat model canvas" -ForegroundColor Gray
Write-Host "   - Open browser console (F12)" -ForegroundColor Gray
Write-Host "   - Look for: 'Connecting to WebSocket: ws://localhost:9100/ws/...'" -ForegroundColor Gray
Write-Host "   - Look for: 'WebSocket connected'" -ForegroundColor Green
Write-Host ""
Write-Host "2. ASYNC THREAT ANALYSIS:" -ForegroundColor Cyan
Write-Host "   - Trigger AI threat analysis on canvas" -ForegroundColor Gray
Write-Host "   - Check console for: 'Threat analysis completed' event" -ForegroundColor Gray
Write-Host "   - Verify real-time notification appears" -ForegroundColor Gray
Write-Host ""
Write-Host "3. GITHUB EVENT NOTIFICATIONS:" -ForegroundColor Cyan
Write-Host "   - Check Events Hub logs:" -ForegroundColor Gray
Write-Host "     docker logs withops-events-hub -f" -ForegroundColor White
Write-Host "   - Look for GitHub event subscriptions" -ForegroundColor Gray
Write-Host ""
Write-Host "4. COLLABORATION REAL-TIME SYNC:" -ForegroundColor Cyan
Write-Host "   - Open same threat model in two browser tabs" -ForegroundColor Gray
Write-Host "   - Make changes in one tab" -ForegroundColor Gray
Write-Host "   - Verify changes appear in other tab instantly" -ForegroundColor Gray
Write-Host ""

# Results Summary
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AUTOMATED TEST RESULTS" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

$total = $testsPassed + $testsFailed
Write-Host "`nTotal Automated Tests: $total" -ForegroundColor White
Write-Host "PASSED: $testsPassed" -ForegroundColor Green
Write-Host "FAILED: $testsFailed" -ForegroundColor Red

if ($testsPassed -gt 0) {
    $successRate = [math]::Round(($testsPassed / $total) * 100, 1)
    Write-Host "`nAutomated Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { 'Green' } else { 'Yellow' })
}

Write-Host "`nNOTE: WebSocket functionality requires manual browser testing" -ForegroundColor Yellow
Write-Host "      Follow the manual testing steps above for full validation" -ForegroundColor Yellow

Write-Host "`n============================================================`n" -ForegroundColor Cyan

if ($testsFailed -eq 0) { exit 0 } else { exit 1 }

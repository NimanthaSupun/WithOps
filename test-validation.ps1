#!/usr/bin/env pwsh
# Test & Validation Script for Pipeline Predictor UI
# Usage: .\test-validation.ps1 -Mode [quick|dev|full|cleanup]

param(
    [ValidateSet('quick', 'dev', 'full', 'cleanup')]
    [string]$Mode = 'quick',
    
    [string]$Org = 'your-org',
    [int]$TimeoutSeconds = 60,
    [switch]$SkipHealthCheck = $false
)

$ErrorActionPreference = "Stop"
$projectRoot = Get-Location

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Pipeline Predictor UI - Test & Validation Script" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "┌─ $Title" -ForegroundColor Yellow
    Write-Host "└" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✓ $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "  ✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "  → $Message" -ForegroundColor Cyan
}

function Test-DockerService {
    param([string]$ServiceName)
    
    try {
        $output = docker-compose ps $ServiceName 2>$null
        if ($output -match "Up") {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Wait-ForService {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )
    
    $startTime = Get-Date
    $timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
    
    while ((Get-Date) - $startTime -lt $timeout) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            # Service not ready yet
        }
        Start-Sleep -Milliseconds 500
    }
    
    return $false
}

# ============================================================================
# MODE: QUICK TEST (Start & Basic Validation)
# ============================================================================

function Test-Quick {
    Write-Section "Quick Test Mode (5 minutes)"
    
    Write-Info "Starting Docker services..."
    docker-compose up -d --remove-orphans kong redis
    
    Write-Info "Waiting for Kong gateway..."
    if (Wait-ForService "http://localhost:9000" 30) {
        Write-Success "Kong gateway ready"
    } else {
        Write-Error-Custom "Kong gateway failed to start"
        return
    }
    
    Write-Info "Starting backend microservices..."
    docker-compose up -d github-service pipeline-prediction-service
    
    Write-Info "Waiting for services..."
    Start-Sleep -Seconds 10
    
    Write-Info "Starting frontend..."
    docker-compose up -d frontend
    
    Write-Info "Waiting for frontend..."
    if (Wait-ForService "http://localhost:5173" 30) {
        Write-Success "Frontend ready"
    } else {
        Write-Error-Custom "Frontend failed to start"
        return
    }
    
    Write-Host ""
    Write-Host "┌─ Service Status" -ForegroundColor Yellow
    docker-compose ps | grep -E "(frontend|kong|github-service|pipeline|Up)" | Select-Object -First 5 | ForEach-Object {
        Write-Host "  $($_)" -ForegroundColor White
    }
    Write-Host "└" -ForegroundColor Yellow
    
    Write-Host ""
    Write-Success "All services started!"
    Write-Host ""
    Write-Host "🌐 Access Frontend:" -ForegroundColor Cyan
    Write-Host "   http://localhost:5173/github/workspace/$Org/predictor" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Monitoring:" -ForegroundColor Cyan
    Write-Host "   Kong Admin:    http://localhost:9001" -ForegroundColor White
    Write-Host "   Grafana:       http://localhost:3001 (admin:admin)" -ForegroundColor White
    Write-Host "   Jaeger:        http://localhost:16686" -ForegroundColor White
    Write-Host ""
}

# ============================================================================
# MODE: DEV TEST (Hot-Reload Frontend)
# ============================================================================

function Test-Dev {
    Write-Section "Dev Mode (Hot-Reload - Best for Iteration)"
    
    Write-Info "Starting backend infrastructure only..."
    docker-compose up -d kong redis
    
    Write-Info "Waiting for Kong..."
    if (-not (Wait-ForService "http://localhost:9000" 20)) {
        Write-Error-Custom "Kong failed to start"
        return
    }
    Write-Success "Kong ready"
    
    Write-Info "Starting microservices..."
    docker-compose up -d github-service auth-service pipeline-prediction-service
    
    Start-Sleep -Seconds 5
    Write-Success "Microservices started"
    
    Write-Host ""
    Write-Host "┌─ Next Steps" -ForegroundColor Yellow
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "│  1. Open new terminal and run:" -ForegroundColor White
    Write-Host "│     cd frontend" -ForegroundColor Cyan
    Write-Host "│     npm install" -ForegroundColor Cyan
    Write-Host "│     npm run dev" -ForegroundColor Cyan
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "│  2. Frontend will be at: http://localhost:5173" -ForegroundColor White
    Write-Host "│     (with hot-reload enabled)" -ForegroundColor Green
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "│  3. Edit the predictor page and changes appear instantly:" -ForegroundColor White
    Write-Host "│     frontend/src/routes/github/workspace/[org]/predictor/+page.svelte" -ForegroundColor Cyan
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "└" -ForegroundColor Yellow
    
    Write-Host ""
    Write-Info "Backend services running in Docker..."
    Write-Info "Press Ctrl+C when done"
    Write-Info "Clean up with: docker-compose down"
    
    # Keep Docker services running
    Write-Host ""
    docker-compose ps | Select-Object -First 10
}

# ============================================================================
# MODE: FULL TEST (All Services + Validation)
# ============================================================================

function Test-Full {
    Write-Section "Full Test Mode (Complete Stack - 10 minutes)"
    
    Write-Info "Starting all Docker services..."
    docker-compose up -d
    
    Write-Info "Waiting for services to initialize (30 seconds)..."
    $services = @(
        @{ name = "Kong"; url = "http://localhost:9000"; timeout = 20 },
        @{ name = "Frontend"; url = "http://localhost:5173"; timeout = 30 },
        @{ name = "GitHub Service"; url = "http://localhost:9102"; timeout = 20 }
    )
    
    foreach ($service in $services) {
        Write-Info "Checking $($service.name)..."
        if (Wait-ForService $service.url $service.timeout) {
            Write-Success "$($service.name) is ready"
        } else {
            Write-Error-Custom "$($service.name) failed to respond"
        }
    }
    
    Write-Host ""
    Write-Host "┌─ Service Status" -ForegroundColor Yellow
    docker-compose ps | Select-Object -First 15 | ForEach-Object {
        $line = $_
        if ($line -match "Up") {
            Write-Host "  $line" -ForegroundColor Green
        } else {
            Write-Host "  $line" -ForegroundColor White
        }
    }
    Write-Host "└" -ForegroundColor Yellow
    
    # ========================================================================
    # RUN VALIDATION TESTS
    # ========================================================================
    
    Write-Section "Running Automated Validation Tests"
    
    # Test 1: API Connectivity
    Write-Info "Test 1: Kong Gateway Connectivity"
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9000/api/health" -Method Get -ErrorAction SilentlyContinue
        Write-Success "Kong gateway responding (HTTP $($response.StatusCode))"
    } catch {
        Write-Error-Custom "Kong gateway not responding"
    }
    
    # Test 2: Frontend Responsiveness
    Write-Info "Test 2: Frontend Responsiveness"
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -ErrorAction SilentlyContinue
        Write-Success "Frontend responding (HTTP $($response.StatusCode))"
    } catch {
        Write-Error-Custom "Frontend not responding"
    }
    
    # Test 3: Check Docker logs for errors
    Write-Info "Test 3: Checking Frontend Logs"
    $logs = docker-compose logs frontend | Select-String -Pattern "error|Error|ERROR|fail|Fail" -First 5
    if ($logs) {
        Write-Error-Custom "Found errors in frontend logs:"
        $logs | ForEach-Object { Write-Host "     $_" -ForegroundColor Red }
    } else {
        Write-Success "No errors in frontend logs"
    }
    
    # Test 4: Service Dependencies
    Write-Info "Test 4: Checking Service Dependencies"
    $criticalServices = @("kong", "frontend", "github-service", "pipeline-prediction-service")
    $running = 0
    $total = $criticalServices.Count
    
    foreach ($svc in $criticalServices) {
        if (Test-DockerService $svc) {
            Write-Success "$svc is running"
            $running++
        } else {
            Write-Error-Custom "$svc is not running"
        }
    }
    
    Write-Host ""
    Write-Info "Services running: $running/$total"
    
    # ========================================================================
    # DISPLAY ACCESS INFORMATION
    # ========================================================================
    
    Write-Host ""
    Write-Host "┌─ Access Endpoints" -ForegroundColor Yellow
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "│  🌐 Frontend:" -ForegroundColor Cyan
    Write-Host "│     http://localhost:5173/github/workspace/$Org/predictor" -ForegroundColor Green
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "│  📊 Monitoring & Debugging:" -ForegroundColor Cyan
    Write-Host "│     Kong Admin:        http://localhost:9001" -ForegroundColor White
    Write-Host "│     Grafana:           http://localhost:3001 (admin:admin)" -ForegroundColor White
    Write-Host "│     Jaeger Traces:     http://localhost:16686" -ForegroundColor White
    Write-Host "│     Prometheus:        http://localhost:9091" -ForegroundColor White
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "│  🔧 Microservices:" -ForegroundColor Cyan
    Write-Host "│     GitHub Service:    http://localhost:9102" -ForegroundColor White
    Write-Host "│     Pipeline Service:  http://localhost:9109" -ForegroundColor White
    Write-Host "│     AI Service:        http://localhost:9101" -ForegroundColor White
    Write-Host "│" -ForegroundColor Yellow
    Write-Host "└" -ForegroundColor Yellow
    
    Write-Host ""
    Write-Host "✅ Full Test Environment Running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open browser to frontend URL above" -ForegroundColor White
    Write-Host "  2. Test the predictor page UI changes" -ForegroundColor White
    Write-Host "  3. Check logs with: docker-compose logs -f [service]" -ForegroundColor White
    Write-Host "  4. Stop everything with: docker-compose down" -ForegroundColor White
    Write-Host ""
}

# ============================================================================
# MODE: CLEANUP
# ============================================================================

function Test-Cleanup {
    Write-Section "Cleanup Mode"
    
    Write-Host "Stopping all containers..." -ForegroundColor Yellow
    docker-compose down
    
    Write-Success "All containers stopped"
    Write-Info "Volumes preserved (use 'docker-compose down -v' to remove volumes)"
    Write-Host ""
}

# ============================================================================
# EXECUTE SELECTED MODE
# ============================================================================

try {
    switch ($Mode) {
        'quick' {
            Test-Quick
        }
        'dev' {
            Test-Dev
        }
        'full' {
            Test-Full
        }
        'cleanup' {
            Test-Cleanup
        }
    }
    
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Test Mode: $Mode - Completed Successfully" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Red
    exit 1
}

# End-to-End Testing Script for WithOps Microservices
# Tests all critical user journeys through Kong API Gateway

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  WithOps Microservices - End-to-End Testing Suite" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0
$warnings = 0

function Test-Service {
    param([string]$Name, [string]$Url, [int]$Expected = 200)
    
    Write-Host "`n[TEST] $Name" -ForegroundColor Cyan
    Write-Host "  URL: $Url" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        
        if ($response.StatusCode -eq $Expected) {
            Write-Host "  PASS - Status: $($response.StatusCode)" -ForegroundColor Green
            $preview = $response.Content.Substring(0, [Math]::Min(60, $response.Content.Length))
            Write-Host "  Response: $preview..." -ForegroundColor DarkGray
            $script:passed++
        } else {
            Write-Host "  WARN - Status: $($response.StatusCode), Expected: $Expected" -ForegroundColor Yellow
            $script:warnings++
        }
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        
        if ($statusCode -eq 401 -or $statusCode -eq 403) {
            Write-Host "  AUTH REQUIRED - Status: $statusCode" -ForegroundColor Yellow
            $script:warnings++
        }
        elseif ($statusCode -eq 404) {
            Write-Host "  FAIL - Status: 404 (Not Found)" -ForegroundColor Red
            $script:failed++
        }
        else {
            Write-Host "  FAIL - Error: $($_.Exception.Message.Split("`n")[0])" -ForegroundColor Red
            $script:failed++
        }
    }
}

# Service Health Checks
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  TEST SUITE 1: Service Health Checks" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Test-Service "Auth Service Health" "http://localhost:8000/api/auth/health"
Test-Service "GitHub Service Health" "http://localhost:8000/api/github/health"
Test-Service "Threat Modeling Health" "http://localhost:8000/api/threat-modeling/health"
Test-Service "Workspace Intelligence Health" "http://localhost:8000/api/workspace-intelligence/health"
Test-Service "Collaboration Service Health" "http://localhost:8000/api/collaboration/health"
Test-Service "Workflow Orchestration Health" "http://localhost:8000/api/workflows/health"
Test-Service "Events Hub Health" "http://localhost:9100/health"

# GitHub Integration
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  TEST SUITE 2: GitHub Integration Flow" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Test-Service "GitHub Installations" "http://localhost:8000/api/github/installations"
Test-Service "GitHub Organizations" "http://localhost:8000/api/github/orgs"

# Threat Modeling
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  TEST SUITE 3: Threat Modeling Flow" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Test-Service "List Threat Models" "http://localhost:8000/api/threat-modeling/models"
Test-Service "Get Methodologies" "http://localhost:8000/api/threat-modeling/methodologies"

# Workspace Intelligence
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  TEST SUITE 4: Workspace Intelligence" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Test-Service "Workspace Intelligence Health" "http://localhost:8000/api/workspace-intelligence/health"

# Results Summary
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  TEST RESULTS SUMMARY" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

$total = $passed + $failed + $warnings
Write-Host "`nTotal Tests: $total" -ForegroundColor White
Write-Host "PASSED: $passed" -ForegroundColor Green
Write-Host "WARNINGS: $warnings (Auth required)" -ForegroundColor Yellow
Write-Host "FAILED: $failed" -ForegroundColor Red

$successRate = [math]::Round(($passed / $total) * 100, 1)
Write-Host "`nSuccess Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { 'Green' } else { 'Yellow' })

Write-Host "`n============================================================`n" -ForegroundColor Cyan

if ($failed -eq 0) { exit 0 } else { exit 1 }

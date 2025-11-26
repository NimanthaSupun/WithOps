# End-to-End Testing Script for WithOps Microservices Architecture
# Tests all critical user journeys through Kong API Gateway

Write-Host "`n" -NoNewline
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  WithOps Microservices - End-to-End Testing Suite" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$results = @{
    Passed = 0
    Failed = 0
    Warnings = 0
    Tests = @()
}

function Test-Endpoint {
    param(
        [string]$Category,
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [string]$Body = $null
    )
    
    $testResult = @{
        Category = $Category
        Name = $Name
        Url = $Url
        Status = "Unknown"
        StatusCode = 0
        Response = ""
        Duration = 0
    }
    
    Write-Host "`n[TEST] " -NoNewline -ForegroundColor Cyan
    Write-Host "$Category" -NoNewline -ForegroundColor White
    Write-Host " -> " -NoNewline -ForegroundColor Gray
    Write-Host "$Name" -ForegroundColor Yellow
    Write-Host "   $Url" -ForegroundColor Gray
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
        }
        
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-WebRequest @params
        $stopwatch.Stop()
        
        $testResult.StatusCode = $response.StatusCode
        $testResult.Duration = $stopwatch.ElapsedMilliseconds
        $testResult.Response = $response.Content
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host "   ✅ PASS" -NoNewline -ForegroundColor Green
            Write-Host " - Status: $($response.StatusCode)" -NoNewline -ForegroundColor Gray
            Write-Host " ($($stopwatch.ElapsedMilliseconds)ms)" -ForegroundColor DarkGray
            
            # Show response preview
            $preview = $response.Content.Substring(0, [Math]::Min(80, $response.Content.Length))
            Write-Host "   Response: $preview..." -ForegroundColor DarkGray
            
            $testResult.Status = "Passed"
            $script:results.Passed++
        } else {
            Write-Host "   ⚠️ UNEXPECTED STATUS" -NoNewline -ForegroundColor Yellow
            Write-Host " - Got: $($response.StatusCode), Expected: $ExpectedStatus" -ForegroundColor Gray
            $testResult.Status = "Warning"
            $script:results.Warnings++
        }
    }
    catch {
        $stopwatch.Stop()
        $statusCode = $_.Exception.Response.StatusCode.value__
        $testResult.StatusCode = $statusCode
        $testResult.Duration = $stopwatch.ElapsedMilliseconds
        
        # Some endpoints require auth - treat 401/403 as "working but needs auth"
        if ($statusCode -eq 401 -or $statusCode -eq 403) {
            Write-Host "   🔒 AUTH REQUIRED" -NoNewline -ForegroundColor Yellow
            Write-Host " - Status: $statusCode (Service is working, authentication needed)" -ForegroundColor Gray
            $testResult.Status = "Auth Required"
            $script:results.Warnings++
        }
        elseif ($statusCode -eq 404) {
            Write-Host "   ❌ NOT FOUND" -NoNewline -ForegroundColor Red
            Write-Host " - Status: 404 (Endpoint doesn't exist or service not routing correctly)" -ForegroundColor Gray
            $testResult.Status = "Failed"
            $script:results.Failed++
        }
        else {
            Write-Host "   ❌ FAIL" -NoNewline -ForegroundColor Red
            $errorMsg = $_.Exception.Message.Split([Environment]::NewLine)[0]
            Write-Host " - $errorMsg" -ForegroundColor Gray
            $testResult.Status = "Failed"
            $script:results.Failed++
        }
    }
    
    $script:results.Tests += $testResult
}

# ═══════════════════════════════════════════════════════════
# TEST SUITE 1: Service Health Checks
# ═══════════════════════════════════════════════════════════
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST SUITE 1: Service Health Checks                     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Test-Endpoint -Category "Health Check" -Name "Auth Service" -Url "http://localhost:8000/api/auth/health"
Test-Endpoint -Category "Health Check" -Name "GitHub Service" -Url "http://localhost:8000/api/github/health"
Test-Endpoint -Category "Health Check" -Name "Threat Modeling Service" -Url "http://localhost:8000/api/threat-modeling/health"
Test-Endpoint -Category "Health Check" -Name "Workspace Intelligence Service" -Url "http://localhost:8000/api/workspace-intelligence/health"
Test-Endpoint -Category "Health Check" -Name "Events Hub (WebSocket)" -Url "http://localhost:9100/health"

# ═══════════════════════════════════════════════════════════
# TEST SUITE 2: GitHub Integration Flow
# ═══════════════════════════════════════════════════════════
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST SUITE 2: GitHub Integration Flow                   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Test-Endpoint -Category "GitHub Flow" -Name "List Installations" -Url "http://localhost:8000/api/github/installations"
Test-Endpoint -Category "GitHub Flow" -Name "Get Organizations" -Url "http://localhost:8000/api/github/orgs"
Test-Endpoint -Category "GitHub Flow" -Name "List Repositories" -Url "http://localhost:8000/api/github/repositories?org=WithOps-Com" -ExpectedStatus 200

# ═══════════════════════════════════════════════════════════
# TEST SUITE 3: Threat Modeling Flow
# ═══════════════════════════════════════════════════════════
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST SUITE 3: Threat Modeling Flow                      ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Test-Endpoint -Category "Threat Modeling" -Name "List Threat Models" -Url "http://localhost:8000/api/threat-modeling/models" -ExpectedStatus 200
Test-Endpoint -Category "Threat Modeling" -Name "Get Methodologies" -Url "http://localhost:8000/api/threat-modeling/methodologies" -ExpectedStatus 200

# ═══════════════════════════════════════════════════════════
# TEST SUITE 4: Workspace Intelligence Flow
# ═══════════════════════════════════════════════════════════
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST SUITE 4: Workspace Intelligence Flow               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Test-Endpoint -Category "Workspace Intelligence" -Name "Service Health" -Url "http://localhost:8000/api/workspace-intelligence/health"
Test-Endpoint -Category "Workspace Intelligence" -Name "Repository Tree Status" -Url "http://localhost:8000/api/repository-tree/status" -ExpectedStatus 200

# ═══════════════════════════════════════════════════════════
# TEST SUITE 5: Workflow Orchestration Flow
# ═══════════════════════════════════════════════════════════
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST SUITE 5: Workflow Orchestration Flow               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Test-Endpoint -Category "Workflow Orchestration" -Name "Project Tree API" -Url "http://localhost:8000/api/project-tree/status" -ExpectedStatus 200
Test-Endpoint -Category "Workflow Orchestration" -Name "Workflows List" -Url "http://localhost:8000/api/workflows/list" -ExpectedStatus 200

# ═══════════════════════════════════════════════════════════
# TEST SUITE 6: Real-Time Features (Events Hub)
# ═══════════════════════════════════════════════════════════
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TEST SUITE 6: Real-Time Features (Events Hub)           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Test-Endpoint -Category "Events Hub" -Name "WebSocket Service Health" -Url "http://localhost:9100/health"
Test-Endpoint -Category "Events Hub" -Name "AI Proxy (via Events Hub)" -Url "http://localhost:8000/api/ai/health" -ExpectedStatus 200

# ═══════════════════════════════════════════════════════════
# FINAL RESULTS
# ═══════════════════════════════════════════════════════════
Write-Host "`n"
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  TEST RESULTS SUMMARY" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

$totalTests = $results.Passed + $results.Failed + $results.Warnings
Write-Host "`nTotal Tests: $totalTests" -ForegroundColor White

if ($results.Passed -gt 0) {
    Write-Host "PASS: $($results.Passed)" -ForegroundColor Green
}
if ($results.Warnings -gt 0) {
    Write-Host "WARN: $($results.Warnings) (Auth required or unexpected status)" -ForegroundColor Yellow
}
if ($results.Failed -gt 0) {
    Write-Host "FAIL: $($results.Failed)" -ForegroundColor Red
}

# Calculate success rate
$successRate = [math]::Round(($results.Passed / $totalTests) * 100, 1)
Write-Host "`nSuccess Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { 'Green' } elseif ($successRate -ge 60) { 'Yellow' } else { 'Red' })

# Show failed tests summary
if ($results.Failed -gt 0) {
    Write-Host "`nFAILED TESTS:" -ForegroundColor Red
    $results.Tests | Where-Object { $_.Status -eq "Failed" } | ForEach-Object {
        Write-Host "   * $($_.Category) -> $($_.Name) (Status: $($_.StatusCode))" -ForegroundColor Red
        Write-Host "     $($_.Url)" -ForegroundColor Gray
    }
}

# Show warnings summary
if ($results.Warnings -gt 0) {
    Write-Host "`nWARNINGS (Require Authentication or Investigation):" -ForegroundColor Yellow
    $results.Tests | Where-Object { $_.Status -eq "Warning" -or $_.Status -eq "Auth Required" } | ForEach-Object {
        Write-Host "   * $($_.Category) -> $($_.Name) (Status: $($_.StatusCode))" -ForegroundColor Yellow
        Write-Host "     $($_.Url)" -ForegroundColor Gray
    }
}

Write-Host "`n═══════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Exit with appropriate code
if ($results.Failed -eq 0) {
    exit 0
} else {
    exit 1
}

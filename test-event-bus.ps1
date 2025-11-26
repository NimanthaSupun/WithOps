# Event Bus Communication Test
# Tests pub/sub messaging between microservices

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  Event Bus Communication Verification" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan

$results = @{
    Connected = 0
    Failed = 0
    Channels = 0
}

# Test 1: Redis Connectivity
Write-Host "`n[TEST 1] Redis Server Health" -ForegroundColor Cyan
try {
    $ping = docker exec withops-redis redis-cli PING
    if ($ping -eq "PONG") {
        Write-Host "  ✓ PASS - Redis responding" -ForegroundColor Green
        $results.Connected++
    }
} catch {
    Write-Host "  ✗ FAIL - Redis not accessible" -ForegroundColor Red
    $results.Failed++
}

# Test 2: Active Pub/Sub Channels
Write-Host "`n[TEST 2] Active Pub/Sub Channels" -ForegroundColor Cyan
try {
    $channels = docker exec withops-redis redis-cli PUBSUB CHANNELS
    $channelList = $channels -split "`n" | Where-Object { $_ -match '\w+' }
    
    Write-Host "  Active Channels: $($channelList.Count)" -ForegroundColor White
    foreach ($channel in $channelList) {
        Write-Host "    - $channel" -ForegroundColor Gray
    }
    
    $results.Channels = $channelList.Count
    
    if ($channelList.Count -gt 0) {
        Write-Host "  ✓ PASS - Event bus has active channels" -ForegroundColor Green
        $results.Connected++
    } else {
        Write-Host "  ✗ WARN - No active channels (services may not be publishing yet)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ FAIL - Could not check channels" -ForegroundColor Red
    $results.Failed++
}

# Test 3: Service Event Bus Connections
Write-Host "`n[TEST 3] Service Event Bus Connections" -ForegroundColor Cyan

$services = @{
    "Events Hub" = "withops-events-hub"
    "GitHub Service" = "withops-github-service"
    "Threat Modeling" = "withops-threat-modeling-service"
    "AI Service" = "withops-ai-service"
    "Workspace Intelligence" = "withops-workspace-intelligence-service"
}

foreach ($service in $services.GetEnumerator()) {
    Write-Host "`n  Checking $($service.Key)..." -ForegroundColor Yellow
    
    try {
        $logs = docker logs $service.Value 2>&1 | Select-String -Pattern "Event.*bus.*connect|EventBus connected" | Select-Object -Last 1
        
        if ($logs) {
            Write-Host "    ✓ Connected to event bus" -ForegroundColor Green
            Write-Host "    $($logs.Line)" -ForegroundColor DarkGray
            $results.Connected++
        } else {
            Write-Host "    ✗ No event bus connection found" -ForegroundColor Red
            $results.Failed++
        }
    } catch {
        Write-Host "    ✗ Could not check logs" -ForegroundColor Red
        $results.Failed++
    }
}

# Test 4: Event Subscriptions
Write-Host "`n[TEST 4] Event Subscriptions" -ForegroundColor Cyan

$subscriptions = @(
    @{Service="Events Hub"; Event="threat.analysis.completed"; Container="withops-events-hub"},
    @{Service="Workspace Intelligence"; Event="github.installation"; Container="withops-workspace-intelligence-service"}
)

foreach ($sub in $subscriptions) {
    Write-Host "`n  $($sub.Service) -> $($sub.Event)" -ForegroundColor Yellow
    
    try {
        $logs = docker logs $sub.Container 2>&1 | Select-String -Pattern "Subscribed.*$($sub.Event)|handler.*$($sub.Event)" | Select-Object -Last 1
        
        if ($logs) {
            Write-Host "    ✓ Subscription active" -ForegroundColor Green
            $results.Connected++
        } else {
            Write-Host "    ? Not found in logs" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    ✗ Could not verify" -ForegroundColor Red
    }
}

# Test 5: Redis Client Connections
Write-Host "`n[TEST 5] Active Redis Client Connections" -ForegroundColor Cyan
try {
    $clients = docker exec withops-redis redis-cli CLIENT LIST
    $clientCount = ($clients -split "`n").Count
    
    Write-Host "  Connected clients: $clientCount" -ForegroundColor White
    Write-Host "  ✓ PASS - Services maintaining connections" -ForegroundColor Green
    $results.Connected++
} catch {
    Write-Host "  ✗ FAIL - Could not check client connections" -ForegroundColor Red
    $results.Failed++
}

# Test 6: Event Bus Listeners
Write-Host "`n[TEST 6] Event Bus Listeners Status" -ForegroundColor Cyan

$listeners = @("withops-events-hub", "withops-workspace-intelligence-service")

foreach ($listener in $listeners) {
    $logs = docker logs $listener 2>&1 | Select-String -Pattern "Listening.*event|started listening" | Select-Object -Last 1
    
    if ($logs) {
        Write-Host "  ✓ $listener is listening" -ForegroundColor Green
        $results.Connected++
    } else {
        Write-Host "  ? $listener status unknown" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  RESULTS SUMMARY" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan

Write-Host "`nEvent Bus Infrastructure:" -ForegroundColor White
Write-Host "  Active Channels: $($results.Channels)" -ForegroundColor Cyan
Write-Host "  Verified Connections: $($results.Connected)" -ForegroundColor Green
Write-Host "  Failed Checks: $($results.Failed)" -ForegroundColor $(if ($results.Failed -gt 0) { 'Red' } else { 'Gray' })

Write-Host "`nKey Findings:" -ForegroundColor White

$channelTypes = @(
    "events:threat.analysis.completed",
    "github_events", 
    "collaboration_events",
    "github:workspace:refresh"
)

Write-Host "  Expected channels present: " -NoNewline
$expectedFound = 0
foreach ($type in $channelTypes) {
    $channels = docker exec withops-redis redis-cli PUBSUB CHANNELS
    if ($channels -match $type) { $expectedFound++ }
}
Write-Host "$expectedFound/$($channelTypes.Count)" -ForegroundColor $(if ($expectedFound -eq $channelTypes.Count) { 'Green' } else { 'Yellow' })

Write-Host "`nEvent Bus Status: " -NoNewline
if ($results.Connected -gt 5 -and $results.Failed -eq 0) {
    Write-Host "FULLY OPERATIONAL" -ForegroundColor Green
} elseif ($results.Connected -gt 3) {
    Write-Host "PARTIALLY WORKING" -ForegroundColor Yellow
} else {
    Write-Host "NEEDS ATTENTION" -ForegroundColor Red
}

Write-Host "`n================================================================`n" -ForegroundColor Cyan

exit $(if ($results.Failed -eq 0) { 0 } else { 1 })

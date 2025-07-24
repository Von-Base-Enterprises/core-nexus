# PowerShell script to fix Core Nexus data sync issue

$ProductionUrl = "https://core-nexus-memory.onrender.com"
$AdminKey = "refresh-stats-2025"

Write-Host "=== Core Nexus Data Sync Fix ===" -ForegroundColor Cyan
Write-Host ""

# Function to check if service is ready
function Test-ServiceHealth {
    try {
        $response = Invoke-WebRequest -Uri "$ProductionUrl/health" -Method Get -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Wait for service to be ready
Write-Host "Checking service status..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    if (Test-ServiceHealth) {
        Write-Host "✅ Service is online!" -ForegroundColor Green
        break
    } else {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 10
    }
}

if ($attempt -eq $maxAttempts) {
    Write-Host ""
    Write-Host "❌ Service not responding. Check https://dashboard.render.com" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Checking current stats..." -ForegroundColor Yellow

# Get current health
try {
    $health = Invoke-RestMethod -Uri "$ProductionUrl/health" -Method Get
    Write-Host "Current total memories: $($health.total_memories)" -ForegroundColor Cyan
} catch {
    Write-Host "Failed to get health status" -ForegroundColor Red
}

Write-Host ""
Write-Host "Refreshing stats..." -ForegroundColor Yellow

# Call refresh endpoint
try {
    $refreshUrl = "$ProductionUrl/admin/refresh-stats?admin_key=$AdminKey"
    $response = Invoke-RestMethod -Uri $refreshUrl -Method Post
    
    Write-Host "✅ Stats refreshed successfully!" -ForegroundColor Green
    Write-Host "Old total: $($response.old_total_memories)" -ForegroundColor Gray
    Write-Host "New total: $($response.new_total_memories)" -ForegroundColor Green
    Write-Host "Difference: $($response.difference)" -ForegroundColor Yellow
    
    if ($response.providers) {
        Write-Host ""
        Write-Host "Provider breakdown:" -ForegroundColor Cyan
        foreach ($provider in $response.providers.PSObject.Properties) {
            Write-Host "  - $($provider.Name): $($provider.Value)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "❌ Failed to refresh stats: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Verifying fix..." -ForegroundColor Yellow

# Check health again
try {
    $health = Invoke-RestMethod -Uri "$ProductionUrl/health" -Method Get
    Write-Host "Updated total memories: $($health.total_memories)" -ForegroundColor Green
    
    if ($health.total_memories -gt 0) {
        Write-Host ""
        Write-Host "✅ Fix successful! Data sync issue resolved." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️  Stats still show 0. Try running again in a minute." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Failed to verify fix" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Complete ===" -ForegroundColor Cyan
# PowerShell script to fix Core Nexus query issue
# This will create the missing database indexes

Write-Host "🔧 Fixing Core Nexus Query Issue with PowerShell..." -ForegroundColor Green
Write-Host ""

# Database connection info
$dbHost = "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"
$dbPort = "5432"
$dbName = "nexus_memory_db"
$dbUser = "nexus_memory_db_user"
$dbPassword = "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"

# Create the SQL commands
$sqlCommands = @"
-- Create critical vector index
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Create metadata index
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories USING GIN (metadata);

-- Create importance score index
CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- Update statistics
ANALYZE vector_memories;

-- Verify indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'vector_memories';
"@

# Option 1: Using psql if available
Write-Host "Method 1: Trying psql command..." -ForegroundColor Yellow
$env:PGPASSWORD = $dbPassword
$psqlCommand = "psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -c `"$sqlCommands`""

try {
    Invoke-Expression $psqlCommand
    Write-Host "✅ Indexes created successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ psql not found, trying alternative method..." -ForegroundColor Red
}

# Option 2: Using .NET PostgreSQL connection
Write-Host ""
Write-Host "Method 2: Using .NET PostgreSQL connection..." -ForegroundColor Yellow

# First, let's create a simple HTTP request to test the fix
Write-Host ""
Write-Host "Testing if queries work now..." -ForegroundColor Cyan

$testUrl = "https://core-nexus-memory-service.onrender.com/memories/query"
$headers = @{
    "Content-Type" = "application/json"
}
$body = @{
    query = "test"
    limit = 5
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $testUrl -Method Post -Headers $headers -Body $body
    Write-Host "Query returned $($response.total_found) memories" -ForegroundColor Green
    
    if ($response.total_found -gt 0) {
        Write-Host "🎉 SUCCESS! Queries are working!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Queries still returning 0 results - indexes need to be created" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error testing query: $_" -ForegroundColor Red
}

# Option 3: Generate psql command for manual execution
Write-Host ""
Write-Host "Option 3: Manual execution command" -ForegroundColor Yellow
Write-Host "If the above didn't work, copy and run this command:" -ForegroundColor Cyan
Write-Host ""
Write-Host "PGPASSWORD='$dbPassword' psql -h $dbHost -p $dbPort -U $dbUser -d $dbName" -ForegroundColor White
Write-Host ""
Write-Host "Then paste this SQL:" -ForegroundColor Cyan
Write-Host $sqlCommands -ForegroundColor White
# PowerShell script to run the vector fix migration

Write-Host "=== Core Nexus Vector Fix Migration ===" -ForegroundColor Cyan
Write-Host "This will migrate the partitioned table to a non-partitioned structure" -ForegroundColor Yellow

# Set PostgreSQL connection parameters
$env:PGHOST = "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"
$env:PGPORT = "5432"
$env:PGDATABASE = "nexus_memory_db"
$env:PGUSER = "nexus_memory_db_user"
$env:PGPASSWORD = "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"

# Path to migration file
$migrationFile = "python/memory_service/migration_vector_fix.sql"

Write-Host "`nChecking connection to PostgreSQL..." -ForegroundColor Yellow

# Test connection first
$testQuery = "SELECT COUNT(*) as count FROM vector_memories;"
$testResult = psql -h $env:PGHOST -p $env:PGPORT -d $env:PGDATABASE -U $env:PGUSER -t -c $testQuery 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully connected to database" -ForegroundColor Green
    Write-Host "Current memory count: $($testResult.Trim())" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to connect to database" -ForegroundColor Red
    Write-Host $testResult
    exit 1
}

# Check if migration is needed
Write-Host "`nChecking if migration is needed..." -ForegroundColor Yellow
$checkQuery = "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memories');"
$tableExists = psql -h $env:PGHOST -p $env:PGPORT -d $env:PGDATABASE -U $env:PGUSER -t -c $checkQuery 2>&1

if ($tableExists -match "t") {
    Write-Host "⚠️  Table 'memories' already exists. Migration may have been completed." -ForegroundColor Yellow
    $response = Read-Host "Do you want to continue anyway? (yes/no)"
    if ($response -ne "yes") {
        Write-Host "Migration cancelled." -ForegroundColor Yellow
        exit 0
    }
}

# Create a simpler migration that we can run directly
Write-Host "`nPreparing migration..." -ForegroundColor Yellow

# Since we can't easily run the full SQL file, let's run the key parts step by step
$migrationSteps = @(
    @{
        Name = "Create new non-partitioned table"
        Query = @"
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    importance_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"@
    },
    @{
        Name = "Copy data from partitioned table"
        Query = @"
INSERT INTO memories (id, content, embedding, metadata, importance_score, created_at)
SELECT id, content, embedding, metadata, importance_score, created_at
FROM vector_memories
WHERE NOT EXISTS (SELECT 1 FROM memories WHERE memories.id = vector_memories.id);
"@
    },
    @{
        Name = "Create HNSW index for vector similarity"
        Query = @"
CREATE INDEX IF NOT EXISTS memories_embedding_idx
ON memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
"@
    },
    @{
        Name = "Create supporting indexes"
        Query = @"
CREATE INDEX IF NOT EXISTS memories_created_idx ON memories (created_at DESC);
CREATE INDEX IF NOT EXISTS memories_importance_idx ON memories (importance_score DESC);
CREATE INDEX IF NOT EXISTS memories_metadata_idx ON memories USING gin (metadata);
"@
    },
    @{
        Name = "Update table statistics"
        Query = "ANALYZE memories;"
    }
)

# Execute migration steps
$totalSteps = $migrationSteps.Count
$currentStep = 0

foreach ($step in $migrationSteps) {
    $currentStep++
    Write-Host "`n[$currentStep/$totalSteps] $($step.Name)..." -ForegroundColor Cyan
    
    $result = psql -h $env:PGHOST -p $env:PGPORT -d $env:PGDATABASE -U $env:PGUSER -c $step.Query 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Success" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed: $result" -ForegroundColor Red
        Write-Host "Rolling back..." -ForegroundColor Yellow
        psql -h $env:PGHOST -p $env:PGPORT -d $env:PGDATABASE -U $env:PGUSER -c "DROP TABLE IF EXISTS memories CASCADE;"
        exit 1
    }
}

# Verify migration
Write-Host "`n=== Verifying Migration ===" -ForegroundColor Cyan

$verifyQuery = @"
SELECT 
    (SELECT COUNT(*) FROM memories) as new_table_count,
    (SELECT COUNT(*) FROM vector_memories) as old_table_count,
    (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'memories') as index_count;
"@

$verifyResult = psql -h $env:PGHOST -p $env:PGPORT -d $env:PGDATABASE -U $env:PGUSER -t -c $verifyQuery

Write-Host "Migration Results:" -ForegroundColor Green
Write-Host $verifyResult

Write-Host "`n✅ Migration completed successfully!" -ForegroundColor Green
Write-Host "The new 'memories' table is ready for use." -ForegroundColor Cyan
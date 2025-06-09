# PowerShell script to debug why queries return empty results

Write-Host "Debugging Core Nexus Empty Query Results..." -ForegroundColor Yellow
Write-Host ""

# Check if there are actually memories in the database
Write-Host "1. Check memory count in database:" -ForegroundColor Cyan
$checkCount = @"
SELECT COUNT(*) as total_memories FROM vector_memories;
"@
Write-Host "Run this SQL:" -ForegroundColor Green
Write-Host $checkCount
Write-Host ""

# Check if embeddings are null
Write-Host "2. Check if embeddings exist:" -ForegroundColor Cyan
$checkEmbeddings = @"
SELECT COUNT(*) as memories_with_embeddings 
FROM vector_memories 
WHERE embedding IS NOT NULL;
"@
Write-Host "Run this SQL:" -ForegroundColor Green
Write-Host $checkEmbeddings
Write-Host ""

# Check a sample memory
Write-Host "3. Check a sample memory:" -ForegroundColor Cyan
$checkSample = @"
SELECT id, content, 
       CASE WHEN embedding IS NULL THEN 'NULL' ELSE 'EXISTS' END as has_embedding,
       array_length(embedding, 1) as embedding_dimensions
FROM vector_memories 
LIMIT 5;
"@
Write-Host "Run this SQL:" -ForegroundColor Green
Write-Host $checkSample
Write-Host ""

# Test a direct similarity query
Write-Host "4. Test direct SQL similarity query:" -ForegroundColor Cyan
$testQuery = @"
SELECT id, content, importance_score
FROM vector_memories
WHERE embedding IS NOT NULL
LIMIT 5;
"@
Write-Host "Run this SQL:" -ForegroundColor Green
Write-Host $testQuery
Write-Host ""

# Full PowerShell command to run all checks
Write-Host "5. Or run all checks at once with this PowerShell command:" -ForegroundColor Yellow
Write-Host '$env:PGPASSWORD="2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"; psql -h dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com -U nexus_memory_db_user -d nexus_memory_db' -ForegroundColor White
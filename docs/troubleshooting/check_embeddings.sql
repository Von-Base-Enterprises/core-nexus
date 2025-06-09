-- Check why queries return empty results

-- 1. Total memories and embedding status
SELECT 
    COUNT(*) as total_memories,
    COUNT(embedding) as memories_with_embeddings,
    COUNT(*) - COUNT(embedding) as missing_embeddings
FROM vector_memories;

-- 2. Check embedding dimensions
SELECT 
    array_length(embedding, 1) as dimensions,
    COUNT(*) as count
FROM vector_memories
WHERE embedding IS NOT NULL
GROUP BY array_length(embedding, 1);

-- 3. Sample of memories to see what's stored
SELECT 
    id,
    LEFT(content, 50) as content_preview,
    CASE WHEN embedding IS NULL THEN 'NULL' ELSE 'EXISTS' END as has_embedding,
    created_at
FROM vector_memories
ORDER BY created_at DESC
LIMIT 10;

-- 4. Test if any memories would match a simple query
SELECT COUNT(*)
FROM vector_memories
WHERE embedding IS NOT NULL
AND content ILIKE '%test%';

-- 5. Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'vector_memories';
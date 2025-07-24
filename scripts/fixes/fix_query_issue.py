#!/usr/bin/env python3
"""
Fix the query issue by updating the emergency search implementation.
The issue is that emergency_search_all returns 0 memories despite the table having 1096.
"""

# Read the current search_fix.py
with open('src/memory_service/search_fix.py', 'r') as f:
    content = f.read()

# The issue might be with the SQL query. Let's check if we need to handle NULL embeddings differently
# or if there's a permission issue with the table

# Update the emergency_search_all method to be more robust
updated_content = content.replace(
    """                rows = await conn.fetch(f\"\"\"
                    SELECT 
                        id, 
                        content, 
                        metadata, 
                        importance_score,
                        created_at
                    FROM {self.table_name}
                    ORDER BY created_at DESC
                    LIMIT $1
                \"\"\", limit)""",
    """                # First, let's check what tables exist
                table_check = await conn.fetchval(f\"\"\"
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_name = '{self.table_name}'
                \"\"\")
                
                if table_check == 0:
                    logger.error(f"Table {self.table_name} does not exist!")
                    # Try alternative table names
                    for alt_table in ['memories', 'memory_vectors', 'vectors']:
                        alt_check = await conn.fetchval(f\"\"\"
                            SELECT COUNT(*) 
                            FROM information_schema.tables 
                            WHERE table_name = '{alt_table}'
                        \"\"\")
                        if alt_check > 0:
                            logger.info(f"Found alternative table: {alt_table}")
                            self.table_name = alt_table
                            break
                
                # Get total count first
                total_count = await conn.fetchval(f"SELECT COUNT(*) FROM {self.table_name}")
                logger.info(f"Total memories in {self.table_name}: {total_count}")
                
                # Now fetch the actual rows
                rows = await conn.fetch(f\"\"\"
                    SELECT 
                        id, 
                        content, 
                        metadata, 
                        importance_score,
                        created_at
                    FROM {self.table_name}
                    WHERE content IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT $1
                \"\"\", limit)""")

# Also fix the ensure_all_memories_visible method
updated_content = updated_content.replace(
    """            async with self.connection_pool.acquire() as conn:
                # Get diagnostic information
                total_count = await conn.fetchval(f"SELECT COUNT(*) FROM {self.table_name}")""",
    """            async with self.connection_pool.acquire() as conn:
                # Check if table exists
                table_exists = await conn.fetchval(f\"\"\"
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{self.table_name}'
                    )
                \"\"\")
                
                if not table_exists:
                    logger.error(f"Table {self.table_name} does not exist!")
                    return {
                        'error': f'Table {self.table_name} not found',
                        'total_memories': 0,
                        'with_embeddings': 0,
                        'without_embeddings': 0
                    }
                
                # Get diagnostic information
                total_count = await conn.fetchval(f"SELECT COUNT(*) FROM {self.table_name}")""")

# Write the updated file
with open('src/memory_service/search_fix.py', 'w') as f:
    f.write(updated_content)

print("✅ Updated search_fix.py with better error handling and table detection")
print("\nChanges made:")
print("1. Added table existence check")
print("2. Added fallback to alternative table names")
print("3. Added WHERE content IS NOT NULL clause")
print("4. Added logging for debugging")
print("\nNext: Deploy these changes to fix the query issue")
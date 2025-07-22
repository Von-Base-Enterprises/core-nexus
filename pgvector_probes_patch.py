#!/usr/bin/env python3
"""
Patch to add optimal probes setting to pgvector provider.

This updates the providers.py file to automatically set ivfflat.probes = 3
for optimal query performance.
"""

import os
import re


def create_patch():
    """Create patch for providers.py to add probes setting."""
    
    patch_content = """
--- a/python/memory_service/src/memory_service/providers.py
+++ b/python/memory_service/src/memory_service/providers.py
@@ -374,6 +374,9 @@ class PgVectorProvider(BaseMemoryProvider):
             return []
             
         async with self.connection_pool.acquire() as conn:
+            # Set optimal probes for IVFFlat index (based on lists=8)
+            await conn.execute("SET ivfflat.probes = 3")
+            
             # Build query with filters
             where_clauses = []
             params = []
"""
    
    # Save patch file
    with open('add_probes_setting.patch', 'w') as f:
        f.write(patch_content)
    
    print("✅ Patch created: add_probes_setting.patch")
    print("\nTo apply the patch:")
    print("1. cd python/memory_service")
    print("2. git apply ../../add_probes_setting.patch")
    print("\nOr manually add this line after line 374 in providers.py:")
    print('    await conn.execute("SET ivfflat.probes = 3")')
    
    # Also create the direct edit for immediate application
    providers_update = """
# Add this line in the query method after acquiring the connection (line ~375):
await conn.execute("SET ivfflat.probes = 3")

# Full context - add after this line:
async with self.connection_pool.acquire() as conn:
    # Set optimal probes for IVFFlat index (based on lists=8)
    await conn.execute("SET ivfflat.probes = 3")
    
    # Build query with filters
    ...
"""
    
    with open('providers_probes_update.txt', 'w') as f:
        f.write(providers_update)
    
    print("\n📄 Manual update instructions saved to: providers_probes_update.txt")


if __name__ == "__main__":
    create_patch()
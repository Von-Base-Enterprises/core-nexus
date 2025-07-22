#!/usr/bin/env python3
"""
Proper fix for probes setting in pgvector.

The issue: SET ivfflat.probes is a session-level setting, but with connection
pooling, each query might get a different connection. We need to ensure it's
set for all connections in the pool.
"""

def generate_proper_fix():
    """Generate the proper fix for providers.py"""
    
    fix_code = '''
# The proper way to fix this is to set probes when initializing each connection
# in the pool. Here's the updated code for providers.py:

# In the __init__ method where we create the pool, add a setup function:

self.connection_pool = await asyncpg.create_pool(
    conn_str,
    min_size=5,
    max_size=20,
    command_timeout=60,
    setup=self._setup_connection  # Add this line
)

# Then add this method to the PgVectorProvider class:

async def _setup_connection(self, conn):
    """Setup function called for each new connection in the pool."""
    try:
        # Set optimal probes for all connections
        await conn.execute("SET ivfflat.probes = 3")
        logger.info("Set ivfflat.probes = 3 for new connection")
    except Exception as e:
        # Log but don't fail - connection will still work with default probes
        logger.warning(f"Could not set ivfflat.probes: {e}")

# Alternative approach if setup doesn't work:
# Set it at the beginning of each query method, but check if already set:

async def query(self, query_embedding: List[float], limit: int, filters: Dict[str, Any]) -> List[MemoryResponse]:
    """Query PostgreSQL for similar vectors."""
    if not self.connection_pool:
        return []
        
    async with self.connection_pool.acquire() as conn:
        # Ensure probes is set for this connection
        try:
            current_probes = await conn.fetchval("SHOW ivfflat.probes")
            if int(current_probes) != 3:
                await conn.execute("SET ivfflat.probes = 3")
                logger.debug("Set probes=3 for query")
        except Exception as e:
            # First time setting or not supported
            try:
                await conn.execute("SET ivfflat.probes = 3")
            except:
                pass  # Continue with default
        
        # Rest of query logic...
'''
    
    return fix_code

def generate_immediate_workaround():
    """Generate an immediate workaround we can apply"""
    
    workaround = '''#!/usr/bin/env python3
"""
Immediate workaround: Set probes globally in PostgreSQL.

This script sets ivfflat.probes at the database level so all connections
use the optimized value by default.
"""

import asyncio
import asyncpg

async def set_probes_globally():
    db_url = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )
    
    print("🔧 Setting probes globally in PostgreSQL...")
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # Try to set it at database level
        try:
            # This would require superuser privileges
            await conn.execute("ALTER DATABASE nexus_memory_db SET ivfflat.probes = 3")
            print("✅ Set probes=3 at database level")
        except Exception as e:
            print(f"❌ Cannot set at database level: {e}")
            
            # Try role level
            try:
                await conn.execute("ALTER ROLE nexus_memory_db_user SET ivfflat.probes = 3")
                print("✅ Set probes=3 for user role")
            except Exception as e2:
                print(f"❌ Cannot set at role level: {e2}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(set_probes_globally())
'''
    
    return workaround


def main():
    print("🔍 Analysis: Why probes setting isn't working\n")
    
    print("The issue is that `SET ivfflat.probes` is a SESSION-level setting.")
    print("With connection pooling, each query might get a different connection,")
    print("so setting it once per query doesn't persist.\n")
    
    print("Solutions:")
    print("1. Set probes in the connection pool setup function")
    print("2. Set it globally at database/role level")
    print("3. Check and set it for each query (inefficient)\n")
    
    # Generate fix code
    fix_code = generate_proper_fix()
    with open('providers_pool_fix.py', 'w') as f:
        f.write(fix_code)
    print("✅ Generated proper fix: providers_pool_fix.py")
    
    # Generate workaround
    workaround = generate_immediate_workaround()
    with open('set_probes_globally.py', 'w') as f:
        f.write(workaround)
    print("✅ Generated workaround: set_probes_globally.py")
    
    print("\nNext steps:")
    print("1. Try the global setting workaround first")
    print("2. If that works, update providers.py with the pool setup fix")
    print("3. Also fix the lists parameter from 100 to 8!")


if __name__ == "__main__":
    main()
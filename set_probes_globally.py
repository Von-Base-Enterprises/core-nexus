#!/usr/bin/env python3
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

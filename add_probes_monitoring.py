#!/usr/bin/env python3
"""
Script to add probes monitoring to the health check endpoint.

This will help detect configuration drift in production.
"""

import asyncio
import asyncpg
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_health_check_patch():
    """Generate the code to add to the health check endpoint."""
    
    patch_code = '''
# Add this to the health check endpoint in api.py

# In the /health endpoint handler, add pgvector configuration check:

# Check pgvector configuration
pgvector_config = {}
try:
    # Get pgvector probes setting
    for provider in store.providers:
        if provider.name == "pgvector" and provider.enabled:
            async with provider.connection_pool.acquire() as conn:
                try:
                    current_probes = await conn.fetchval("SHOW ivfflat.probes")
                    pgvector_config["probes"] = int(current_probes)
                except Exception as e:
                    pgvector_config["probes"] = "unknown"
                    pgvector_config["probes_error"] = str(e)
                
                # Get index information
                index_info = await conn.fetch("""
                    SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                    FROM pg_indexes 
                    WHERE tablename = 'vector_memories'
                    AND indexname LIKE '%embedding%'
                    LIMIT 1
                """)
                
                if index_info:
                    pgvector_config["index_name"] = index_info[0]['indexname']
                    pgvector_config["index_size"] = index_info[0]['size']
                
                # Get lists parameter from index definition
                index_def = await conn.fetchval("""
                    SELECT indexdef 
                    FROM pg_indexes 
                    WHERE tablename = 'vector_memories'
                    AND indexname LIKE '%embedding%'
                    AND indexdef LIKE '%ivfflat%'
                    LIMIT 1
                """)
                
                if index_def:
                    import re
                    lists_match = re.search(r'lists = (\d+)', index_def)
                    if lists_match:
                        pgvector_config["lists"] = int(lists_match.group(1))
                
                break
except Exception as e:
    logger.error(f"Error checking pgvector config: {e}")
    pgvector_config["error"] = str(e)

# Add to health response
health_response["pgvector_config"] = pgvector_config

# Add configuration warnings
config_warnings = []
if pgvector_config.get("probes", 1) != 3:
    config_warnings.append(f"Probes is {pgvector_config.get('probes', 'unknown')}, should be 3")

if pgvector_config.get("lists", 0) > 10:
    config_warnings.append(f"Lists parameter ({pgvector_config.get('lists', 'unknown')}) may be too high for dataset size")

if config_warnings:
    health_response["configuration_warnings"] = config_warnings
'''
    
    return patch_code


async def test_pgvector_monitoring():
    """Test the pgvector monitoring locally."""
    db_url = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )
    
    logger.info("Testing pgvector monitoring...")
    
    try:
        conn = await asyncpg.connect(db_url)
        
        pgvector_config = {}
        
        # Get probes setting
        try:
            current_probes = await conn.fetchval("SHOW ivfflat.probes")
            pgvector_config["probes"] = int(current_probes)
        except Exception as e:
            pgvector_config["probes"] = "unknown"
            pgvector_config["probes_error"] = str(e)
        
        # Get index information
        index_info = await conn.fetch("""
            SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
            AND indexname LIKE '%embedding%'
            LIMIT 1
        """)
        
        if index_info:
            pgvector_config["index_name"] = index_info[0]['indexname']
            pgvector_config["index_size"] = index_info[0]['size']
        
        # Get lists parameter
        index_def = await conn.fetchval("""
            SELECT indexdef 
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
            AND indexname LIKE '%embedding%'
            AND indexdef LIKE '%ivfflat%'
            LIMIT 1
        """)
        
        if index_def:
            import re
            lists_match = re.search(r'lists = (\d+)', index_def)
            if lists_match:
                pgvector_config["lists"] = int(lists_match.group(1))
        
        # Get memory count
        total_memories = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        pgvector_config["total_memories"] = total_memories
        
        await conn.close()
        
        # Print results
        logger.info(f"\nPgvector Configuration:")
        logger.info(f"  Probes: {pgvector_config.get('probes', 'unknown')}")
        logger.info(f"  Lists: {pgvector_config.get('lists', 'unknown')}")
        logger.info(f"  Index: {pgvector_config.get('index_name', 'unknown')}")
        logger.info(f"  Index Size: {pgvector_config.get('index_size', 'unknown')}")
        logger.info(f"  Total Memories: {pgvector_config.get('total_memories', 0):,}")
        
        # Check for issues
        issues = []
        if pgvector_config.get("probes", 1) != 3:
            issues.append(f"Probes is {pgvector_config.get('probes', 'unknown')}, should be 3")
        
        optimal_lists = max(8, pgvector_config.get('total_memories', 0) // 1000)
        if pgvector_config.get("lists", 0) > optimal_lists * 2:
            issues.append(f"Lists parameter ({pgvector_config.get('lists', 'unknown')}) may be too high")
        
        if issues:
            logger.warning("\n⚠️ Configuration Issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        else:
            logger.info("\n✅ Configuration looks good!")
        
        return pgvector_config
        
    except Exception as e:
        logger.error(f"Error testing pgvector monitoring: {e}")
        return None


def main():
    """Generate monitoring code and test it."""
    logger.info("🔍 Pgvector Monitoring Setup")
    logger.info("=" * 60)
    
    # Generate patch code
    patch_code = generate_health_check_patch()
    
    # Save to file
    with open('health_check_pgvector_patch.py', 'w') as f:
        f.write(patch_code)
    
    logger.info("✅ Generated health check patch code")
    logger.info("📄 Saved to: health_check_pgvector_patch.py")
    
    # Test monitoring
    logger.info("\n🧪 Testing pgvector monitoring...")
    config = asyncio.run(test_pgvector_monitoring())
    
    if config:
        # Save test results
        with open('pgvector_monitoring_test.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("\n📊 Test results saved to: pgvector_monitoring_test.json")


if __name__ == "__main__":
    main()
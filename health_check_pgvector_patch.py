
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


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

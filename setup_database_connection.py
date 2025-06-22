#!/usr/bin/env python3
"""
Database Connection Setup for Phase 2 Testing

Helps establish database connectivity for performance optimization testing.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the memory service to the path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

def setup_environment():
    """Setup environment variables for database connection."""
    print("=== DATABASE CONNECTION SETUP ===")
    
    # Import config to see defaults
    try:
        from memory_service.config import DatabaseConfig
        print("\nCurrent Configuration:")
        print(f"  Host: {DatabaseConfig.HOST}")
        print(f"  Port: {DatabaseConfig.PORT}")
        print(f"  Database: {DatabaseConfig.DATABASE}")
        print(f"  User: {DatabaseConfig.USER}")
        print(f"  Password: {'SET' if DatabaseConfig.PASSWORD else 'NOT SET'}")
    except Exception as e:
        print(f"Failed to import config: {e}")
        return False
    
    # Check if this is production database (Render)
    if "dpg-" in DatabaseConfig.HOST and "render.com" in DatabaseConfig.HOST:
        print("\n🏭 PRODUCTION DATABASE DETECTED")
        print("This appears to be the Render.com production database.")
        print("You'll need the production database password.")
        print("\nTo set the password:")
        print("  export PGVECTOR_PASSWORD='your_production_password_here'")
        print("  # OR")
        print("  export PGPASSWORD='your_production_password_here'")
        
        # Check for common environment files
        env_files = [
            ".env",
            "python/memory_service/.env", 
            "../.env"
        ]
        
        for env_file in env_files:
            if os.path.exists(env_file):
                print(f"\nFound environment file: {env_file}")
                print("Consider loading it with: source {env_file}")
        
        return False
    
    # If not production, try to set up development environment
    print("\n🧪 DEVELOPMENT SETUP")
    print("Setting up development database connection...")
    
    # You could set development defaults here if needed
    return True

async def test_connection_with_current_setup():
    """Test database connection with current environment."""
    print("\n=== CONNECTION TEST ===")
    
    try:
        from memory_service.config import DatabaseConfig
        
        if not DatabaseConfig.PASSWORD:
            print("❌ No database password configured")
            print("\nOptions:")
            print("1. Set PGVECTOR_PASSWORD environment variable")
            print("2. Set PGPASSWORD environment variable") 
            print("3. Create .env file with database credentials")
            return False
        
        import asyncpg
        
        conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
        print(f"Testing connection to: {DatabaseConfig.USER}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}")
        
        try:
            conn = await asyncpg.connect(conn_str, command_timeout=10)
            
            # Basic connectivity test
            version = await conn.fetchval("SELECT version()")
            print(f"✅ Connected! PostgreSQL: {version[:50]}...")
            
            # Test vector extension
            vector_ext = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            print(f"✅ Vector extension: {vector_ext or 'Not installed'}")
            
            # Test access to vector_memories table
            try:
                count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
                size = await conn.fetchval("SELECT pg_size_pretty(pg_total_relation_size('vector_memories'))")
                print(f"✅ vector_memories table: {count} records, {size}")
                
                # Quick performance test
                import time
                start_time = time.time()
                test_vector = [0.1] * 1536
                
                rows = await conn.fetch("""
                    SELECT id, embedding <=> $1::vector as distance
                    FROM vector_memories
                    ORDER BY embedding <=> $1::vector
                    LIMIT 5
                """, test_vector)
                
                query_time = (time.time() - start_time) * 1000
                print(f"✅ Sample vector query: {len(rows)} results in {query_time:.1f}ms")
                
                print(f"\n🎯 CURRENT BASELINE: {query_time:.1f}ms")
                print(f"🎯 OPTIMIZATION TARGET: <20ms")
                if query_time > 20:
                    improvement = ((query_time - 20) / query_time) * 100
                    print(f"🎯 POTENTIAL IMPROVEMENT: {improvement:.1f}%")
                else:
                    print(f"🎯 ALREADY OPTIMIZED!")
                
                await conn.close()
                return True
                
            except Exception as e:
                print(f"⚠️  Table access issue: {e}")
                await conn.close()
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def show_next_steps(connection_successful):
    """Show next steps based on connection test results."""
    print("\n=== NEXT STEPS ===")
    
    if connection_successful:
        print("✅ Database connection successful!")
        print("\nYou can now proceed with Phase 2 testing:")
        print("1. Run the Stage 1 test again: python3 stage1_environment_test.py")
        print("2. Proceed to Stage 2: PostgreSQL configuration optimization")
        print("3. Continue with the systematic optimization pipeline")
    else:
        print("❌ Database connection not yet established.")
        print("\nTo proceed, you need to:")
        print("1. Set the database password environment variable:")
        print("   export PGVECTOR_PASSWORD='your_password'")
        print("2. Or create a .env file with database credentials")
        print("3. Or contact the team for production database access")
        print("\nFor development/testing, you could also:")
        print("1. Set up a local PostgreSQL with pgvector extension")
        print("2. Use Docker to run a test database")
        print("3. Update config to point to a development database")

async def main():
    """Main setup and testing function."""
    print("Core Nexus - Database Connection Setup for Phase 2 Testing")
    print("=" * 60)
    
    # Setup environment
    setup_successful = setup_environment()
    
    # Test connection with current setup
    connection_successful = await test_connection_with_current_setup()
    
    # Show next steps
    show_next_steps(connection_successful)
    
    return connection_successful

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
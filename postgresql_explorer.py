#!/usr/bin/env python3
"""
PostgreSQL Database Explorer for Render Instance
A replacement for psql when command-line tools aren't available
"""

import asyncio
import asyncpg
import json
from typing import List, Dict, Any


class PostgreSQLExplorer:
    def __init__(self):
        # Production settings from configuration
        self.host = "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"
        self.port = 5432
        self.database = "nexus_memory_db"
        self.user = "nexus_memory_db_user"
        self.password = "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
        self.conn = None

    async def connect(self):
        """Establish connection to PostgreSQL"""
        try:
            self.conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                timeout=10
            )
            print("✓ Connected to PostgreSQL database")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Close connection"""
        if self.conn:
            await self.conn.close()
            print("✓ Disconnected from database")

    async def list_tables(self):
        """List all tables in the database"""
        print("\n=== TABLES ===")
        query = """
            SELECT schemaname, tablename, tableowner 
            FROM pg_tables 
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
            ORDER BY schemaname, tablename;
        """
        
        try:
            rows = await self.conn.fetch(query)
            for row in rows:
                print(f"  {row['schemaname']}.{row['tablename']} (owner: {row['tableowner']})")
            print(f"\nTotal tables: {len(rows)}")
        except Exception as e:
            print(f"Error listing tables: {e}")

    async def list_extensions(self):
        """List installed PostgreSQL extensions"""
        print("\n=== EXTENSIONS ===")
        query = "SELECT name, default_version, installed_version FROM pg_available_extensions WHERE installed_version IS NOT NULL ORDER BY name;"
        
        try:
            rows = await self.conn.fetch(query)
            for row in rows:
                print(f"  {row['name']} (v{row['installed_version']})")
            print(f"\nTotal extensions: {len(rows)}")
        except Exception as e:
            print(f"Error listing extensions: {e}")

    async def describe_table(self, table_name: str):
        """Describe a table's structure"""
        print(f"\n=== TABLE STRUCTURE: {table_name} ===")
        
        # Get column information
        query = """
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = $1 
            ORDER BY ordinal_position;
        """
        
        try:
            rows = await self.conn.fetch(query, table_name)
            for row in rows:
                nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {row['column_default']}" if row['column_default'] else ""
                length = f"({row['character_maximum_length']})" if row['character_maximum_length'] else ""
                print(f"  {row['column_name']}: {row['data_type']}{length} {nullable}{default}")
        except Exception as e:
            print(f"Error describing table: {e}")

    async def list_indexes(self, table_name: str):
        """List indexes for a table"""
        print(f"\n=== INDEXES: {table_name} ===")
        query = """
            SELECT 
                indexname, 
                indexdef
            FROM pg_indexes 
            WHERE tablename = $1;
        """
        
        try:
            rows = await self.conn.fetch(query, table_name)
            for row in rows:
                print(f"  {row['indexname']}:")
                print(f"    {row['indexdef']}")
        except Exception as e:
            print(f"Error listing indexes: {e}")

    async def table_stats(self, table_name: str):
        """Get basic statistics for a table"""
        print(f"\n=== TABLE STATS: {table_name} ===")
        
        try:
            # Row count
            count = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"  Total rows: {count:,}")
            
            # Table size
            size_query = "SELECT pg_size_pretty(pg_total_relation_size($1)) as size"
            size = await self.conn.fetchval(size_query, table_name)
            print(f"  Table size: {size}")
            
        except Exception as e:
            print(f"Error getting table stats: {e}")

    async def test_vector_operations(self):
        """Test pgvector operations"""
        print("\n=== VECTOR OPERATIONS TEST ===")
        
        try:
            # Test if we can query vector_memories
            query = """
                SELECT id, content, 
                       importance_score,
                       created_at,
                       CASE WHEN embedding IS NOT NULL THEN 'YES' ELSE 'NO' END as has_embedding
                FROM vector_memories 
                ORDER BY created_at DESC
                LIMIT 5;
            """
            
            rows = await self.conn.fetch(query)
            print(f"Sample vector memories ({len(rows)} shown):")
            for row in rows:
                print(f"  ID: {row['id']}")
                print(f"  Content: {row['content'][:100]}...")
                print(f"  Has embedding: {row['has_embedding']}")
                print(f"  Importance: {row['importance_score']}")
                print(f"  Created: {row['created_at']}")
                print()
            
            # Test vector similarity search
            print("Testing vector similarity query...")
            similarity_query = """
                SELECT COUNT(*) as total_with_embeddings
                FROM vector_memories 
                WHERE embedding IS NOT NULL;
            """
            count = await self.conn.fetchval(similarity_query)
            print(f"  Total memories with embeddings: {count}")
                
        except Exception as e:
            print(f"Error testing vector operations: {e}")

    async def check_partitions(self):
        """Check partition information"""
        print("\n=== PARTITION INFORMATION ===")
        
        query = """
            SELECT 
                schemaname,
                tablename,
                partitionboundspec
            FROM pg_partitions
            ORDER BY tablename, partitionboundspec;
        """
        
        try:
            rows = await self.conn.fetch(query)
            current_table = None
            for row in rows:
                if row['tablename'] != current_table:
                    current_table = row['tablename']
                    print(f"\nTable: {row['tablename']}")
                print(f"  Partition: {row['partitionboundspec']}")
        except Exception as e:
            print(f"Error checking partitions: {e}")

    async def database_overview(self):
        """Get general database information"""
        print("\n=== DATABASE OVERVIEW ===")
        
        try:
            # Database size
            db_size = await self.conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
            print(f"Database size: {db_size}")
            
            # Version
            version = await self.conn.fetchval("SELECT version()")
            print(f"PostgreSQL version: {version}")
            
            # Current user
            current_user = await self.conn.fetchval("SELECT current_user")
            print(f"Current user: {current_user}")
            
            # Connection info
            print(f"Connected to: {self.database} on {self.host}:{self.port}")
            
        except Exception as e:
            print(f"Error getting database overview: {e}")

    async def execute_query(self, query: str, params: List = None):
        """Execute a custom query"""
        try:
            if params:
                rows = await self.conn.fetch(query, *params)
            else:
                rows = await self.conn.fetch(query)
            
            if rows:
                # Print results in a formatted way
                if len(rows) > 0:
                    columns = rows[0].keys()
                    print(f"\nResults ({len(rows)} rows):")
                    print("  " + " | ".join(columns))
                    print("  " + "-" * (len(" | ".join(columns))))
                    
                    for row in rows[:10]:  # Limit to first 10 rows
                        values = [str(row[col])[:50] for col in columns]  # Truncate long values
                        print("  " + " | ".join(values))
                    
                    if len(rows) > 10:
                        print(f"  ... and {len(rows) - 10} more rows")
                else:
                    print("No results returned")
            else:
                print("Query executed successfully (no results)")
                
        except Exception as e:
            print(f"Error executing query: {e}")

    async def full_exploration(self):
        """Run a complete database exploration"""
        print("🔍 PostgreSQL Database Explorer")
        print("=" * 50)
        
        if not await self.connect():
            return
        
        try:
            await self.database_overview()
            await self.list_extensions()
            await self.list_tables()
            await self.describe_table("vector_memories")
            await self.list_indexes("vector_memories")
            await self.table_stats("vector_memories")
            await self.test_vector_operations()
            await self.check_partitions()
            
            # Check if knowledge graph tables exist
            print("\n=== KNOWLEDGE GRAPH TABLES ===")
            for table in ["graph_nodes", "graph_relationships", "memory_entity_map"]:
                await self.describe_table(table)
                await self.table_stats(table)
        
        finally:
            await self.disconnect()


async def main():
    explorer = PostgreSQLExplorer()
    await explorer.full_exploration()


if __name__ == "__main__":
    asyncio.run(main())
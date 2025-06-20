#!/usr/bin/env python3
"""
PostgreSQL Toolkit for Render Database
A comprehensive toolkit for database operations when psql isn't available
"""

import asyncio
import asyncpg
import json
import sys
from typing import List, Dict, Any, Optional


class PostgreSQLToolkit:
    def __init__(self):
        # Production settings
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
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """Close connection"""
        if self.conn:
            await self.conn.close()

    async def backup_table_structure(self, table_name: str):
        """Generate CREATE TABLE statement for backup"""
        print(f"\n=== BACKUP: {table_name} structure ===")
        
        # Get table definition
        query = """
            SELECT 
                'CREATE TABLE ' || table_name || ' (' || 
                string_agg(
                    column_name || ' ' || 
                    CASE 
                        WHEN data_type = 'USER-DEFINED' THEN udt_name
                        WHEN data_type = 'character varying' AND character_maximum_length IS NOT NULL 
                            THEN data_type || '(' || character_maximum_length || ')'
                        WHEN data_type = 'numeric' AND numeric_precision IS NOT NULL 
                            THEN data_type || '(' || numeric_precision || ',' || numeric_scale || ')'
                        ELSE data_type 
                    END ||
                    CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END ||
                    CASE WHEN column_default IS NOT NULL THEN ' DEFAULT ' || column_default ELSE '' END,
                    ', '
                ) || ');' as create_statement
            FROM information_schema.columns 
            WHERE table_name = $1
            GROUP BY table_name;
        """
        
        try:
            result = await self.conn.fetchval(query, table_name)
            if result:
                print(result)
            else:
                print(f"Table {table_name} not found")
        except Exception as e:
            print(f"Error generating backup: {e}")

    async def export_table_data(self, table_name: str, limit: int = 100):
        """Export table data as SQL INSERT statements"""
        print(f"\n=== EXPORT: {table_name} data (limit {limit}) ===")
        
        try:
            # Get all rows
            rows = await self.conn.fetch(f"SELECT * FROM {table_name} LIMIT $1", limit)
            
            if not rows:
                print("No data to export")
                return
            
            # Get column names
            columns = list(rows[0].keys())
            columns_str = ', '.join(columns)
            
            print(f"-- Data for table {table_name}")
            for row in rows:
                # Convert values to SQL-safe format
                values = []
                for col in columns:
                    val = row[col]
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif isinstance(val, (dict, list)):
                        # JSON data
                        json_str = json.dumps(val).replace("'", "''")
                        values.append(f"'{json_str}'")
                    else:
                        values.append(str(val))
                
                values_str = ', '.join(values)
                print(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});")
                
        except Exception as e:
            print(f"Error exporting data: {e}")

    async def analyze_table_performance(self, table_name: str):
        """Analyze table performance and suggest optimizations"""
        print(f"\n=== PERFORMANCE ANALYSIS: {table_name} ===")
        
        try:
            # Table size and row count
            stats_query = """
                SELECT 
                    pg_size_pretty(pg_total_relation_size($1::regclass)) as total_size,
                    pg_size_pretty(pg_relation_size($1::regclass)) as table_size,
                    pg_size_pretty(pg_total_relation_size($1::regclass) - pg_relation_size($1::regclass)) as index_size,
                    (SELECT reltuples::bigint FROM pg_class WHERE relname = $1) as estimated_rows
            """
            stats = await self.conn.fetchrow(stats_query, table_name)
            
            print(f"  Total size: {stats['total_size']}")
            print(f"  Table size: {stats['table_size']}")
            print(f"  Index size: {stats['index_size']}")
            print(f"  Estimated rows: {stats['estimated_rows']:,}")
            
            # Index usage statistics
            index_query = """
                SELECT 
                    indexrelname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes 
                WHERE relname = $1
                ORDER BY idx_scan DESC;
            """
            
            indexes = await self.conn.fetch(index_query, table_name)
            if indexes:
                print("\n  Index usage:")
                for idx in indexes:
                    print(f"    {idx['indexrelname']}: {idx['idx_scan']} scans, {idx['idx_tup_read']} reads")
            
        except Exception as e:
            print(f"Error analyzing performance: {e}")

    async def test_vector_search(self, query_text: str = "test query"):
        """Test vector similarity search functionality"""
        print(f"\n=== VECTOR SEARCH TEST ===")
        
        try:
            # Get an actual embedding from the database for testing
            existing_vector_query = """
                SELECT embedding 
                FROM vector_memories 
                WHERE embedding IS NOT NULL 
                LIMIT 1;
            """
            
            existing_vector = await self.conn.fetchval(existing_vector_query)
            
            if not existing_vector:
                print("No vectors found in database")
                return
            
            # Test similarity search using an existing vector
            search_query = """
                SELECT 
                    id,
                    content,
                    importance_score,
                    1 - (embedding <=> $1) as similarity_score
                FROM vector_memories 
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT 5;
            """
            
            results = await self.conn.fetch(search_query, existing_vector)
            
            print(f"Vector search results (using random test vector):")
            for i, row in enumerate(results, 1):
                print(f"  {i}. Similarity: {row['similarity_score']:.4f}")
                print(f"     Content: {row['content'][:100]}...")
                print(f"     Importance: {row['importance_score']}")
                print()
                
        except Exception as e:
            print(f"Error testing vector search: {e}")

    async def database_health_check(self):
        """Comprehensive database health check"""
        print(f"\n=== DATABASE HEALTH CHECK ===")
        
        try:
            # Connection test
            print("✓ Database connection: OK")
            
            # Check extensions
            extensions = await self.conn.fetch("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp')")
            ext_names = [e['extname'] for e in extensions]
            
            if 'vector' in ext_names:
                print("✓ pgvector extension: OK")
            else:
                print("✗ pgvector extension: MISSING")
                
            if 'uuid-ossp' in ext_names:
                print("✓ uuid-ossp extension: OK")
            else:
                print("✗ uuid-ossp extension: MISSING")
            
            # Check main tables
            tables = ['vector_memories', 'graph_nodes', 'graph_relationships']
            for table in tables:
                try:
                    count = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    print(f"✓ Table {table}: {count:,} rows")
                except:
                    print(f"✗ Table {table}: ERROR")
            
            # Check vector data integrity
            vector_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
            )
            total_count = await self.conn.fetchval("SELECT COUNT(*) FROM vector_memories")
            
            vector_percentage = (vector_count / total_count * 100) if total_count > 0 else 0
            print(f"✓ Vector embeddings: {vector_count:,}/{total_count:,} ({vector_percentage:.1f}%)")
            
        except Exception as e:
            print(f"✗ Health check error: {e}")

    async def interactive_query(self):
        """Interactive query mode"""
        print("\n=== INTERACTIVE QUERY MODE ===")
        print("Enter SQL queries (type 'exit' to quit, 'help' for commands)")
        
        while True:
            try:
                query = input("\nsql> ").strip()
                
                if query.lower() == 'exit':
                    break
                elif query.lower() == 'help':
                    self.print_help()
                    continue
                elif not query:
                    continue
                
                # Execute query
                if query.upper().startswith('SELECT'):
                    rows = await self.conn.fetch(query)
                    if rows:
                        # Print column headers
                        columns = list(rows[0].keys())
                        print("  " + " | ".join(columns))
                        print("  " + "-" * (len(" | ".join(columns))))
                        
                        # Print rows (limit to 50)
                        for row in rows[:50]:
                            values = [str(row[col])[:50] for col in columns]
                            print("  " + " | ".join(values))
                        
                        if len(rows) > 50:
                            print(f"  ... and {len(rows) - 50} more rows")
                        
                        print(f"\n({len(rows)} rows)")
                    else:
                        print("No results")
                else:
                    result = await self.conn.execute(query)
                    print(f"Query executed: {result}")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def print_help(self):
        """Print available commands"""
        print("""
Available commands:
  SELECT * FROM vector_memories LIMIT 10;   - Query data
  \\dt                                       - List tables (use: SELECT tablename FROM pg_tables WHERE schemaname='public';)
  \\d vector_memories                        - Describe table (use DESCRIBE commands above)
  
Example queries:
  SELECT COUNT(*) FROM vector_memories;
  SELECT * FROM graph_nodes WHERE entity_type = 'person';
  SELECT embedding <=> '[1,2,3,...]'::vector FROM vector_memories LIMIT 1;
  
Type 'exit' to quit interactive mode.
        """)

    async def run_command(self, command: str):
        """Run a specific command"""
        if not await self.connect():
            return
        
        try:
            if command == "explore":
                await self.database_health_check()
                await self.analyze_table_performance("vector_memories")
                await self.test_vector_search()
                
            elif command == "health":
                await self.database_health_check()
                
            elif command == "backup":
                for table in ["vector_memories", "graph_nodes", "graph_relationships"]:
                    await self.backup_table_structure(table)
                    
            elif command == "export":
                table = input("Enter table name to export: ").strip()
                limit = int(input("Enter row limit (default 100): ").strip() or "100")
                await self.export_table_data(table, limit)
                
            elif command == "query":
                await self.interactive_query()
                
            elif command == "test":
                await self.test_vector_search()
                
            else:
                print(f"Unknown command: {command}")
                self.print_usage()
                
        finally:
            await self.disconnect()

    def print_usage(self):
        """Print usage instructions"""
        print("""
PostgreSQL Toolkit Usage:

python pg_toolkit.py <command>

Commands:
  explore  - Full database exploration
  health   - Database health check
  backup   - Backup table structures
  export   - Export table data
  query    - Interactive query mode
  test     - Test vector operations

Examples:
  python pg_toolkit.py health
  python pg_toolkit.py query
  python pg_toolkit.py explore
        """)


async def main():
    if len(sys.argv) < 2:
        toolkit = PostgreSQLToolkit()
        toolkit.print_usage()
        return
    
    command = sys.argv[1].lower()
    toolkit = PostgreSQLToolkit()
    await toolkit.run_command(command)


if __name__ == "__main__":
    asyncio.run(main())
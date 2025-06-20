#!/usr/bin/env python3
"""
Secure Database Backup System for Core Nexus
Enhanced version with environment variable security and better error handling
"""

import asyncio
import asyncpg
import json
import os
import gzip
import pickle
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging


class SecureDatabaseBackupSystem:
    """Secure database backup and restore system using environment variables"""
    
    def __init__(self, backup_dir: str = "/mnt/c/Users/Tyvon/core-nexus/backups"):
        # Database connection settings from environment
        self.host = os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com")
        self.port = int(os.getenv("PGVECTOR_PORT", "5432"))
        self.database = os.getenv("PGVECTOR_DATABASE", "nexus_memory_db")
        self.user = os.getenv("PGVECTOR_USER", "nexus_memory_db_user")
        self.password = os.getenv("PGVECTOR_PASSWORD")
        
        if not self.password:
            raise ValueError("PGVECTOR_PASSWORD environment variable is required")
        
        # Backup settings
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.conn = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """Establish database connection"""
        try:
            self.conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                timeout=30
            )
            self.logger.info("Connected to database successfully")
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            self.logger.info("Disconnected from database")

    async def create_full_backup(self, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a complete database backup"""
        if backup_name is None:
            backup_name = f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        self.logger.info(f"Starting full backup: {backup_name}")
        
        backup_info = {
            "backup_name": backup_name,
            "backup_date": datetime.now(timezone.utc).isoformat(),
            "backup_type": "full",
            "database": self.database,
            "host": self.host,
            "files": {},
            "checksums": {},
            "total_records": 0,
            "tables_backed_up": []
        }
        
        try:
            if not await self.connect():
                raise Exception("Could not connect to database")
            
            # 1. Backup database schema
            self.logger.info("Backing up database schema...")
            schema_file = backup_path / "schema.sql"
            await self._backup_schema(schema_file)
            backup_info["files"]["schema"] = str(schema_file)
            
            # 2. Backup all table data
            tables = await self._get_all_tables()
            self.logger.info(f"Found {len(tables)} tables to backup: {tables}")
            
            for table_name in tables:
                self.logger.info(f"Backing up table: {table_name}")
                
                # Backup table data
                data_file = backup_path / f"{table_name}_data.json.gz"
                record_count = await self._backup_table_data(table_name, data_file)
                backup_info["files"][f"{table_name}_data"] = str(data_file)
                backup_info["total_records"] += record_count
                backup_info["tables_backed_up"].append({
                    "table": table_name,
                    "records": record_count
                })
                
                # Create checksum
                checksum = await self._calculate_file_checksum(data_file)
                backup_info["checksums"][f"{table_name}_data"] = checksum
                
                self.logger.info(f"Backed up {record_count} records from {table_name}")
            
            # 3. Backup vector embeddings separately (binary format for efficiency)
            self.logger.info("Backing up vector embeddings...")
            vectors_file = backup_path / "vector_embeddings.pkl.gz"
            vector_count = await self._backup_vector_embeddings(vectors_file)
            backup_info["files"]["vector_embeddings"] = str(vectors_file)
            backup_info["vector_count"] = vector_count
            
            # 4. Create backup metadata
            metadata_file = backup_path / "backup_info.json"
            with open(metadata_file, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            # 5. Create backup manifest for integrity checking
            manifest_file = backup_path / "MANIFEST"
            await self._create_backup_manifest(backup_path, manifest_file)
            
            # 6. Calculate total backup size
            total_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
            backup_info["backup_size_bytes"] = total_size
            backup_info["backup_size_human"] = self._format_bytes(total_size)
            
            self.logger.info(f"Backup completed successfully: {backup_path}")
            self.logger.info(f"Total records backed up: {backup_info['total_records']:,}")
            self.logger.info(f"Total backup size: {backup_info['backup_size_human']}")
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "backup_info": backup_info
            }
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await self.disconnect()

    async def verify_backup(self, backup_name: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {
                "backup_name": backup_name,
                "integrity_check": False,
                "error": "Backup directory not found",
                "check_date": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            # Check if backup info exists
            backup_info_file = backup_path / "backup_info.json"
            if not backup_info_file.exists():
                return {
                    "backup_name": backup_name,
                    "integrity_check": False,
                    "error": "Backup info file missing",
                    "check_date": datetime.now(timezone.utc).isoformat()
                }
            
            # Load backup info
            with open(backup_info_file, 'r') as f:
                backup_info = json.load(f)
            
            # Verify manifest integrity
            integrity_check = await self._verify_backup_integrity(backup_path)
            
            return {
                "backup_name": backup_name,
                "integrity_check": integrity_check,
                "backup_info": backup_info,
                "check_date": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "backup_name": backup_name,
                "integrity_check": False,
                "error": str(e),
                "check_date": datetime.now(timezone.utc).isoformat()
            }

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups with details"""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                info_file = backup_dir / "backup_info.json"
                if info_file.exists():
                    try:
                        with open(info_file, 'r') as f:
                            backup_info = json.load(f)
                        
                        # Calculate backup size if not already stored
                        if "backup_size_bytes" not in backup_info:
                            size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                            backup_info["backup_size_bytes"] = size
                            backup_info["backup_size_human"] = self._format_bytes(size)
                        
                        # Add verification status
                        verification = await self.verify_backup(backup_dir.name)
                        backup_info["last_verified"] = verification.get("check_date")
                        backup_info["integrity_ok"] = verification.get("integrity_check", False)
                        
                        backups.append(backup_info)
                    except Exception as e:
                        self.logger.warning(f"Could not read backup info for {backup_dir.name}: {e}")
        
        # Sort by backup date (newest first)
        backups.sort(key=lambda x: x.get("backup_date", ""), reverse=True)
        return backups

    # Helper methods (keeping the essential ones from original)
    
    async def _get_all_tables(self) -> List[str]:
        """Get list of all tables"""
        query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """
        rows = await self.conn.fetch(query)
        return [row['tablename'] for row in rows]

    async def _backup_schema(self, schema_file: Path):
        """Backup database schema"""
        schema_lines = []
        
        # Extensions
        extensions = await self.conn.fetch("SELECT extname FROM pg_extension WHERE extname NOT IN ('plpgsql')")
        for ext in extensions:
            schema_lines.append(f"CREATE EXTENSION IF NOT EXISTS {ext['extname']};")
        
        # Tables with full schema
        tables = await self._get_all_tables()
        for table_name in tables:
            # Get table creation DDL
            columns = await self.conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default,
                       character_maximum_length, numeric_precision, numeric_scale
                FROM information_schema.columns 
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table_name)
            
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            col_defs = []
            for col in columns:
                col_def = f"  {col['column_name']} "
                
                # Handle data types properly
                if col['data_type'] == 'character varying' and col['character_maximum_length']:
                    col_def += f"varchar({col['character_maximum_length']})"
                elif col['data_type'] == 'numeric' and col['numeric_precision']:
                    col_def += f"numeric({col['numeric_precision']},{col['numeric_scale'] or 0})"
                else:
                    col_def += col['data_type']
                
                if col['is_nullable'] == 'NO':
                    col_def += " NOT NULL"
                if col['column_default']:
                    col_def += f" DEFAULT {col['column_default']}"
                col_defs.append(col_def)
            
            create_sql += ",\n".join(col_defs) + "\n);"
            schema_lines.append(create_sql)
        
        with open(schema_file, 'w') as f:
            f.write('\n\n'.join(schema_lines))

    async def _backup_table_data(self, table_name: str, data_file: Path) -> int:
        """Backup table data to compressed JSON"""
        # Check if table has an 'id' column, otherwise use first column for ordering
        columns = await self.conn.fetch("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = $1 ORDER BY ordinal_position
        """, table_name)
        
        if not columns:
            return 0
        
        # Use 'id' if available, otherwise first column
        order_column = 'id' if any(col['column_name'] == 'id' for col in columns) else columns[0]['column_name']
        query = f"SELECT * FROM {table_name} ORDER BY {order_column}"
        
        with gzip.open(data_file, 'wt') as f:
            records = await self.conn.fetch(query)
            
            # Convert records to JSON-serializable format
            serializable_records = []
            for record in records:
                record_dict = dict(record)
                # Handle special types
                for key, value in record_dict.items():
                    if isinstance(value, uuid.UUID):
                        record_dict[key] = str(value)
                    elif isinstance(value, datetime):
                        record_dict[key] = value.isoformat()
                    elif hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                        # Convert vectors and arrays to lists
                        try:
                            record_dict[key] = list(value)
                        except:
                            record_dict[key] = str(value)
                
                serializable_records.append(record_dict)
            
            json.dump(serializable_records, f, indent=2)
            return len(records)

    async def _backup_vector_embeddings(self, vectors_file: Path) -> int:
        """Backup vector embeddings in efficient binary format"""
        try:
            query = "SELECT id, embedding FROM vector_memories WHERE embedding IS NOT NULL"
            records = await self.conn.fetch(query)
            
            # Store as binary pickle for efficiency
            embeddings_data = {
                str(record['id']): list(record['embedding']) 
                for record in records
            }
            
            with gzip.open(vectors_file, 'wb') as f:
                pickle.dump(embeddings_data, f)
            
            return len(records)
        except Exception as e:
            self.logger.warning(f"Vector backup failed: {e}")
            return 0

    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def _create_backup_manifest(self, backup_path: Path, manifest_file: Path):
        """Create backup manifest file"""
        manifest = {
            "backup_path": str(backup_path),
            "creation_date": datetime.now(timezone.utc).isoformat(),
            "files": {}
        }
        
        for file_path in backup_path.rglob('*'):
            if file_path.is_file() and file_path.name != "MANIFEST":
                rel_path = file_path.relative_to(backup_path)
                manifest["files"][str(rel_path)] = {
                    "size": file_path.stat().st_size,
                    "checksum": await self._calculate_file_checksum(file_path)
                }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

    async def _verify_backup_integrity(self, backup_path: Path) -> bool:
        """Verify backup file integrity"""
        manifest_file = backup_path / "MANIFEST"
        if not manifest_file.exists():
            self.logger.warning("Manifest file missing - cannot verify integrity")
            return False
        
        try:
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            for rel_path, file_info in manifest["files"].items():
                file_path = backup_path / rel_path
                if not file_path.exists():
                    self.logger.error(f"Missing file: {rel_path}")
                    return False
                
                actual_checksum = await self._calculate_file_checksum(file_path)
                if actual_checksum != file_info["checksum"]:
                    self.logger.error(f"Checksum mismatch: {rel_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Integrity check failed: {e}")
            return False

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"


async def main():
    """CLI interface for secure backup system"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
Secure Database Backup System Usage:

python secure_backup_system.py <command> [options]

Commands:
  full_backup [name]           - Create full database backup
  list                         - List all backups with verification status
  verify <backup_name>         - Verify backup integrity
  health                       - Test database connection

Environment Variables Required:
  PGVECTOR_PASSWORD           - PostgreSQL password

Optional Environment Variables:
  PGVECTOR_HOST              - PostgreSQL host (default: render host)
  PGVECTOR_PORT              - PostgreSQL port (default: 5432)
  PGVECTOR_DATABASE          - Database name (default: nexus_memory_db)
  PGVECTOR_USER              - Username (default: nexus_memory_db_user)

Examples:
  export PGVECTOR_PASSWORD="your_password"
  python secure_backup_system.py full_backup
  python secure_backup_system.py list
  python secure_backup_system.py verify "full_backup_20250620_120000"
        """)
        return
    
    try:
        backup_system = SecureDatabaseBackupSystem()
        command = sys.argv[1].lower()
        
        if command == "full_backup":
            backup_name = sys.argv[2] if len(sys.argv) > 2 else None
            result = await backup_system.create_full_backup(backup_name)
            print(json.dumps(result, indent=2))
            
        elif command == "list":
            backups = await backup_system.list_backups()
            print(json.dumps(backups, indent=2))
            
        elif command == "verify":
            if len(sys.argv) < 3:
                print("Error: Backup name required")
                return
            backup_name = sys.argv[2]
            result = await backup_system.verify_backup(backup_name)
            print(json.dumps(result, indent=2))
            
        elif command == "health":
            # Test connection
            if await backup_system.connect():
                print("✅ Database connection successful")
                await backup_system.disconnect()
            else:
                print("❌ Database connection failed")
        
        else:
            print(f"Unknown command: {command}")
    
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set the PGVECTOR_PASSWORD environment variable")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
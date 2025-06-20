#!/usr/bin/env python3
"""
Comprehensive Database Backup System for Core Nexus
Provides full database backup and restore capabilities without pg_dump
"""

import asyncio
import asyncpg
import json
import os
import gzip
import pickle
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging


class DatabaseBackupSystem:
    """Complete database backup and restore system"""
    
    def __init__(self, backup_dir: str = "./backups"):
        # Database connection settings
        self.host = "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"
        self.port = 5432
        self.database = "nexus_memory_db"
        self.user = "nexus_memory_db_user"
        self.password = "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
        
        # Backup settings
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.conn = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
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
            self.logger.info("Connected to database")
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            self.logger.info("Disconnected from database")

    async def create_full_backup(self, backup_name: Optional[str] = None) -> Dict[str, str]:
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
            "files": {},
            "checksums": {},
            "total_records": 0
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
            
            for table_name in tables:
                self.logger.info(f"Backing up table: {table_name}")
                
                # Backup table data
                data_file = backup_path / f"{table_name}_data.json.gz"
                record_count = await self._backup_table_data(table_name, data_file)
                backup_info["files"][f"{table_name}_data"] = str(data_file)
                backup_info["total_records"] += record_count
                
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
            
            self.logger.info(f"Backup completed successfully: {backup_path}")
            self.logger.info(f"Total records backed up: {backup_info['total_records']}")
            
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

    async def create_incremental_backup(self, base_backup: str, backup_name: Optional[str] = None) -> Dict[str, str]:
        """Create an incremental backup based on a previous full backup"""
        if backup_name is None:
            backup_name = f"incremental_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Load base backup info
        base_backup_path = self.backup_dir / base_backup
        base_info_file = base_backup_path / "backup_info.json"
        
        if not base_info_file.exists():
            raise Exception(f"Base backup not found: {base_backup}")
        
        with open(base_info_file, 'r') as f:
            base_info = json.load(f)
        
        base_date = datetime.fromisoformat(base_info["backup_date"])
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        self.logger.info(f"Starting incremental backup: {backup_name}")
        self.logger.info(f"Base backup: {base_backup} from {base_date}")
        
        backup_info = {
            "backup_name": backup_name,
            "backup_date": datetime.now(timezone.utc).isoformat(),
            "backup_type": "incremental",
            "base_backup": base_backup,
            "base_backup_date": base_info["backup_date"],
            "database": self.database,
            "files": {},
            "checksums": {},
            "total_records": 0
        }
        
        try:
            if not await self.connect():
                raise Exception("Could not connect to database")
            
            # Backup only changed data since base backup
            tables = await self._get_all_tables()
            
            for table_name in tables:
                # Get records modified since base backup
                if table_name == "vector_memories":
                    # Use created_at and updated_at for filtering
                    query = f"""
                        SELECT * FROM {table_name} 
                        WHERE created_at > $1 OR updated_at > $1
                        ORDER BY created_at
                    """
                elif "created_at" in await self._get_table_columns(table_name):
                    query = f"""
                        SELECT * FROM {table_name} 
                        WHERE created_at > $1
                        ORDER BY created_at
                    """
                else:
                    # For tables without timestamps, skip incremental
                    continue
                
                records = await self.conn.fetch(query, base_date)
                
                if records:
                    self.logger.info(f"Backing up {len(records)} changed records from {table_name}")
                    
                    data_file = backup_path / f"{table_name}_incremental.json.gz"
                    await self._save_records_to_file(records, data_file)
                    backup_info["files"][f"{table_name}_data"] = str(data_file)
                    backup_info["total_records"] += len(records)
                    
                    checksum = await self._calculate_file_checksum(data_file)
                    backup_info["checksums"][f"{table_name}_data"] = checksum
            
            # Save backup metadata
            metadata_file = backup_path / "backup_info.json"
            with open(metadata_file, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            self.logger.info(f"Incremental backup completed: {backup_path}")
            self.logger.info(f"Changed records backed up: {backup_info['total_records']}")
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "backup_info": backup_info
            }
            
        except Exception as e:
            self.logger.error(f"Incremental backup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await self.disconnect()

    async def restore_from_backup(self, backup_name: str, confirm: bool = False) -> Dict[str, str]:
        """Restore database from backup (DANGEROUS - requires confirmation)"""
        if not confirm:
            return {
                "success": False,
                "error": "Restore requires explicit confirmation (confirm=True). This will overwrite all existing data!"
            }
        
        backup_path = self.backup_dir / backup_name
        backup_info_file = backup_path / "backup_info.json"
        
        if not backup_info_file.exists():
            return {
                "success": False,
                "error": f"Backup not found: {backup_name}"
            }
        
        with open(backup_info_file, 'r') as f:
            backup_info = json.load(f)
        
        self.logger.warning(f"STARTING RESTORE OPERATION: {backup_name}")
        self.logger.warning("THIS WILL OVERWRITE ALL EXISTING DATA!")
        
        try:
            if not await self.connect():
                raise Exception("Could not connect to database")
            
            # Verify backup integrity first
            if not await self._verify_backup_integrity(backup_path):
                raise Exception("Backup integrity check failed")
            
            # Start transaction for atomic restore
            async with self.conn.transaction():
                # 1. Clear existing data (in reverse dependency order)
                await self._clear_all_tables()
                
                # 2. Restore schema if needed
                schema_file = backup_path / "schema.sql"
                if schema_file.exists():
                    self.logger.info("Restoring database schema...")
                    await self._restore_schema(schema_file)
                
                # 3. Restore table data
                for table_name in await self._get_all_tables():
                    data_file = backup_path / f"{table_name}_data.json.gz"
                    if data_file.exists():
                        self.logger.info(f"Restoring table: {table_name}")
                        await self._restore_table_data(table_name, data_file)
                
                # 4. Restore vector embeddings
                vectors_file = backup_path / "vector_embeddings.pkl.gz"
                if vectors_file.exists():
                    self.logger.info("Restoring vector embeddings...")
                    await self._restore_vector_embeddings(vectors_file)
            
            self.logger.info("Restore completed successfully")
            
            return {
                "success": True,
                "restored_backup": backup_name,
                "restore_date": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await self.disconnect()

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                info_file = backup_dir / "backup_info.json"
                if info_file.exists():
                    try:
                        with open(info_file, 'r') as f:
                            backup_info = json.load(f)
                        
                        # Calculate backup size
                        size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                        backup_info["size_bytes"] = size
                        backup_info["size_human"] = self._format_bytes(size)
                        
                        backups.append(backup_info)
                    except Exception as e:
                        self.logger.warning(f"Could not read backup info for {backup_dir.name}: {e}")
        
        # Sort by backup date
        backups.sort(key=lambda x: x["backup_date"], reverse=True)
        return backups

    async def verify_backup(self, backup_name: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        backup_path = self.backup_dir / backup_name
        return {
            "backup_name": backup_name,
            "integrity_check": await self._verify_backup_integrity(backup_path),
            "check_date": datetime.now(timezone.utc).isoformat()
        }

    # Helper methods
    
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

    async def _get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table"""
        query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = $1
            ORDER BY ordinal_position
        """
        rows = await self.conn.fetch(query, table_name)
        return [row['column_name'] for row in rows]

    async def _backup_schema(self, schema_file: Path):
        """Backup database schema"""
        # Get table creation statements
        schema_lines = []
        
        # Extensions
        extensions = await self.conn.fetch("SELECT extname FROM pg_extension WHERE extname NOT IN ('plpgsql')")
        for ext in extensions:
            schema_lines.append(f"CREATE EXTENSION IF NOT EXISTS {ext['extname']};")
        
        # Tables
        tables = await self._get_all_tables()
        for table_name in tables:
            # This is a simplified schema backup - in production you'd want full DDL
            columns = await self.conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table_name)
            
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            col_defs = []
            for col in columns:
                col_def = f"  {col['column_name']} {col['data_type']}"
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
        query = f"SELECT * FROM {table_name} ORDER BY id"
        
        with gzip.open(data_file, 'wt') as f:
            records = await self.conn.fetch(query)
            
            # Convert records to JSON-serializable format
            serializable_records = []
            for record in records:
                record_dict = dict(record)
                # Handle special types
                for key, value in record_dict.items():
                    if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                        # Convert vectors and arrays to lists
                        try:
                            record_dict[key] = list(value)
                        except:
                            record_dict[key] = str(value)
                    elif isinstance(value, datetime):
                        record_dict[key] = value.isoformat()
                
                serializable_records.append(record_dict)
            
            json.dump(serializable_records, f, indent=2)
            return len(records)

    async def _backup_vector_embeddings(self, vectors_file: Path) -> int:
        """Backup vector embeddings in efficient binary format"""
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

    async def _save_records_to_file(self, records: List, data_file: Path):
        """Save records to compressed JSON file"""
        with gzip.open(data_file, 'wt') as f:
            serializable_records = []
            for record in records:
                record_dict = dict(record)
                for key, value in record_dict.items():
                    if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                        try:
                            record_dict[key] = list(value)
                        except:
                            record_dict[key] = str(value)
                    elif isinstance(value, datetime):
                        record_dict[key] = value.isoformat()
                serializable_records.append(record_dict)
            
            json.dump(serializable_records, f, indent=2)

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

    async def _clear_all_tables(self):
        """Clear all tables (for restore operation)"""
        tables = await self._get_all_tables()
        # Reverse order to handle dependencies
        for table_name in reversed(tables):
            await self.conn.execute(f"TRUNCATE TABLE {table_name} CASCADE")

    async def _restore_schema(self, schema_file: Path):
        """Restore database schema from file"""
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema statements
        statements = schema_sql.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                await self.conn.execute(statement)

    async def _restore_table_data(self, table_name: str, data_file: Path):
        """Restore table data from backup file"""
        with gzip.open(data_file, 'rt') as f:
            records = json.load(f)
        
        if not records:
            return
        
        # Get column names
        columns = list(records[0].keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        
        insert_query = f"""
            INSERT INTO {table_name} ({', '.join(columns)}) 
            VALUES ({', '.join(placeholders)})
        """
        
        # Insert in batches
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            values = [list(record.values()) for record in batch]
            await self.conn.executemany(insert_query, values)

    async def _restore_vector_embeddings(self, vectors_file: Path):
        """Restore vector embeddings from binary backup"""
        with gzip.open(vectors_file, 'rb') as f:
            embeddings_data = pickle.load(f)
        
        # Update embeddings in batches
        for memory_id, embedding in embeddings_data.items():
            await self.conn.execute(
                "UPDATE vector_memories SET embedding = $1 WHERE id = $2",
                embedding, memory_id
            )

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"


async def main():
    """CLI interface for backup system"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
Database Backup System Usage:

python database_backup_system.py <command> [options]

Commands:
  full_backup [name]           - Create full database backup
  incremental_backup <base>    - Create incremental backup
  list                         - List all backups
  verify <backup_name>         - Verify backup integrity
  restore <backup_name>        - Restore from backup (requires confirmation)

Examples:
  python database_backup_system.py full_backup
  python database_backup_system.py full_backup "my_backup_20241216"
  python database_backup_system.py incremental_backup "full_backup_20241216_120000"
  python database_backup_system.py list
  python database_backup_system.py verify "full_backup_20241216_120000"
        """)
        return
    
    backup_system = DatabaseBackupSystem()
    command = sys.argv[1].lower()
    
    if command == "full_backup":
        backup_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = await backup_system.create_full_backup(backup_name)
        print(json.dumps(result, indent=2))
        
    elif command == "incremental_backup":
        if len(sys.argv) < 3:
            print("Error: Base backup name required for incremental backup")
            return
        base_backup = sys.argv[2]
        backup_name = sys.argv[3] if len(sys.argv) > 3 else None
        result = await backup_system.create_incremental_backup(base_backup, backup_name)
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
        
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Error: Backup name required")
            return
        backup_name = sys.argv[2]
        
        # Safety confirmation
        print(f"WARNING: This will completely replace all data in the database!")
        print(f"Backup to restore: {backup_name}")
        confirm = input("Type 'CONFIRM_RESTORE' to proceed: ")
        
        if confirm == "CONFIRM_RESTORE":
            result = await backup_system.restore_from_backup(backup_name, confirm=True)
            print(json.dumps(result, indent=2))
        else:
            print("Restore cancelled")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
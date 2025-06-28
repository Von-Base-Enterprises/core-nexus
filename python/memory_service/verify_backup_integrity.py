#!/usr/bin/env python3
"""
Backup Integrity Verification Script for Core Nexus
Verifies backup completeness, checksums, and data consistency.
"""

import os
import json
import gzip
import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackupIntegrityVerifier:
    """Verify backup integrity and completeness"""
    
    def __init__(self, backup_dir: str = "/mnt/c/Users/Tyvon/core-nexus/python/memory_service/backups"):
        self.backup_dir = Path(backup_dir)
        self.results = {
            'tests_passed': 0,
            'tests_failed': 0,
            'warnings': 0,
            'critical_issues': 0
        }
    
    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return None
    
    def verify_file_integrity(self, backup_name: str, backup_info: Dict) -> bool:
        """Verify file integrity using checksums"""
        logger.info(f"🔍 Verifying file integrity for backup: {backup_name}")
        
        backup_path = self.backup_dir / backup_name
        checksums = backup_info.get('checksums', {})
        all_files_valid = True
        
        for file_key, expected_checksum in checksums.items():
            # Get the actual file path
            file_info = backup_info.get('files', {})
            if file_key not in file_info:
                logger.error(f"   ❌ Missing file reference for {file_key}")
                all_files_valid = False
                self.results['tests_failed'] += 1
                continue
            
            file_path = backup_path / Path(file_info[file_key]).name
            
            if not file_path.exists():
                logger.error(f"   ❌ File missing: {file_path}")
                all_files_valid = False
                self.results['tests_failed'] += 1
                continue
            
            actual_checksum = self.calculate_file_checksum(file_path)
            if actual_checksum != expected_checksum:
                logger.error(f"   ❌ Checksum mismatch for {file_key}")
                logger.error(f"      Expected: {expected_checksum}")
                logger.error(f"      Actual:   {actual_checksum}")
                all_files_valid = False
                self.results['critical_issues'] += 1
            else:
                logger.info(f"   ✅ {file_key}: checksum valid")
                self.results['tests_passed'] += 1
        
        return all_files_valid
    
    def verify_data_content(self, backup_name: str, backup_info: Dict) -> bool:
        """Verify that backup data files contain expected content"""
        logger.info(f"📊 Verifying data content for backup: {backup_name}")
        
        backup_path = self.backup_dir / backup_name
        files = backup_info.get('files', {})
        content_valid = True
        
        # Check memories data
        if 'memories_data' in files:
            memories_file = backup_path / Path(files['memories_data']).name
            try:
                with gzip.open(memories_file, 'rt') as f:
                    memories_data = json.load(f)
                    memory_count = len(memories_data)
                    logger.info(f"   ✅ Memories data: {memory_count} records")
                    
                    # Sample a few records to verify structure
                    if memory_count > 0:
                        sample_memory = memories_data[0]
                        required_fields = ['id', 'content', 'metadata']
                        missing_fields = [field for field in required_fields if field not in sample_memory]
                        if missing_fields:
                            logger.error(f"   ❌ Missing fields in memory data: {missing_fields}")
                            content_valid = False
                            self.results['critical_issues'] += 1
                        else:
                            logger.info(f"   ✅ Memory data structure valid")
                            self.results['tests_passed'] += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Failed to read memories data: {e}")
                content_valid = False
                self.results['tests_failed'] += 1
        
        # Check vector embeddings
        if 'vector_embeddings' in files:
            embeddings_file = backup_path / Path(files['vector_embeddings']).name
            try:
                with gzip.open(embeddings_file, 'rb') as f:
                    embeddings_data = pickle.load(f)
                    embedding_count = len(embeddings_data)
                    logger.info(f"   ✅ Vector embeddings: {embedding_count} records")
                    
                    # Verify embedding structure
                    if embedding_count > 0:
                        sample_embedding = next(iter(embeddings_data.values()))
                        if isinstance(sample_embedding, list) and len(sample_embedding) > 0:
                            logger.info(f"   ✅ Embedding vectors valid (dimension: {len(sample_embedding)})")
                            self.results['tests_passed'] += 1
                        else:
                            logger.error(f"   ❌ Invalid embedding format")
                            content_valid = False
                            self.results['critical_issues'] += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Failed to read vector embeddings: {e}")
                content_valid = False
                self.results['tests_failed'] += 1
        
        # Check graph data
        graph_files = ['graph_nodes_data', 'graph_relationships_data', 'graph_edges_data']
        for graph_file_key in graph_files:
            if graph_file_key in files:
                graph_file = backup_path / Path(files[graph_file_key]).name
                try:
                    with gzip.open(graph_file, 'rt') as f:
                        graph_data = json.load(f)
                        record_count = len(graph_data)
                        logger.info(f"   ✅ {graph_file_key}: {record_count} records")
                        self.results['tests_passed'] += 1
                except Exception as e:
                    logger.error(f"   ❌ Failed to read {graph_file_key}: {e}")
                    content_valid = False
                    self.results['tests_failed'] += 1
        
        return content_valid
    
    def verify_backup_completeness(self, backup_info: Dict) -> bool:
        """Verify backup contains all expected components"""
        logger.info("📋 Verifying backup completeness...")
        
        expected_files = [
            'memories_data',
            'vector_memories_data', 
            'vector_embeddings',
            'graph_nodes_data',
            'graph_relationships_data',
            'schema'
        ]
        
        files = backup_info.get('files', {})
        missing_files = []
        
        for expected_file in expected_files:
            if expected_file not in files:
                missing_files.append(expected_file)
        
        if missing_files:
            logger.error(f"   ❌ Missing backup components: {missing_files}")
            self.results['critical_issues'] += len(missing_files)
            return False
        else:
            logger.info(f"   ✅ All expected backup components present")
            self.results['tests_passed'] += 1
            return True
    
    def verify_record_counts(self, backup_info: Dict) -> bool:
        """Verify record counts are reasonable"""
        logger.info("📊 Verifying record counts...")
        
        tables_backed_up = backup_info.get('tables_backed_up', [])
        total_records = backup_info.get('total_records', 0)
        
        if not tables_backed_up:
            logger.error("   ❌ No table information in backup")
            self.results['critical_issues'] += 1
            return False
        
        calculated_total = sum(table.get('records', 0) for table in tables_backed_up)
        
        if calculated_total != total_records:
            logger.warning(f"   ⚠️  Record count mismatch: calculated {calculated_total} vs reported {total_records}")
            self.results['warnings'] += 1
        else:
            logger.info(f"   ✅ Record counts consistent: {total_records} total records")
            self.results['tests_passed'] += 1
        
        # Check for reasonable data volumes
        for table in tables_backed_up:
            table_name = table.get('table', 'unknown')
            record_count = table.get('records', 0)
            
            if table_name == 'memories' and record_count < 100:
                logger.warning(f"   ⚠️  Low memory count for production system: {record_count}")
                self.results['warnings'] += 1
            elif table_name == 'vector_memories' and record_count < 100:
                logger.warning(f"   ⚠️  Low vector memory count: {record_count}")
                self.results['warnings'] += 1
            else:
                logger.info(f"   ✅ {table_name}: {record_count} records")
        
        return True
    
    def run_full_verification(self) -> Dict:
        """Run complete backup verification suite"""
        logger.info("🔧 Starting Core Nexus Backup Integrity Verification")
        logger.info("=" * 60)
        
        # Read backup status
        status_file = self.backup_dir / "backup_status.json"
        if not status_file.exists():
            logger.error("❌ No backup status file found")
            return {'status': 'failed', 'error': 'No backup status file'}
        
        try:
            with open(status_file, 'r') as f:
                backup_status = json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to read backup status: {e}")
            return {'status': 'failed', 'error': str(e)}
        
        backup_history = backup_status.get('backup_history', [])
        if not backup_history:
            logger.error("❌ No backups found in history")
            return {'status': 'failed', 'error': 'No backups available'}
        
        # Get most recent backup
        latest_backup = backup_history[-1]
        backup_name = latest_backup['backup_name']
        
        logger.info(f"🎯 Verifying latest backup: {backup_name}")
        logger.info(f"📅 Backup date: {latest_backup.get('timestamp', 'unknown')}")
        logger.info(f"📦 Backup size: {latest_backup.get('size_human', 'unknown')}")
        logger.info("")
        
        # Read backup info
        backup_info_file = self.backup_dir / backup_name / "backup_info.json"
        if not backup_info_file.exists():
            logger.error(f"❌ Backup info file missing for {backup_name}")
            return {'status': 'failed', 'error': 'Backup info missing'}
        
        try:
            with open(backup_info_file, 'r') as f:
                backup_info = json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to read backup info: {e}")
            return {'status': 'failed', 'error': str(e)}
        
        # Run verification tests
        tests = [
            ('Backup Completeness', lambda: self.verify_backup_completeness(backup_info)),
            ('Record Counts', lambda: self.verify_record_counts(backup_info)),
            ('File Integrity', lambda: self.verify_file_integrity(backup_name, backup_info)),
            ('Data Content', lambda: self.verify_data_content(backup_name, backup_info))
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running test: {test_name}")
            try:
                result = test_func()
                if not result:
                    all_passed = False
                    logger.error(f"   ❌ {test_name} failed")
                else:
                    logger.info(f"   ✅ {test_name} passed")
            except Exception as e:
                logger.error(f"   ❌ {test_name} error: {e}")
                all_passed = False
                self.results['tests_failed'] += 1
        
        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 BACKUP VERIFICATION SUMMARY")
        logger.info("=" * 60)
        
        logger.info(f"✅ Tests passed: {self.results['tests_passed']}")
        logger.info(f"❌ Tests failed: {self.results['tests_failed']}")
        logger.info(f"⚠️  Warnings: {self.results['warnings']}")
        logger.info(f"🚨 Critical issues: {self.results['critical_issues']}")
        
        if all_passed and self.results['critical_issues'] == 0:
            logger.info("\n🎉 BACKUP VERIFICATION: PASSED")
            logger.info("✅ Backup integrity confirmed")
            logger.info("✅ All data files present and valid")
            logger.info("✅ Ready for disaster recovery")
            status = 'passed'
        elif self.results['critical_issues'] == 0:
            logger.info("\n⚠️  BACKUP VERIFICATION: PASSED WITH WARNINGS")
            logger.info("✅ Backup is usable but has minor issues")
            status = 'warning'
        else:
            logger.error("\n❌ BACKUP VERIFICATION: FAILED")
            logger.error("🚨 Critical issues found - backup may be corrupted")
            status = 'failed'
        
        return {
            'status': status,
            'backup_name': backup_name,
            'results': self.results,
            'timestamp': latest_backup.get('timestamp'),
            'size': latest_backup.get('size_human')
        }

def main():
    """Run backup verification"""
    verifier = BackupIntegrityVerifier()
    result = verifier.run_full_verification()
    
    # Exit with appropriate code
    if result['status'] == 'passed':
        exit(0)
    elif result['status'] == 'warning':
        exit(1)
    else:
        exit(2)

if __name__ == "__main__":
    main()
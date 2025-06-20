#!/usr/bin/env python3
"""
Automated Backup Scheduler with Retention Policy
Safely schedules and manages database backups for Core Nexus
"""

import asyncio
import json
import os
import schedule
import time
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import logging

# Import our secure backup system
from secure_backup_system import SecureDatabaseBackupSystem


class BackupScheduler:
    """Automated backup scheduler with retention policy"""
    
    def __init__(self, backup_dir: str = "/mnt/c/Users/Tyvon/core-nexus/backups"):
        self.backup_system = SecureDatabaseBackupSystem(backup_dir)
        self.backup_dir = Path(backup_dir)
        self.running = False
        
        # Retention policy: 7 daily, 4 weekly, 12 monthly
        self.retention_policy = {
            "daily": 7,    # Keep 7 daily backups
            "weekly": 4,   # Keep 4 weekly backups  
            "monthly": 12  # Keep 12 monthly backups
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backup_scheduler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    async def create_scheduled_backup(self, backup_type: str = "daily"):
        """Create a scheduled backup with appropriate naming"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{backup_type}_backup_{timestamp}"
        
        self.logger.info(f"Starting {backup_type} backup: {backup_name}")
        
        try:
            result = await self.backup_system.create_full_backup(backup_name)
            
            if result["success"]:
                self.logger.info(f"✅ {backup_type} backup successful: {backup_name}")
                self.logger.info(f"   Size: {result['backup_info']['backup_size_human']}")
                self.logger.info(f"   Records: {result['backup_info']['total_records']:,}")
                
                # Log backup details to status file
                await self._log_backup_status(backup_name, result["backup_info"], "success")
                
                return True
            else:
                self.logger.error(f"❌ {backup_type} backup failed: {result['error']}")
                await self._log_backup_status(backup_name, {}, "failed", result["error"])
                return False
                
        except Exception as e:
            self.logger.error(f"❌ {backup_type} backup exception: {e}")
            await self._log_backup_status(backup_name, {}, "error", str(e))
            return False

    async def cleanup_old_backups(self):
        """Apply retention policy to remove old backups"""
        self.logger.info("Starting backup cleanup based on retention policy...")
        
        try:
            # Get all backups
            backups = await self.backup_system.list_backups()
            
            # Sort backups by type and date
            daily_backups = []
            weekly_backups = []
            monthly_backups = []
            
            for backup in backups:
                backup_name = backup.get("backup_name", "")
                if "daily_backup_" in backup_name:
                    daily_backups.append(backup)
                elif "weekly_backup_" in backup_name:
                    weekly_backups.append(backup)
                elif "monthly_backup_" in backup_name:
                    monthly_backups.append(backup)
            
            # Apply retention policy
            deleted_count = 0
            
            # Clean daily backups (keep last 7)
            if len(daily_backups) > self.retention_policy["daily"]:
                # Sort by date (oldest first)
                daily_backups.sort(key=lambda x: x.get("backup_date", ""))
                to_delete = daily_backups[:-self.retention_policy["daily"]]
                
                for backup in to_delete:
                    await self._delete_backup(backup["backup_name"])
                    deleted_count += 1
            
            # Clean weekly backups (keep last 4)
            if len(weekly_backups) > self.retention_policy["weekly"]:
                weekly_backups.sort(key=lambda x: x.get("backup_date", ""))
                to_delete = weekly_backups[:-self.retention_policy["weekly"]]
                
                for backup in to_delete:
                    await self._delete_backup(backup["backup_name"])
                    deleted_count += 1
            
            # Clean monthly backups (keep last 12)
            if len(monthly_backups) > self.retention_policy["monthly"]:
                monthly_backups.sort(key=lambda x: x.get("backup_date", ""))
                to_delete = monthly_backups[:-self.retention_policy["monthly"]]
                
                for backup in to_delete:
                    await self._delete_backup(backup["backup_name"])
                    deleted_count += 1
            
            if deleted_count > 0:
                self.logger.info(f"🗑️  Cleaned up {deleted_count} old backups")
            else:
                self.logger.info("✅ No old backups to clean up")
                
        except Exception as e:
            self.logger.error(f"❌ Backup cleanup failed: {e}")

    async def _delete_backup(self, backup_name: str):
        """Delete a backup directory and its contents"""
        backup_path = self.backup_dir / backup_name
        if backup_path.exists():
            import shutil
            shutil.rmtree(backup_path)
            self.logger.info(f"🗑️  Deleted old backup: {backup_name}")

    async def _log_backup_status(self, backup_name: str, backup_info: Dict, status: str, error: str = None):
        """Log backup status to a status file"""
        status_file = self.backup_dir / "backup_status.json"
        
        # Load existing status
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
        else:
            status_data = {"backup_history": []}
        
        # Add new status entry
        entry = {
            "backup_name": backup_name,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "size_human": backup_info.get("backup_size_human", "unknown"),
            "total_records": backup_info.get("total_records", 0)
        }
        
        if error:
            entry["error"] = error
        
        status_data["backup_history"].append(entry)
        
        # Keep only last 100 entries
        status_data["backup_history"] = status_data["backup_history"][-100:]
        
        # Save status
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)

    def schedule_backups(self):
        """Setup backup schedule"""
        self.logger.info("Setting up backup schedule...")
        
        # Daily backup at 2 AM
        schedule.every().day.at("02:00").do(
            lambda: asyncio.create_task(self.create_scheduled_backup("daily"))
        )
        
        # Weekly backup on Sunday at 3 AM
        schedule.every().sunday.at("03:00").do(
            lambda: asyncio.create_task(self.create_scheduled_backup("weekly"))
        )
        
        # Monthly backup on 1st of month at 4 AM
        schedule.every().month.do(
            lambda: asyncio.create_task(self.create_scheduled_backup("monthly"))
        )
        
        # Cleanup old backups daily at 5 AM
        schedule.every().day.at("05:00").do(
            lambda: asyncio.create_task(self.cleanup_old_backups())
        )
        
        self.logger.info("✅ Backup schedule configured:")
        self.logger.info("   📅 Daily backups: 2:00 AM")
        self.logger.info("   📅 Weekly backups: Sunday 3:00 AM")
        self.logger.info("   📅 Monthly backups: 1st of month 4:00 AM")
        self.logger.info("   🗑️  Cleanup: Daily 5:00 AM")

    async def health_check(self):
        """Perform health check on backup system"""
        self.logger.info("Running backup system health check...")
        
        try:
            # Test database connection
            if await self.backup_system.connect():
                await self.backup_system.disconnect()
                self.logger.info("✅ Database connection: OK")
                return True
            else:
                self.logger.error("❌ Database connection: FAILED")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}")
            return False

    async def run_immediate_backup(self, backup_type: str = "manual"):
        """Run an immediate backup for testing"""
        self.logger.info(f"Running immediate {backup_type} backup...")
        success = await self.create_scheduled_backup(backup_type)
        
        if success:
            self.logger.info("✅ Immediate backup completed successfully")
        else:
            self.logger.error("❌ Immediate backup failed")
        
        return success

    async def start_scheduler(self):
        """Start the backup scheduler daemon"""
        self.logger.info("🚀 Starting backup scheduler daemon...")
        
        # Check environment
        if not os.getenv("PGVECTOR_PASSWORD"):
            self.logger.error("❌ PGVECTOR_PASSWORD environment variable not set")
            return
        
        # Health check
        if not await self.health_check():
            self.logger.error("❌ Health check failed, cannot start scheduler")
            return
        
        # Setup schedules
        self.schedule_backups()
        
        # Start daemon loop
        self.running = True
        self.logger.info("✅ Backup scheduler daemon started")
        
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
        
        self.logger.info("🛑 Backup scheduler daemon stopped")

    def get_status(self):
        """Get current backup status"""
        status_file = self.backup_dir / "backup_status.json"
        
        if status_file.exists():
            with open(status_file, 'r') as f:
                return json.load(f)
        else:
            return {"backup_history": []}


async def main():
    """CLI interface for backup scheduler"""
    if len(sys.argv) < 2:
        print("""
Backup Scheduler Usage:

python backup_scheduler.py <command> [options]

Commands:
  start                        - Start the backup scheduler daemon
  health                       - Check backup system health  
  manual                       - Run immediate manual backup
  status                       - Show backup status history
  cleanup                      - Run backup cleanup now

Environment Variables Required:
  PGVECTOR_PASSWORD           - PostgreSQL password

Examples:
  export PGVECTOR_PASSWORD="your_password"
  python backup_scheduler.py start      # Start daemon
  python backup_scheduler.py manual     # Manual backup now
  python backup_scheduler.py health     # Health check
  python backup_scheduler.py status     # Show status
        """)
        return
    
    scheduler = BackupScheduler()
    command = sys.argv[1].lower()
    
    try:
        if command == "start":
            await scheduler.start_scheduler()
            
        elif command == "health":
            healthy = await scheduler.health_check()
            sys.exit(0 if healthy else 1)
            
        elif command == "manual":
            success = await scheduler.run_immediate_backup("manual")
            sys.exit(0 if success else 1)
            
        elif command == "status":
            status = scheduler.get_status()
            print(json.dumps(status, indent=2))
            
        elif command == "cleanup":
            await scheduler.cleanup_old_backups()
            
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
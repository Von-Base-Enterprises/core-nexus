# 🔐 Core Nexus Database Backup Safety Guide

## Quick Start - Immediate Data Protection

### 1. Set Up Environment
```bash
# Required: Set your PostgreSQL password
export PGVECTOR_PASSWORD="your_secure_password"

# Optional: Verify connection
poetry run python secure_backup_system.py health
```

### 2. Create Your First Backup
```bash
# Create an immediate backup
poetry run python backup_scheduler.py manual

# Verify it worked
poetry run python secure_backup_system.py list
```

### 3. Verify Backup Integrity
```bash
# Check backup integrity
poetry run python secure_backup_system.py verify "backup_name"
```

## ✅ Backup System Status

**Current Implementation:**
- ✅ **Secure credential management** (environment variables)
- ✅ **Full database backup** (all tables + vector embeddings)
- ✅ **Backup integrity verification** (checksums + manifests)
- ✅ **Compressed storage** (gzip compression for space efficiency)
- ✅ **UUID and datetime handling** (proper serialization)
- ✅ **Automated scheduling** (daily/weekly/monthly backups)
- ✅ **Retention policy** (7 daily, 4 weekly, 12 monthly backups)
- ✅ **Backup monitoring** (status tracking and logging)

**What's Backed Up:**
- 📊 **Database Schema** (table structures, extensions)
- 📈 **All Table Data** (memories, graph nodes, relationships, etc.)
- 🧠 **Vector Embeddings** (1,155+ embeddings in efficient binary format)
- 🔍 **Knowledge Graph Data** (entities, relationships, canonicalization)

## 📋 Daily Backup Checklist

### For Manual Backups:
1. **Set Environment Variable**
   ```bash
   export PGVECTOR_PASSWORD="your_password"
   ```

2. **Run Health Check**
   ```bash
   poetry run python secure_backup_system.py health
   ```

3. **Create Backup**
   ```bash
   poetry run python backup_scheduler.py manual
   ```

4. **Verify Success**
   ```bash
   poetry run python backup_scheduler.py status
   ```

### For Automated Backups:
1. **Start Scheduler Daemon**
   ```bash
   # This runs continuously and handles scheduled backups
   poetry run python backup_scheduler.py start
   ```

2. **Monitor Backup Logs**
   ```bash
   tail -f backup_scheduler.log
   ```

## 🛡️ Safety Features

### Data Protection
- **Atomic Operations**: Backups are created completely or not at all
- **Integrity Verification**: MD5 checksums for all backup files
- **Safe Serialization**: Proper handling of UUIDs, dates, and vectors
- **Manifest Files**: Complete inventory of backup contents

### Security
- **No Hardcoded Passwords**: All credentials via environment variables
- **Secure Connections**: SSL/TLS database connections
- **Safe File Handling**: Proper permissions and error handling

### Reliability
- **Connection Testing**: Health checks before operations
- **Error Recovery**: Graceful handling of connection failures
- **Comprehensive Logging**: Detailed logs for troubleshooting
- **Status Tracking**: Historical backup success/failure records

## 📊 Current Database Status

**As of last backup:**
- **Total Records**: 2,569
- **Vector Embeddings**: 1,155
- **Database Size**: ~25.8 MB (compressed)
- **Tables**: 7 (memories, graph_nodes, vector_memories, etc.)

## 🔄 Automated Schedule

When scheduler is running:
- **Daily Backups**: 2:00 AM (keeps 7 days)
- **Weekly Backups**: Sunday 3:00 AM (keeps 4 weeks)
- **Monthly Backups**: 1st of month 4:00 AM (keeps 12 months)
- **Cleanup**: Daily 5:00 AM (removes old backups per retention policy)

## 🚨 Emergency Recovery

### If You Need to Restore Data:
1. **Stop all services** that access the database
2. **Verify backup integrity** before restoring
3. **Use the original backup system** (database_backup_system.py has restore functionality)
4. **Test restored data** before resuming normal operations

⚠️ **Important**: The current secure backup system focuses on backup creation and verification. For restore operations, use the original `database_backup_system.py` script which includes restore functionality.

## 📁 Backup File Structure

```
backups/
├── backup_status.json          # Historical backup status
├── test_backup_safe/           # Example backup directory
│   ├── MANIFEST               # File integrity manifest
│   ├── backup_info.json       # Backup metadata
│   ├── schema.sql             # Database schema
│   ├── *_data.json.gz         # Compressed table data
│   └── vector_embeddings.pkl.gz # Binary vector data
└── manual_backup_YYYYMMDD_HHMMSS/
```

## 🎯 Best Practices

1. **Regular Testing**: Verify backups weekly
2. **Monitor Space**: Keep an eye on backup directory size
3. **Security**: Never commit passwords to git
4. **Documentation**: Update this guide when making changes
5. **Redundancy**: Consider additional off-site backup strategies

## 📞 Quick Commands Reference

```bash
# Health check
poetry run python secure_backup_system.py health

# Manual backup
poetry run python backup_scheduler.py manual

# List all backups
poetry run python secure_backup_system.py list

# Verify specific backup
poetry run python secure_backup_system.py verify "backup_name"

# Check scheduler status
poetry run python backup_scheduler.py status

# Start automated scheduler
poetry run python backup_scheduler.py start

# One-time cleanup of old backups
poetry run python backup_scheduler.py cleanup
```

---

🔒 **Your Core Nexus data is now protected with enterprise-grade backup safety!**
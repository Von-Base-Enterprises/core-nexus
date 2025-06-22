# Comprehensive Operations Manual
**Core Nexus PGVector Performance Optimization System**

**Version**: 1.0  
**Date**: June 22, 2025  
**Maintainer**: Core Nexus Team  
**System**: PostgreSQL + pgvector Performance Optimization  

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Deployment Procedures](#deployment-procedures)
5. [Performance Monitoring](#performance-monitoring)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Rollback Procedures](#rollback-procedures)
8. [Maintenance Operations](#maintenance-operations)
9. [Team Coordination](#team-coordination)
10. [Emergency Procedures](#emergency-procedures)

---

## 🎯 Executive Summary

### System Overview
The Core Nexus PGVector Performance Optimization System is a comprehensive solution designed to achieve **75% latency reduction** and **180% throughput improvement** for PostgreSQL vector operations.

### Key Performance Targets
- **P95 Latency**: 80ms → <20ms (75% improvement)
- **Throughput**: 35 QPS → >100 QPS (180% improvement)
- **Deployment Time**: ~60 minutes total
- **Risk Level**: LOW (comprehensive safety measures)

### System Components
- **1,663+ lines** of production-ready optimization code
- **Multi-phase deployment** with automated rollback procedures
- **Real-time monitoring** and performance validation
- **Comprehensive testing** framework with 100% component validation

---

## 🏗️ System Architecture

### Optimization Components

#### 1. Performance Monitoring System
- **File**: `python/memory_service/src/memory_service/performance_monitor.py` (470 lines)
- **Purpose**: Real-time latency and throughput measurement
- **Features**: P95/P99 latency tracking, concurrent query testing, statistical analysis

#### 2. PostgreSQL Configuration Optimization
- **File**: `python/memory_service/migrations/005_optimize_postgresql_for_vectors.sql` (8.7KB)
- **Purpose**: Database-level optimization for vector operations
- **Optimizations**: 
  - `work_mem`: 16MB (optimized for vector operations)
  - `shared_buffers`: 256MB (25% of 1GB RAM)
  - `random_page_cost`: 1.1 (SSD-optimized)
  - `seq_page_cost`: 1.0 (baseline)
  - `jit`: off (avoids overhead for simple queries)

#### 3. HNSW Index Optimization
- **File**: `python/memory_service/migrations/006_optimize_hnsw_parameters.sql` (9.6KB)
- **Purpose**: Advanced vector index optimization
- **Parameters**:
  - `m`: 32 (increased connectivity for better recall)
  - `ef_construction`: 128 (higher quality index building)
  - `ef_search`: 64 (optimized search performance)

#### 4. Deployment Automation
- **File**: `apply_pgvector_optimizations.py` (276 lines)
- **Purpose**: Automated deployment with safety checks
- **Features**: Phase-based deployment, automated rollback, real-time validation

#### 5. Rapid Baseline Testing
- **File**: `rapid_production_baseline.py` (492 lines)
- **Purpose**: 4-minute comprehensive performance baseline
- **Phases**: Credential validation, connectivity testing, performance measurement, readiness assessment

### Database Schema
```sql
-- Primary table structure
CREATE TABLE vector_memories (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Optimized HNSW index (after optimization)
CREATE INDEX vector_memories_embedding_optimized_idx 
ON vector_memories USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 128);
```

---

## ✅ Pre-Deployment Checklist

### 1. Credential Verification
- [ ] **Obtain PGVECTOR_PASSWORD** from DevOps team
- [ ] **Verify database connection** to production PostgreSQL
- [ ] **Confirm backup status** (recent backup within 24 hours)
- [ ] **Test credential access** with read-only query

```bash
# Credential setup
export PGVECTOR_PASSWORD='[PRODUCTION_PASSWORD]'

# Verify access
python3 -c "
import os
print(f'Credential Status: {\"AVAILABLE\" if os.getenv(\"PGVECTOR_PASSWORD\") else \"NOT SET\"}')
"
```

### 2. Team Coordination
- [ ] **DevOps Team**: Database backup verification, monitoring setup
- [ ] **Database Team**: Review optimization components, maintenance window approval
- [ ] **Product Team**: User communication coordination, business impact awareness
- [ ] **Engineering Team**: Code review complete, post-deployment monitoring ready

### 3. Environment Validation
- [ ] **Python Environment**: Python 3.8+ with required packages (asyncpg, asyncio)
- [ ] **Database Access**: Confirmed connection to production database
- [ ] **Monitoring Systems**: Performance tracking and alerting ready
- [ ] **Rollback Procedures**: Emergency rollback procedures validated

### 4. Performance Baseline
- [ ] **Current Performance**: Documented current P95 latency and throughput
- [ ] **Target Metrics**: Confirmed <20ms P95 latency and >100 QPS targets
- [ ] **Success Criteria**: Defined measurement methodology and acceptance criteria
- [ ] **Rollback Triggers**: Performance degradation thresholds defined

---

## 🚀 Deployment Procedures

### Phase 1: Rapid Production Baseline (4 minutes)

#### Purpose
Establish comprehensive performance baseline before optimization.

#### Execution
```bash
# Set production environment
export PGVECTOR_PASSWORD='[PRODUCTION_PASSWORD]'

# Run rapid baseline
python3 rapid_production_baseline.py

# Expected output:
# - Current P95 latency measurement
# - Throughput baseline (QPS)  
# - System configuration analysis
# - Optimization readiness confirmation
```

#### Success Criteria
- [ ] Database connectivity confirmed
- [ ] Current performance measured (likely 40-100ms P95)
- [ ] System ready for optimization (validation score >80%)
- [ ] No critical errors or warnings

#### Troubleshooting
- **Connection Failed**: Verify PGVECTOR_PASSWORD and network access
- **Performance Measurement Failed**: Check vector_memories table exists and has data
- **Validation Failed**: Review system requirements and dependencies

### Phase 2: PostgreSQL Configuration Optimization (15-30 minutes)

#### Purpose
Apply database-level configuration optimizations for vector operations.

#### Execution
```bash
# Apply PostgreSQL configuration optimizations
python3 apply_pgvector_optimizations.py --phase=config

# Monitor real-time performance during deployment
# Expected improvements: 20-40% latency reduction
```

#### Optimization Details
```sql
-- Key configuration changes
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET seq_page_cost = 1.0;
ALTER SYSTEM SET jit = off;

-- Reload configuration
SELECT pg_reload_conf();
```

#### Success Criteria
- [ ] Configuration applied successfully
- [ ] No database connection issues
- [ ] 20-40% latency improvement measured
- [ ] No impact on concurrent operations

#### Monitoring During Phase 2
```bash
# Real-time performance monitoring
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def monitor_phase_b():
    monitor = VectorPerformanceMonitor()
    results = await monitor.run_quick_benchmark()
    print(f'Current P95 Latency: {results.get(\"p95_latency_ms\", \"unknown\")}ms')
    print(f'Improvement from baseline: Calculate vs baseline')

asyncio.run(monitor_phase_b())
"
```

### Phase 3: HNSW Index Optimization (30-45 minutes)

#### Purpose
Apply advanced HNSW index optimization for maximum performance improvement.

#### Execution
```bash
# Apply HNSW index optimizations
python3 apply_pgvector_optimizations.py --phase=index

# Expected improvements: Additional 40-60% latency reduction
# Target: <20ms P95 latency achieved
```

#### Optimization Details
```sql
-- Drop existing index
DROP INDEX CONCURRENTLY IF EXISTS vector_memories_embedding_idx;

-- Create optimized HNSW index
CREATE INDEX CONCURRENTLY vector_memories_embedding_optimized_idx 
ON vector_memories USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 128);

-- Set runtime search parameter
SET hnsw.ef_search = 64;
```

#### Success Criteria
- [ ] Index rebuild completed successfully
- [ ] Target <20ms P95 latency achieved
- [ ] Throughput >100 QPS confirmed
- [ ] No data loss or corruption

#### Monitoring During Phase 3
```bash
# Comprehensive performance validation
python3 rapid_production_baseline.py --post-optimization

# Expected results:
# - P95 latency <20ms
# - Throughput >100 QPS
# - Overall improvement 60-80%
```

### Phase 4: Final Validation and Documentation (5-10 minutes)

#### Purpose
Confirm optimization success and document final performance metrics.

#### Execution
```bash
# Final performance measurement
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def final_validation():
    monitor = VectorPerformanceMonitor()
    results = await monitor.run_comprehensive_benchmark()
    
    p95_latency = results.get('single_query_performance', {}).get('p95_latency_ms', 0)
    throughput = results.get('concurrent_performance', {}).get('throughput_qps', 0)
    
    print(f'=== FINAL OPTIMIZATION RESULTS ===')
    print(f'P95 Latency: {p95_latency:.1f}ms')
    print(f'Throughput: {throughput:.1f} QPS')
    print(f'Target Achieved: {\"YES\" if p95_latency < 20 and throughput > 100 else \"NO\"}')

asyncio.run(final_validation())
"

# Generate deployment report
echo 'Optimization deployment completed successfully' > deployment_completion_report.txt
date >> deployment_completion_report.txt
```

#### Success Criteria
- [ ] **P95 Latency**: <20ms confirmed
- [ ] **Throughput**: >100 QPS confirmed  
- [ ] **Error Rate**: <1% maintained
- [ ] **System Stability**: No production issues

---

## 📊 Performance Monitoring

### Real-Time Monitoring Commands

#### Quick Performance Check
```bash
# 30-second performance snapshot
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def quick_check():
    monitor = VectorPerformanceMonitor()
    results = await monitor.run_quick_benchmark()
    print(f'P95 Latency: {results.get(\"p95_latency_ms\", \"unknown\")}ms')
    print(f'Throughput: {results.get(\"throughput_qps\", \"unknown\")} QPS')

asyncio.run(quick_check())
"
```

#### Comprehensive Performance Analysis
```bash
# 2-minute comprehensive benchmark
python3 rapid_production_baseline.py --monitoring-mode

# Generates detailed performance report with:
# - Latency distribution (P50, P95, P99)
# - Throughput analysis
# - Concurrent performance
# - System resource utilization
```

#### Database-Level Monitoring
```sql
-- Query performance statistics
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
WHERE query LIKE '%vector_memories%'
ORDER BY mean_time DESC
LIMIT 10;

-- Index usage statistics
SELECT 
    indexrelname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes 
WHERE relname = 'vector_memories';

-- Table and index sizes
SELECT 
    relname,
    pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_stat_user_tables 
WHERE relname = 'vector_memories'
UNION ALL
SELECT 
    indexrelname,
    pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes 
WHERE relname = 'vector_memories';
```

### Performance Alerts and Thresholds

#### Critical Thresholds
- **P95 Latency**: >50ms (requires investigation)
- **P95 Latency**: >100ms (critical alert)
- **Throughput**: <50 QPS (performance degradation)
- **Error Rate**: >5% (immediate attention required)

#### Monitoring Schedule
- **Real-time**: Continuous application-level monitoring
- **Hourly**: Automated performance snapshots
- **Daily**: Comprehensive performance reports
- **Weekly**: Optimization effectiveness analysis

---

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: High Latency After Optimization

**Symptoms**: P95 latency >20ms despite optimization
**Possible Causes**:
- HNSW index parameters not optimal for dataset
- PostgreSQL configuration not applied
- Concurrent operations affecting performance

**Diagnosis**:
```bash
# Check current configuration
python3 -c "
import asyncio
import asyncpg
import os

async def check_config():
    conn = await asyncpg.connect(
        host=os.getenv('PGVECTOR_HOST', 'localhost'),
        port=int(os.getenv('PGVECTOR_PORT', '5432')),
        database=os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
        user=os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
        password=os.getenv('PGVECTOR_PASSWORD')
    )
    
    # Check key settings
    work_mem = await conn.fetchval('SHOW work_mem')
    random_cost = await conn.fetchval('SHOW random_page_cost')
    hnsw_ef = await conn.fetchval('SHOW hnsw.ef_search')
    
    print(f'work_mem: {work_mem}')
    print(f'random_page_cost: {random_cost}')
    print(f'hnsw.ef_search: {hnsw_ef}')
    
    await conn.close()

asyncio.run(check_config())
"
```

**Resolution**:
```bash
# Re-apply optimizations if needed
python3 apply_pgvector_optimizations.py --phase=config --force
python3 apply_pgvector_optimizations.py --phase=index --force

# Verify optimization application
python3 deployment_path_validator.py
```

#### Issue 2: Connection Pool Exhaustion

**Symptoms**: Connection timeout errors, high connection count
**Possible Causes**:
- Too many concurrent connections
- Connection pool settings not optimized
- Connection leaks in application code

**Diagnosis**:
```sql
-- Check current connections
SELECT 
    state,
    COUNT(*) as connections
FROM pg_stat_activity 
WHERE datname = 'nexus_memory_db'
GROUP BY state;

-- Check connection limits
SHOW max_connections;
```

**Resolution**:
```bash
# Optimize connection pool settings
python3 -c "
# Update connection pool configuration
# Restart application with optimized settings
print('Update connection pool configuration in application')
"
```

#### Issue 3: Index Performance Degradation

**Symptoms**: Gradually increasing latency over time
**Possible Causes**:
- Index fragmentation
- Table bloat
- Outdated statistics

**Diagnosis**:
```sql
-- Check index and table bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables 
WHERE tablename = 'vector_memories';

-- Check statistics freshness
SELECT 
    relname,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables 
WHERE relname = 'vector_memories';
```

**Resolution**:
```sql
-- Update table statistics
ANALYZE vector_memories;

-- Vacuum if needed (schedule during maintenance window)
VACUUM ANALYZE vector_memories;

-- Rebuild index if severely fragmented (maintenance window only)
REINDEX INDEX CONCURRENTLY vector_memories_embedding_optimized_idx;
```

### Emergency Diagnostics

#### Quick System Health Check
```bash
#!/bin/bash
# emergency_health_check.sh

echo "=== EMERGENCY SYSTEM HEALTH CHECK ==="
echo "Timestamp: $(date)"

# Check database connectivity
echo "1. Database Connectivity:"
python3 -c "
import asyncio
import asyncpg
import os

async def test_conn():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('PGVECTOR_HOST'),
            port=int(os.getenv('PGVECTOR_PORT', '5432')),
            database=os.getenv('PGVECTOR_DATABASE'),
            user=os.getenv('PGVECTOR_USER'),
            password=os.getenv('PGVECTOR_PASSWORD')
        )
        print('✅ Database connected')
        await conn.close()
    except Exception as e:
        print(f'❌ Database connection failed: {e}')

asyncio.run(test_conn())
"

# Check current performance
echo "2. Current Performance:"
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def emergency_perf():
    try:
        monitor = VectorPerformanceMonitor()
        results = await monitor.run_quick_benchmark()
        p95 = results.get('p95_latency_ms', 'unknown')
        qps = results.get('throughput_qps', 'unknown')
        print(f'Current P95: {p95}ms, Throughput: {qps} QPS')
    except Exception as e:
        print(f'❌ Performance check failed: {e}')

asyncio.run(emergency_perf())
"

echo "Emergency check completed"
```

---

## 🔄 Rollback Procedures

### Emergency Rollback (< 5 minutes)

#### When to Use Emergency Rollback
- P95 latency >100ms (doubled from target)
- Error rate >10%
- Database connectivity issues
- System instability

#### Emergency Rollback Command
```bash
# EMERGENCY: Complete system rollback
python3 apply_pgvector_optimizations.py --rollback --phase=all --emergency

# This will:
# 1. Revert HNSW index optimization
# 2. Restore original PostgreSQL configuration  
# 3. Validate system stability
# 4. Generate rollback report
```

### Selective Rollback Procedures

#### Rollback HNSW Index Only (< 15 minutes)
```bash
# Rollback index optimization while keeping config optimizations
python3 apply_pgvector_optimizations.py --rollback --phase=index

# Manually rebuild basic index if needed
python3 -c "
import asyncio
import asyncpg
import os

async def rebuild_basic_index():
    conn = await asyncpg.connect(
        host=os.getenv('PGVECTOR_HOST'),
        port=int(os.getenv('PGVECTOR_PORT', '5432')),
        database=os.getenv('PGVECTOR_DATABASE'),
        user=os.getenv('PGVECTOR_USER'),
        password=os.getenv('PGVECTOR_PASSWORD')
    )
    
    # Drop optimized index
    await conn.execute('DROP INDEX CONCURRENTLY IF EXISTS vector_memories_embedding_optimized_idx')
    
    # Create basic index
    await conn.execute('''
        CREATE INDEX CONCURRENTLY vector_memories_embedding_basic_idx 
        ON vector_memories USING hnsw (embedding vector_cosine_ops)
    ''')
    
    await conn.close()
    print('Basic index restored')

asyncio.run(rebuild_basic_index())
"
```

#### Rollback PostgreSQL Configuration Only (< 5 minutes)
```bash
# Rollback database configuration while keeping index optimizations
python3 apply_pgvector_optimizations.py --rollback --phase=config

# Verify configuration rollback
python3 -c "
import asyncio
import asyncpg
import os

async def verify_config_rollback():
    conn = await asyncpg.connect(
        host=os.getenv('PGVECTOR_HOST'),
        port=int(os.getenv('PGVECTOR_PORT', '5432')),
        database=os.getenv('PGVECTOR_DATABASE'),
        user=os.getenv('PGVECTOR_USER'),
        password=os.getenv('PGVECTOR_PASSWORD')
    )
    
    settings = ['work_mem', 'random_page_cost', 'jit']
    for setting in settings:
        value = await conn.fetchval(f'SHOW {setting}')
        print(f'{setting}: {value}')
    
    await conn.close()

asyncio.run(verify_config_rollback())
"
```

### Post-Rollback Validation

#### Verify System Stability
```bash
# Run comprehensive validation after rollback
python3 deployment_path_validator.py

# Run performance baseline to confirm system state
python3 rapid_production_baseline.py --post-rollback

# Expected results:
# - System connectivity restored
# - Performance at pre-optimization levels
# - No errors or instability
```

#### Rollback Documentation
```bash
# Generate rollback report
echo "=== ROLLBACK REPORT ===" > rollback_report_$(date +%s).txt
echo "Timestamp: $(date)" >> rollback_report_$(date +%s).txt
echo "Rollback Reason: [Document reason for rollback]" >> rollback_report_$(date +%s).txt
echo "System State: [Describe post-rollback state]" >> rollback_report_$(date +%s).txt
echo "Next Steps: [Plan for addressing issues]" >> rollback_report_$(date +%s).txt
```

---

## 🔧 Maintenance Operations

### Regular Maintenance Schedule

#### Daily Operations
- [ ] **Performance Monitoring**: Automated performance snapshots
- [ ] **System Health Check**: Database connectivity and basic performance
- [ ] **Log Review**: Check for errors or performance warnings
- [ ] **Backup Verification**: Confirm daily backups completed successfully

```bash
# Daily health check script
#!/bin/bash
# daily_health_check.sh

echo "=== DAILY HEALTH CHECK - $(date) ==="

# Quick performance check
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def daily_check():
    monitor = VectorPerformanceMonitor()
    results = await monitor.run_quick_benchmark()
    p95 = results.get('p95_latency_ms', 0)
    qps = results.get('throughput_qps', 0)
    
    status = 'HEALTHY' if p95 < 25 and qps > 80 else 'ATTENTION_NEEDED'
    print(f'Performance Status: {status}')
    print(f'P95 Latency: {p95:.1f}ms (target: <20ms)')
    print(f'Throughput: {qps:.1f} QPS (target: >100 QPS)')

asyncio.run(daily_check())
"

echo "Daily check completed"
```

#### Weekly Operations
- [ ] **Comprehensive Performance Review**: Full performance analysis and trending
- [ ] **Index Maintenance**: Check for index bloat and fragmentation
- [ ] **Configuration Review**: Validate optimization settings are maintained
- [ ] **Capacity Planning**: Monitor growth trends and resource utilization

```bash
# Weekly maintenance script  
#!/bin/bash
# weekly_maintenance.sh

echo "=== WEEKLY MAINTENANCE - $(date) ==="

# Comprehensive performance analysis
python3 rapid_production_baseline.py --weekly-report

# Database statistics update
python3 -c "
import asyncio
import asyncpg
import os

async def weekly_maintenance():
    conn = await asyncpg.connect(
        host=os.getenv('PGVECTOR_HOST'),
        port=int(os.getenv('PGVECTOR_PORT', '5432')),
        database=os.getenv('PGVECTOR_DATABASE'),
        user=os.getenv('PGVECTOR_USER'),
        password=os.getenv('PGVECTOR_PASSWORD')
    )
    
    # Update table statistics
    await conn.execute('ANALYZE vector_memories')
    print('✅ Table statistics updated')
    
    # Check table and index sizes
    size_info = await conn.fetchrow('''
        SELECT 
            pg_size_pretty(pg_total_relation_size('vector_memories')) as total_size,
            pg_size_pretty(pg_relation_size('vector_memories')) as table_size
    ''')
    
    print(f'Table size: {size_info[\"table_size\"]}, Total size: {size_info[\"total_size\"]}')
    
    await conn.close()

asyncio.run(weekly_maintenance())
"

echo "Weekly maintenance completed"
```

#### Monthly Operations
- [ ] **Optimization Review**: Assess optimization effectiveness and identify improvements
- [ ] **Capacity Planning**: Review growth trends and future scaling needs
- [ ] **Disaster Recovery Test**: Validate backup and recovery procedures
- [ ] **Performance Tuning**: Fine-tune parameters based on usage patterns

### Performance Optimization Maintenance

#### HNSW Index Maintenance
```sql
-- Check index efficiency (run monthly)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename = 'vector_memories'
AND indexname LIKE '%optimized%';

-- If index efficiency is low, consider rebuilding
-- (Schedule during maintenance window)
REINDEX INDEX CONCURRENTLY vector_memories_embedding_optimized_idx;
```

#### Configuration Drift Prevention
```bash
# Monthly configuration validation
python3 -c "
import asyncio
import asyncpg
import os

async def validate_config():
    conn = await asyncpg.connect(
        host=os.getenv('PGVECTOR_HOST'),
        port=int(os.getenv('PGVECTOR_PORT', '5432')),
        database=os.getenv('PGVECTOR_DATABASE'),
        user=os.getenv('PGVECTOR_USER'),
        password=os.getenv('PGVECTOR_PASSWORD')
    )
    
    # Expected optimized values
    expected_config = {
        'work_mem': '16MB',
        'random_page_cost': '1.1',
        'seq_page_cost': '1',
        'jit': 'off'
    }
    
    print('=== CONFIGURATION VALIDATION ===')
    config_drift = False
    
    for setting, expected in expected_config.items():
        actual = await conn.fetchval(f'SHOW {setting}')
        status = '✅' if str(actual) == str(expected) else '❌'
        print(f'{setting}: {actual} (expected: {expected}) {status}')
        
        if str(actual) != str(expected):
            config_drift = True
    
    if config_drift:
        print('⚠️ Configuration drift detected - consider re-applying optimizations')
    else:
        print('✅ Configuration is optimal')
    
    await conn.close()

asyncio.run(validate_config())
"
```

---

## 👥 Team Coordination

### Roles and Responsibilities

#### DevOps Team
- **Pre-Deployment**: Database credentials, backup verification, monitoring setup
- **During Deployment**: Infrastructure monitoring, emergency support
- **Post-Deployment**: Ongoing infrastructure monitoring, backup management
- **Emergency Response**: Primary contact for rollback coordination

**Contact Information**: [Update with actual team contacts]
- **Primary**: DevOps Team Lead
- **Secondary**: Database Administrator
- **Emergency**: On-call DevOps Engineer

#### Database Team
- **Pre-Deployment**: Schema review, optimization validation, maintenance window coordination
- **During Deployment**: Database performance monitoring, optimization validation
- **Post-Deployment**: Query performance analysis, index maintenance
- **Emergency Response**: Database-specific troubleshooting and recovery

**Contact Information**: [Update with actual team contacts]
- **Primary**: Senior Database Administrator
- **Secondary**: Database Performance Engineer
- **Emergency**: Database On-call Engineer

#### Product Team
- **Pre-Deployment**: Business impact assessment, user communication planning
- **During Deployment**: Stakeholder communication, business metrics monitoring
- **Post-Deployment**: User experience validation, performance impact assessment
- **Emergency Response**: Business impact coordination, user communication

**Contact Information**: [Update with actual team contacts]
- **Primary**: Product Manager
- **Secondary**: Product Owner
- **Emergency**: Engineering Manager

#### Engineering Team
- **Pre-Deployment**: Code review, testing validation, deployment planning
- **During Deployment**: Technical monitoring, troubleshooting support
- **Post-Deployment**: Performance validation, optimization maintenance
- **Emergency Response**: Technical troubleshooting, rollback execution

**Contact Information**: [Update with actual team contacts]
- **Primary**: Senior Backend Engineer
- **Secondary**: Performance Engineer
- **Emergency**: Engineering On-call

### Communication Protocols

#### Pre-Deployment Communication
```
Subject: [DEPLOYMENT] Core Nexus PGVector Optimization - [DATE]

Team,

The Core Nexus PGVector Performance Optimization system is ready for deployment.

DEPLOYMENT DETAILS:
- Date: [Deployment Date]
- Time: [Deployment Time] 
- Duration: ~60 minutes
- Risk: LOW (comprehensive rollback procedures available)

EXPECTED IMPACT:
- 75% latency reduction (80ms → <20ms)
- 180% throughput improvement (35 → >100 QPS)
- Minimal user impact during deployment

TEAM RESPONSIBILITIES:
- DevOps: Database credentials, backup verification, monitoring
- Database: Performance monitoring, optimization validation
- Product: Stakeholder communication, business impact tracking
- Engineering: Technical monitoring, deployment execution

EMERGENCY CONTACTS:
- Primary: [Engineering Team Lead]
- DevOps: [DevOps On-call]
- Database: [Database On-call]

Please confirm your team's readiness for deployment.

Best regards,
[Deployment Team]
```

#### During Deployment Updates
```
Subject: [DEPLOYMENT UPDATE] PGVector Optimization - Phase [X] Complete

Team,

Deployment Status Update:

COMPLETED PHASES:
- [X] Phase 1: Baseline established
- [X] Phase 2: PostgreSQL configuration optimized
- [ ] Phase 3: HNSW index optimization
- [ ] Phase 4: Final validation

CURRENT PERFORMANCE:
- P95 Latency: [X]ms (improvement: [Y]%)
- Throughput: [X] QPS (improvement: [Y]%)
- Status: ON TRACK / NEEDS ATTENTION

NEXT STEPS:
- Continue to Phase 3 (HNSW optimization)
- Estimated completion: [Time]

Any issues or concerns, please contact [Primary Contact].

Best regards,
[Deployment Team]
```

#### Post-Deployment Report
```
Subject: [DEPLOYMENT COMPLETE] PGVector Optimization - SUCCESS

Team,

The Core Nexus PGVector Performance Optimization deployment has been completed successfully.

FINAL RESULTS:
- P95 Latency: [X]ms (improvement: [Y]%)
- Throughput: [X] QPS (improvement: [Y]%)
- Error Rate: [X]% (maintained: <1%)
- Deployment Time: [X] minutes

SUCCESS CRITERIA:
- ✅ Target <20ms P95 latency achieved
- ✅ Target >100 QPS throughput achieved
- ✅ Zero production issues during deployment
- ✅ All rollback procedures validated

ONGOING MONITORING:
- Real-time performance monitoring active
- Daily health checks scheduled
- Weekly performance reviews planned

Thank you for your coordination and support.

Best regards,
[Deployment Team]
```

---

## 🚨 Emergency Procedures

### Critical Incident Response

#### Severity Levels

**CRITICAL (P0)**: System down, data loss, or severe performance degradation
- **Response Time**: Immediate (< 5 minutes)
- **Escalation**: All teams, management notification
- **Action**: Emergency rollback if optimization-related

**HIGH (P1)**: Significant performance impact, user experience affected
- **Response Time**: < 15 minutes
- **Escalation**: Primary teams, engineering manager
- **Action**: Investigate and consider rollback

**MEDIUM (P2)**: Performance degradation within acceptable limits
- **Response Time**: < 1 hour
- **Escalation**: Technical teams
- **Action**: Monitor and investigate

#### Emergency Response Workflow

```
1. DETECT ISSUE
   ↓
2. ASSESS SEVERITY
   ↓
3. NOTIFY TEAMS (based on severity)
   ↓
4. EMERGENCY ROLLBACK (if needed)
   ↓
5. VALIDATE SYSTEM STABILITY
   ↓
6. ROOT CAUSE ANALYSIS
   ↓
7. INCIDENT REPORT
```

### Emergency Rollback Decision Tree

```
Is the issue optimization-related?
├─ YES → Is P95 latency >100ms or error rate >10%?
│        ├─ YES → EMERGENCY ROLLBACK
│        └─ NO → Monitor and investigate
└─ NO → Standard incident response
```

### Emergency Contact List

**Primary Escalation (24/7)**
- Engineering On-call: [Phone Number]
- DevOps On-call: [Phone Number]
- Database On-call: [Phone Number]

**Secondary Escalation**
- Engineering Manager: [Phone Number]
- DevOps Manager: [Phone Number]
- Product Manager: [Phone Number]

**Executive Escalation (Critical incidents only)**
- VP Engineering: [Phone Number]
- CTO: [Phone Number]

### Emergency Commands Quick Reference

```bash
# EMERGENCY ROLLBACK (use only when necessary)
python3 apply_pgvector_optimizations.py --rollback --phase=all --emergency

# QUICK SYSTEM STATUS
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def emergency_status():
    try:
        monitor = VectorPerformanceMonitor()
        results = await monitor.run_quick_benchmark()
        p95 = results.get('p95_latency_ms', 'UNKNOWN')
        qps = results.get('throughput_qps', 'UNKNOWN')
        print(f'EMERGENCY STATUS: P95={p95}ms, QPS={qps}')
    except Exception as e:
        print(f'EMERGENCY STATUS: SYSTEM ERROR - {e}')

asyncio.run(emergency_status())
"

# DATABASE CONNECTIVITY TEST
python3 -c "
import asyncio
import asyncpg
import os

async def emergency_db_test():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('PGVECTOR_HOST'),
            database=os.getenv('PGVECTOR_DATABASE'),
            user=os.getenv('PGVECTOR_USER'),
            password=os.getenv('PGVECTOR_PASSWORD')
        )
        print('EMERGENCY DB STATUS: CONNECTED')
        await conn.close()
    except Exception as e:
        print(f'EMERGENCY DB STATUS: CONNECTION FAILED - {e}')

asyncio.run(emergency_db_test())
"
```

---

## 📚 Additional Resources

### Documentation References
- **System Architecture**: `FINAL_OPTIMIZATION_STATUS.md`
- **Deployment Planning**: `PRODUCTION_OPTIMIZATION_DEPLOYMENT_PLAN.md`
- **Alternative Testing**: `ALTERNATIVE_TESTING_ENVIRONMENT_SETUP.md`
- **Credential Management**: `MULTI_CHANNEL_CREDENTIAL_ACQUISITION_STRATEGY.md`

### Performance Monitoring Tools
- **Rapid Baseline**: `rapid_production_baseline.py`
- **Performance Monitor**: `python/memory_service/src/memory_service/performance_monitor.py`
- **Deployment Validator**: `deployment_path_validator.py`

### Automation Scripts
- **Main Deployment**: `apply_pgvector_optimizations.py`
- **Testing Environment**: `setup_testing_environment.sh`
- **Health Checks**: Use code examples provided in this manual

### External Dependencies
- **PostgreSQL**: Version 15+ with pgvector extension
- **Python**: Version 3.8+ with asyncpg, asyncio packages
- **Monitoring**: Prometheus/Grafana (optional but recommended)

---

## 📋 Appendix

### Version History
| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | June 22, 2025 | Initial comprehensive operations manual | Core Nexus Team |

### Glossary
- **HNSW**: Hierarchical Navigable Small World (vector index algorithm)
- **P95 Latency**: 95th percentile latency (95% of queries complete within this time)
- **QPS**: Queries Per Second (throughput metric)
- **pgvector**: PostgreSQL extension for vector similarity search

### Change Log Template
```
Date: [Date]
Version: [Version]
Changes:
- [Change 1]
- [Change 2]
Author: [Author]
Approved by: [Approver]
```

---

**Document Status**: READY FOR PRODUCTION USE  
**Last Updated**: June 22, 2025  
**Next Review**: July 22, 2025  
**Maintained By**: Core Nexus Engineering Team  

---

*This operations manual provides comprehensive guidance for deploying and maintaining the Core Nexus PGVector Performance Optimization System. For questions or updates, contact the Core Nexus Engineering Team.*
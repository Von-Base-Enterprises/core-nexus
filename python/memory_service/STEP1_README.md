# 🎯 Step 1: Minimal Production Docker Environment

## Overview

This is **Step 1** of our production simulation setup. The goal is to create the **smallest possible production-like environment** to validate our Core Nexus Memory Service works correctly before adding monitoring, stress testing, and other production features.

## What Step 1 Accomplishes

✅ **Validates Core Service Startup** - Service starts without errors  
✅ **Confirms Docker Environment** - All containers work together  
✅ **Tests Basic Health Checks** - Health endpoint responds correctly  
✅ **Verifies API Endpoints** - Core endpoints are accessible  
✅ **Validates Dependencies** - All Python packages install correctly  

## What Step 1 Does NOT Include

❌ **Monitoring/Metrics** (Step 2)  
❌ **Stress Testing** (Step 3)  
❌ **Log Aggregation** (Step 4)  
❌ **External Dependencies** (OpenAI, Pinecone - Optional)  

## Quick Start

```bash
# 1. Navigate to memory service directory
cd python/memory_service/

# 2. Run the Step 1 deployment
./step1_deploy.sh

# 3. If successful, you'll see:
#    ✅ Step 1 Deployment SUCCESSFUL!
#    📊 Access Points:
#       - API: http://localhost:8000
#       - API Docs: http://localhost:8000/docs
```

## Files Created for Step 1

- `docker-compose.minimal.yml` - Minimal Docker setup (2 services)
- `Dockerfile.minimal` - Simplified production Docker build
- `.env.minimal` - Only required environment variables
- `validate_step1.py` - Health check and validation script
- `step1_deploy.sh` - One-command deployment script

## Step 1 Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │  Memory Service │
│   (pgvector)    │◄───┤   (FastAPI)     │
│   Port: 5432    │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘
```

**Services:**
1. **PostgreSQL with pgvector** - Essential vector database
2. **Memory Service** - Core Nexus API (minimal config)

## Environment Variables (Step 1)

Only **essential** variables are included:

```bash
# Database (Required)
POSTGRES_HOST=postgres
POSTGRES_USER=core_nexus
POSTGRES_PASSWORD=minimal_test_password

# Service (Basic)
SERVICE_NAME=core-nexus-memory-minimal
LOG_LEVEL=INFO

# Providers (Disabled for Step 1)
PINECONE_API_KEY=""           # Empty = disabled
OPENAI_API_KEY=mock_key       # Mock for testing
```

## Validation Tests

The `validate_step1.py` script runs these tests:

1. **Service Startup** - Service responds within 60 seconds
2. **Health Endpoint** - `/health` returns 200 with proper JSON
3. **Basic Endpoints** - `/providers`, `/memories/stats` accessible
4. **Memory Endpoints** - `/memories`, `/memories/query` exist

## Expected Results

### ✅ Success Output
```
🎯 Core Nexus Memory Service - Step 1 Minimal Deployment
========================================================

✅ Prerequisites check passed
🧹 Cleaning up any existing containers...
🔨 Building minimal Docker image...
🚀 Starting minimal production services...
⏳ Waiting for PostgreSQL to be ready...
✅ PostgreSQL is ready
⏳ Waiting for Memory Service to be ready...
✅ Memory Service is ready

🧪 Running Step 1 validation tests...
[HH:MM:SS] INFO: 🚀 Starting Step 1 Validation for Core Nexus Memory Service
[HH:MM:SS] PASS: ✅ Service starts successfully
[HH:MM:SS] PASS: ✅ Health endpoint responds
[HH:MM:SS] PASS: ✅ Health data has status field
[HH:MM:SS] PASS: ✅ Service reports healthy status

🎉 Step 1 Deployment SUCCESSFUL!
```

### ❌ Common Issues

**Issue**: Service fails to start
**Solution**: Check Docker is running, ports 5432/8000 are free

**Issue**: Health check fails
**Solution**: Wait longer for service startup, check logs

**Issue**: Missing dependencies
**Solution**: All dependencies are in `requirements.txt`

## Manual Testing

After successful deployment, test manually:

```bash
# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# Check service logs
docker-compose -f docker-compose.minimal.yml logs -f memory_service
```

## Next Steps

After Step 1 succeeds:

1. **Step 2**: Add Prometheus + Grafana monitoring
2. **Step 3**: Add stress testing suite  
3. **Step 4**: Add log aggregation (Loki + Promtail)
4. **Step 5**: Full production simulation

## Cleanup

```bash
# Stop services
docker-compose -f docker-compose.minimal.yml down

# Remove volumes (if needed)
docker-compose -f docker-compose.minimal.yml down --volumes
```

## Troubleshooting

### View Logs
```bash
# All services
docker-compose -f docker-compose.minimal.yml logs

# Just memory service
docker-compose -f docker-compose.minimal.yml logs memory_service

# Just database
docker-compose -f docker-compose.minimal.yml logs postgres
```

### Debug Container
```bash
# Enter memory service container
docker-compose -f docker-compose.minimal.yml exec memory_service bash

# Check database connection
docker-compose -f docker-compose.minimal.yml exec postgres psql -U core_nexus -d core_nexus_minimal
```

---

## 🎯 Step 1 Success Criteria

- [ ] `docker-compose up` starts without errors
- [ ] `curl localhost:8000/health` returns 200
- [ ] All validation tests pass
- [ ] Service logs show no critical errors
- [ ] Ready to proceed to Step 2

**Step 1 is the foundation** - it must work perfectly before we add complexity!
# Core Nexus Memory Service - Production Deployment Guide

🧠 **Complete production deployment guide for the Core Nexus Long Term Memory Module (LTMM)**

## 🚀 Quick Start (5 Minutes to Production)

```bash
# 1. Clone and setup
git clone <your-repo>
cd core-nexus/python/memory_service

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Deploy with Docker
docker-compose up -d

# 4. Verify deployment
curl http://localhost:8000/health
```

## 📋 Architecture Overview

### Core Components

1. **UnifiedVectorStore** - Multi-provider vector storage orchestration
2. **ADM Scoring Engine** - Automated Decision Making with Darwin-Gödel principles  
3. **Memory Dashboard** - Real-time analytics and monitoring
4. **Usage Tracking** - Performance monitoring and system learning
5. **Vector Providers**:
   - **pgvector** (Primary) - PostgreSQL with vector extensions for SQL queries
   - **ChromaDB** (Local) - Fast local vector storage with no API limits
   - **Pinecone** (Cloud) - Scalable cloud vector database (optional)

### Key Features

- ✅ **Multi-Provider Resilience** - Automatic failover between vector stores
- ✅ **Intelligent Memory Scoring** - ADM system with quality/relevance/intelligence analysis
- ✅ **Real-Time Analytics** - Comprehensive dashboard with performance insights
- ✅ **Self-Evolution** - System learns and improves from usage patterns
- ✅ **Production Ready** - Docker deployment with monitoring and scaling

## 🔧 Prerequisites

### System Requirements

- **OS**: Linux, macOS, or Windows with WSL2
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: 10GB+ available space
- **CPU**: 2+ cores recommended

### Required Software

- Docker & Docker Compose
- PostgreSQL 13+ (with pgvector extension)
- Python 3.11+ (for development)

### Optional Services

- Redis (for advanced caching)
- Nginx (for reverse proxy)
- Prometheus/Grafana (for monitoring)

## 📦 Installation Methods

### Method 1: Docker Compose (Recommended)

```bash
# 1. Create project directory
mkdir core-nexus-memory && cd core-nexus-memory

# 2. Download deployment files
curl -O https://raw.githubusercontent.com/.../docker-compose.yml
curl -O https://raw.githubusercontent.com/.../init-db.sql
curl -O https://raw.githubusercontent.com/.../.env.example

# 3. Configure environment
cp .env.example .env
nano .env  # Update with your settings

# 4. Deploy services
docker-compose up -d

# 5. Check status
docker-compose logs -f memory-service
```

### Method 2: Manual Installation

```bash
# 1. Install PostgreSQL with pgvector
sudo apt update
sudo apt install postgresql-16-pgvector

# 2. Setup Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure database
sudo -u postgres createdb core_nexus
sudo -u postgres psql core_nexus < init-db.sql

# 4. Start service
export POSTGRES_PASSWORD=your_password
python -m uvicorn memory_service.api:app --host 0.0.0.0 --port 8000
```

### Method 3: Kubernetes (Advanced)

```yaml
# See k8s-deployment.yaml for full Kubernetes manifests
apiVersion: apps/v1
kind: Deployment
metadata:
  name: core-nexus-memory
spec:
  replicas: 3
  selector:
    matchLabels:
      app: core-nexus-memory
  template:
    spec:
      containers:
      - name: memory-service
        image: core-nexus/memory-service:latest
        ports:
        - containerPort: 8000
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=core_nexus
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_change_me

# Vector Provider APIs (Optional)
PINECONE_API_KEY=your_pinecone_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Service Configuration
LOG_LEVEL=INFO
WORKERS=4
DEBUG=false

# ADM Configuration
ADM_ENABLED=true
ADM_UPDATE_INTERVAL=3600
EVOLUTION_THRESHOLD=0.1

# Performance Tuning
EMBEDDING_CACHE_SIZE=1000
QUERY_CACHE_TTL=300
MAX_CONCURRENT_QUERIES=50
```

### Provider Priority Configuration

The system automatically configures providers in this priority order:

1. **pgvector** (Primary) - Best for complex queries and ACID compliance
2. **Pinecone** (Cloud Scale) - Best for massive datasets and global distribution  
3. **ChromaDB** (Local Fallback) - Best for development and no-dependency deployment

## 🔐 Security Configuration

### Database Security

```sql
-- Create dedicated application user
CREATE USER memory_service_app WITH PASSWORD 'secure_app_password';

-- Grant minimal required permissions
GRANT USAGE ON SCHEMA public TO memory_service_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO memory_service_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO memory_service_app;

-- Enable row-level security
ALTER TABLE vector_memories ENABLE ROW LEVEL SECURITY;
```

### API Security

```python
# Add authentication middleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.middleware("http")
async def authenticate_request(request: Request, call_next):
    # Implement your authentication logic
    return await call_next(request)
```

### Network Security

```nginx
# nginx.conf - Rate limiting and SSL
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://memory-service:8000;
    }
}
```

## 📊 Monitoring & Health Checks

### Health Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed provider health
curl http://localhost:8000/providers

# Dashboard metrics
curl http://localhost:8000/dashboard/metrics

# ADM performance
curl http://localhost:8000/adm/performance
```

### Performance Monitoring

```bash
# Usage analytics
curl http://localhost:8000/analytics/usage

# Quality trends (last 7 days)
curl http://localhost:8000/dashboard/quality-trends?days=7

# Export comprehensive metrics
curl http://localhost:8000/analytics/export?format=comprehensive
```

### Logging Configuration

```python
# logging.conf
[loggers]
keys=root,memory_service

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler,fileHandler

[logger_memory_service]
level=DEBUG
handlers=fileHandler
qualname=memory_service
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=DEBUG
formatter=simpleFormatter
args=('/app/logs/memory_service.log',)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## 🔄 Backup & Recovery

### Database Backup

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/core-nexus"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump -h localhost -U postgres core_nexus | gzip > $BACKUP_DIR/core_nexus_$DATE.sql.gz

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "core_nexus_*.sql.gz" -mtime +7 -delete
```

### Vector Store Backup

```bash
# ChromaDB backup
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz ./chroma_db/

# pgvector backup (included in database backup)
# Pinecone backup (use Pinecone's backup tools)
```

### Recovery Procedure

```bash
# 1. Stop services
docker-compose down

# 2. Restore database
gunzip -c core_nexus_backup.sql.gz | psql -h localhost -U postgres core_nexus

# 3. Restore ChromaDB
tar -xzf chroma_backup.tar.gz

# 4. Restart services
docker-compose up -d

# 5. Verify health
curl http://localhost:8000/health
```

## 📈 Scaling Strategies

### Vertical Scaling

```yaml
# docker-compose.yml - Increase resources
memory-service:
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 8G
      reservations:
        cpus: '2.0'
        memory: 4G
```

### Horizontal Scaling

```yaml
# Load balancer configuration
services:
  memory-service:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

### Database Scaling

```sql
-- Partition management for high-volume deployments
SELECT maintain_partitions(); -- Automated partition creation

-- Index optimization
REINDEX INDEX CONCURRENTLY vector_memories_embedding_hnsw_idx;

-- Analyze for query optimization
ANALYZE vector_memories;
```

## 🧪 Testing & Validation

### Automated Testing

```bash
# Run comprehensive tests
python -m pytest tests/ -v

# Load testing
python tests/load_test.py --duration=300 --concurrent=50

# Integration testing
python tests/integration_test.py --full-suite
```

### Manual Validation

```bash
# 1. Store test memory
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test memory for validation",
    "metadata": {"test": true},
    "user_id": "test_user"
  }'

# 2. Query memories
curl -X POST http://localhost:8000/memories/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test memory",
    "limit": 5
  }'

# 3. Check ADM analysis
curl -X POST http://localhost:8000/adm/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a test for ADM scoring system"
  }'
```

## 🚨 Troubleshooting

### Common Issues

**1. pgvector Extension Not Found**
```bash
# Solution: Install pgvector extension
sudo apt install postgresql-16-pgvector
sudo -u postgres psql -c "CREATE EXTENSION vector;"
```

**2. ChromaDB Permission Errors**
```bash
# Solution: Fix directory permissions
sudo chown -R 1000:1000 ./chroma_db
chmod -R 755 ./chroma_db
```

**3. High Memory Usage**
```bash
# Solution: Tune cache settings
export EMBEDDING_CACHE_SIZE=500
export QUERY_CACHE_TTL=60
```

**4. Slow Query Performance**
```sql
-- Solution: Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE tablename = 'vector_memories';
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# View detailed logs
docker-compose logs -f memory-service

# Check provider health
curl http://localhost:8000/providers | jq
```

## 📚 API Documentation

### Core Endpoints

- `POST /memories` - Store new memory
- `POST /memories/query` - Query similar memories  
- `GET /health` - Service health check
- `GET /dashboard/metrics` - Dashboard metrics
- `POST /adm/analyze` - ADM content analysis
- `GET /analytics/usage` - Usage analytics

### Full API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI.

## 🔮 Next Steps

### Week 1: Production Deployment
- [ ] Deploy to production environment
- [ ] Configure monitoring and alerting
- [ ] Run load tests and optimize performance
- [ ] Set up automated backups

### Week 2: Advanced Features  
- [ ] Implement memory lifecycle management
- [ ] Add knowledge graph integration
- [ ] Create custom embedding models
- [ ] Implement advanced evolution strategies

### Month 2: Scale and Intelligence
- [ ] Multi-region deployment
- [ ] Advanced ML model integration
- [ ] Custom ADM weight optimization
- [ ] Federated learning across instances

## 🎯 Success Metrics

### Performance Targets
- **Query Response Time**: < 100ms p95
- **Memory Storage Time**: < 50ms p95  
- **System Availability**: > 99.9%
- **ADM Calculation Time**: < 200ms p95

### Quality Targets
- **Average ADM Score**: > 0.65
- **Memory Utilization**: > 80% of stored memories accessed
- **Evolution Success Rate**: > 70% of suggestions improve performance
- **User Satisfaction**: > 4.5/5 feedback score

---

## 🤝 Support

For issues, questions, or contributions:

- 📧 Email: support@core-nexus.ai
- 📝 Issues: [GitHub Issues](https://github.com/core-nexus/memory-service/issues)
- 📖 Documentation: [Core Nexus Docs](https://docs.core-nexus.ai)
- 💬 Community: [Discord Server](https://discord.gg/core-nexus)

---

**🎉 Congratulations! You now have a production-ready Core Nexus Memory Service with:**

✅ Multi-provider vector storage resilience  
✅ Intelligent ADM scoring and evolution  
✅ Real-time analytics and monitoring  
✅ Comprehensive API with 20+ endpoints  
✅ Docker deployment with scaling  
✅ Security, backup, and recovery procedures  

**The foundation for your self-evolving AI system is ready! 🚀**

# 📊 Core Nexus Simple Baseline Report
Generated: 2025-07-21 23:23:59

## 🗄️ Database Status
- Total memories: 1,728
- Current probes setting: 1
- Indexes: 1

## 📈 Current Performance (API)
- Average latency: 341.5ms
- Median latency: 239.5ms
- P90 latency: 528.5ms
- P95 latency: 758.8ms
- Min/Max: 179.3ms / 930.2ms

## 🔬 Probes Sensitivity (Direct DB)
| Probes | Avg Latency | Min | Max |
|--------|-------------|-----|-----|
| 1 | 252.6ms | 94.6ms | 874.1ms |
| 2 | 95.5ms | 92.5ms | 100.6ms |
| 3 | 96.2ms | 92.0ms | 98.5ms |
| 4 | 128.0ms | 93.3ms | 208.3ms |
| 5 | 98.4ms | 92.4ms | 108.7ms |


## 🎯 Key Findings

1. **Current State**:
   - API latency averaging 342ms
   - Using probes=1 (optimal: 2)
   - 21 successful queries tested

2. **Performance Target**:
   - Current P95: 759ms
   - Target: <100ms
   - Gap: 659ms improvement needed

3. **Next Steps**:
   - Implement Redis caching to reduce P50 by ~50%
   - Target 40% cache hit rate
   - Expected P95 after caching: ~455ms

## 📝 Baseline Established
This baseline will be used to measure the effectiveness of Redis caching implementation.

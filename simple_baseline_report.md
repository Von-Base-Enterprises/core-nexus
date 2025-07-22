
# 📊 Core Nexus Simple Baseline Report
Generated: 2025-07-22 00:14:44

## 🗄️ Database Status
- Total memories: 1,728
- Current probes setting: 1
- Indexes: 1

## 📈 Current Performance (API)
- Average latency: 360.8ms
- Median latency: 211.1ms
- P90 latency: 750.1ms
- P95 latency: 801.0ms
- Min/Max: 181.7ms / 892.4ms

## 🔬 Probes Sensitivity (Direct DB)
| Probes | Avg Latency | Min | Max |
|--------|-------------|-----|-----|
| 1 | 253.0ms | 97.8ms | 839.1ms |
| 2 | 96.1ms | 92.3ms | 103.0ms |
| 3 | 98.1ms | 95.8ms | 100.4ms |
| 4 | 100.5ms | 96.0ms | 109.5ms |
| 5 | 101.6ms | 96.7ms | 110.3ms |


## 🎯 Key Findings

1. **Current State**:
   - API latency averaging 361ms
   - Using probes=1 (optimal: 2)
   - 21 successful queries tested

2. **Performance Target**:
   - Current P95: 801ms
   - Target: <100ms
   - Gap: 701ms improvement needed

3. **Next Steps**:
   - Implement Redis caching to reduce P50 by ~50%
   - Target 40% cache hit rate
   - Expected P95 after caching: ~481ms

## 📝 Baseline Established
This baseline will be used to measure the effectiveness of Redis caching implementation.

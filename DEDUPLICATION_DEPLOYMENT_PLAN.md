# Deduplication Deployment Plan

## Environment Variable Setup in Render

Add these environment variables to your Render service:

```bash
DEDUPLICATION_MODE=off
DEDUP_SIMILARITY_THRESHOLD=0.95
DEDUP_EXACT_MATCH_ONLY=false
```

## Phased Rollout Plan

### Phase 1: Deploy with OFF Mode (Day 1)
```bash
DEDUPLICATION_MODE=off
```
- Deploy the code with deduplication completely disabled
- Verify no performance regression
- Ensure all existing functionality works

### Phase 2: Enable Log-Only Mode (Day 2-3)
```bash
DEDUPLICATION_MODE=log_only
```
- Detects duplicates but doesn't prevent them
- Monitor logs for detection accuracy
- Check performance impact
- Gather metrics on duplicate rate

### Phase 3: Active Mode for New Data (Day 4-7)
```bash
DEDUPLICATION_MODE=active
```
- Prevents new duplicates from being stored
- Returns existing memory instead
- Monitor for false positives
- Check user experience

### Phase 4: Strict Mode (Optional - Week 2+)
```bash
DEDUPLICATION_MODE=strict
```
- More aggressive deduplication
- Lower similarity threshold
- Use only after validating accuracy

## Monitoring Checklist

### During Log-Only Mode:
- [ ] Check `/dedup/stats` endpoint hourly
- [ ] Monitor write latency (should stay < 1200ms)
- [ ] Review duplicate detection rate
- [ ] Check for false positives in logs

### During Active Mode:
- [ ] Monitor `duplicates_prevented` counter
- [ ] Check `storage_saved_bytes` metric
- [ ] Watch for user complaints about missing data
- [ ] Verify API response times remain stable

## Quick Commands

### Check deduplication status:
```bash
curl https://core-nexus-memory-service.onrender.com/dedup/stats
```

### Test duplicate detection:
```bash
# Store a memory
curl -X POST https://core-nexus-memory-service.onrender.com/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Test duplicate content"}'

# Try to store same content again
curl -X POST https://core-nexus-memory-service.onrender.com/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Test duplicate content"}'
```

### Emergency Rollback:
In Render dashboard, change:
```bash
DEDUPLICATION_MODE=off
```
Then restart the service.

## Success Criteria

### Log-Only Mode Success:
- Duplicate detection rate 5-20% (expected range)
- No performance degradation > 10%
- No errors in logs

### Active Mode Success:
- Storage savings > 1MB per day
- False positive rate < 1%
- User satisfaction maintained
- Write latency < 1200ms p99

## Risk Mitigation

1. **Start with OFF** - Zero risk deployment
2. **Log-Only first** - Validate detection accuracy
3. **Monitor closely** - Check stats every hour initially
4. **Quick rollback** - Just change env var
5. **Gradual rollout** - One mode at a time

## Recommended Timeline

- **Monday**: Deploy with DEDUPLICATION_MODE=off
- **Tuesday**: Switch to log_only mode
- **Wednesday**: Review metrics, tune threshold if needed
- **Thursday**: Enable active mode if metrics look good
- **Friday**: Full monitoring, prepare weekend runbook
- **Next Week**: Consider strict mode if appropriate

This approach ensures zero risk to production while allowing gradual validation of the deduplication system.
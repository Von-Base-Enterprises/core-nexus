# 🚀 Probes Fix Deployment Checklist

## Pre-Deployment
- [x] Added error handling for probes setting compatibility
- [x] Captured baseline metrics (342ms avg, 759ms P95)
- [x] Verified 100% recall with current configuration
- [x] Created performance regression check scripts
- [x] Committed changes with clear message

## Deployment Steps
1. [ ] Push to main branch
2. [ ] Verify Render auto-deployment triggered
3. [ ] Monitor deployment logs for errors
4. [ ] Wait for deployment to complete (~5-10 minutes)

## Post-Deployment Verification
1. [ ] Run `python3 baseline_metrics_simple.py` to verify:
   - Probes setting applied (should show probes=3 or handle gracefully)
   - Latency improvement (expect ~150ms avg instead of 342ms)
   - P95 < 400ms

2. [ ] Run `python3 simple_recall_test.py` to verify:
   - Recall remains at 100%
   - No quality degradation

3. [ ] Check application logs for:
   - No errors related to probes setting
   - Warning logs if probes not supported (expected for older PostgreSQL)

4. [ ] Run `python3 check_performance_regression.py`:
   - Should pass all checks
   - Generate performance report

## Success Criteria
- [ ] Average latency reduced by >50% (from 342ms to <170ms)
- [ ] P95 latency < 400ms (from 759ms)
- [ ] Recall remains at 100%
- [ ] No increase in errors
- [ ] Performance regression checks pass

## If Issues Occur
1. Check logs for "ivfflat.probes not supported" warnings
2. Verify PostgreSQL version supports pgvector probes
3. Run manual query test:
   ```sql
   SET ivfflat.probes = 3;
   SHOW ivfflat.probes;
   ```

## Next Steps After Success
1. [ ] Update monitoring dashboards with new baseline
2. [ ] Set up weekly performance regression tests
3. [ ] Document in CLAUDE.md that probes=3 is critical
4. [ ] Evaluate if Redis caching is still needed

## Notes
- The error handling ensures the app won't crash if probes isn't supported
- Even without probes optimization, the index still provides benefits
- Monitor for configuration drift in future deployments
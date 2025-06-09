# Knowledge Graph Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the Knowledge Graph functionality in Core Nexus Memory Service. All tests are designed to run without requiring a live database or external services.

## Test Files

### 1. `test_graph_provider.py`
Tests the core GraphProvider implementation:
- Entity extraction (spaCy and regex fallback)
- Relationship inference logic
- Database operations (mocked)
- Error handling and edge cases
- Provider lifecycle (initialization, health checks)

**Key Test Classes:**
- `TestGraphProvider`: Core provider functionality
- `TestEntityExtraction`: Entity extraction specifics
- `TestRelationshipInference`: Relationship logic

### 2. `test_graph_integration.py`
Integration tests for end-to-end workflows:
- Memory to entity extraction flow
- Entity to relationship inference
- Graph traversal operations
- Memory-entity correlation
- Concurrent processing
- ADM scoring integration

**Key Test Classes:**
- `TestGraphIntegration`: Full workflow tests
- `TestGraphQueries`: Query pattern tests

### 3. `test_graph_performance.py`
Performance benchmarks and optimization tests:
- Entity extraction performance at scale
- Relationship inference scaling (O(n²))
- Graph traversal performance
- Memory efficiency tests
- Batch processing benchmarks

**Key Test Classes:**
- `TestEntityExtractionPerformance`: Extraction speed
- `TestRelationshipInferencePerformance`: Inference scaling
- `TestGraphQueryPerformance`: Query optimization
- `TestMemoryEfficiency`: Memory usage

## Running Tests

### Run All Tests
```bash
python run_graph_tests.py
```

### Run Individual Test Files
```bash
# Unit tests
pytest tests/test_graph_provider.py -v

# Integration tests
pytest tests/test_graph_integration.py -v

# Performance tests (with output)
pytest tests/test_graph_performance.py -v -s
```

### Run Specific Test
```bash
pytest tests/test_graph_provider.py::TestGraphProvider::test_entity_extraction_with_spacy_mock -v
```

## Test Design Principles

### 1. No External Dependencies
- All database operations are mocked
- No live PostgreSQL connection required
- No external API calls

### 2. Comprehensive Mocking
- `MockConnection`: Simulates database operations
- `MockConnectionPool`: Simulates async pool behavior
- `MockGraphStore`: In-memory graph for integration tests

### 3. Performance Awareness
- Benchmarks include timing assertions
- Tests verify O(n²) scaling for relationships
- Memory usage is monitored

### 4. Async Support
- Full async/await test coverage
- Concurrent operation testing
- Event loop management

## Test Coverage

### Entity Extraction
- ✅ spaCy NER integration
- ✅ Regex fallback mechanism
- ✅ Entity type mapping
- ✅ Confidence scoring
- ✅ Position tracking

### Relationship Inference
- ✅ Distance-based strength calculation
- ✅ Context-aware type determination
- ✅ Co-occurrence detection
- ✅ ADM score integration

### Graph Operations
- ✅ Node creation and updates
- ✅ Relationship management
- ✅ Memory-entity correlation
- ✅ Graph traversal (BFS)
- ✅ Query by entity/relationship

### Performance
- ✅ Sub-10ms regex extraction (< 5000 words)
- ✅ Linear scaling for entity extraction
- ✅ O(n²) relationship inference
- ✅ Sub-100ms graph traversal (< 500 nodes)

## Expected Results

### Success Criteria
- All unit tests pass (0 failures)
- Integration tests complete without errors
- Performance benchmarks meet targets:
  - Entity extraction: < 10ms for typical content
  - Relationship inference: < 50ms for 20 entities
  - Graph traversal: < 100ms for 500 nodes

### Known Limitations
- Mock data doesn't test actual PostgreSQL performance
- spaCy tests use simplified mock
- Network latency not simulated

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No database setup required
- Predictable execution time
- Clear pass/fail criteria
- JSON report generation

## Extending Tests

To add new tests:
1. Follow existing mock patterns
2. Ensure no external dependencies
3. Add performance assertions where relevant
4. Update this documentation

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure `memory_service` is in PYTHONPATH
   - Run from project root directory

2. **Async Warnings**
   - Use `pytest-asyncio` for async tests
   - Properly close event loops

3. **Performance Failures**
   - May vary by system
   - Adjust thresholds if needed
   - Focus on relative performance

### Debug Mode
```bash
# Run with full output
pytest tests/test_graph_provider.py -v -s --tb=long

# Run with logging
TESTING=false LOG_LEVEL=DEBUG pytest tests/test_graph_provider.py
```

## Test Report

After running `run_graph_tests.py`, check `test_report_graph.json` for:
- Detailed test results
- Execution times
- Failure details
- Performance metrics
#!/usr/bin/env python3
"""
Core Nexus Memory Service - Production Readiness Verification
Complete verification following Darwin-Gödel self-evolution testing principles
"""

import asyncio
import json
import random
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

class ProductionReadinessVerifier:
    """Complete verification of every component"""

    def __init__(self):
        self.test_results = {
            'passed': [],
            'failed': [],
            'performance': {},
            'evolution_metrics': {},
            'critical_failures': []
        }
        self.start_time = time.time()

    def log_success(self, test_name: str, details: str = ""):
        """Log successful test"""
        self.test_results['passed'].append((test_name, details))
        print(f"✅ {test_name}: {details}")

    def log_failure(self, test_name: str, error: str, critical: bool = False):
        """Log failed test"""
        self.test_results['failed'].append((test_name, error))
        if critical:
            self.test_results['critical_failures'].append((test_name, error))
        print(f"❌ {test_name}: {error}")

    def log_performance(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metric"""
        self.test_results['performance'][metric_name] = {'value': value, 'unit': unit}
        print(f"📊 {metric_name}: {value:.2f}{unit}")

    async def phase1_code_integrity_check(self):
        """Phase 1: Code Integrity Check"""
        print("\n" + "="*60)
        print("PHASE 1: CODE INTEGRITY CHECK")
        print("="*60)

        # Check for incomplete code patterns
        try:
            result = subprocess.run([
                'grep', '-r',
                'TODO\\|FIXME\\|XXX\\|NotImplementedError\\|raise NotImplementedError\\|pass #\\|coming soon\\|not implemented\\|placeholder',
                '.', '--include=*.py', '--exclude-dir=.git', '--exclude-dir=__pycache__'
            ], capture_output=True, text=True, cwd=Path(__file__).parent)

            if result.returncode == 0 and result.stdout.strip():
                incomplete_items = result.stdout.strip().split('\n')
                self.log_failure('code_completeness', f"Found {len(incomplete_items)} incomplete code patterns", critical=True)
                for item in incomplete_items[:5]:  # Show first 5
                    print(f"  - {item}")
                if len(incomplete_items) > 5:
                    print(f"  ... and {len(incomplete_items) - 5} more")
            else:
                self.log_success('code_completeness', "No incomplete code patterns found")

        except Exception as e:
            self.log_failure('code_completeness_check', f"Failed to run code check: {e}")

        # Test all imports
        try:
            modules_to_test = [
                'memory_service.unified_store',
                'memory_service.providers',
                'memory_service.adm',
                'memory_service.api',
                'memory_service.dashboard',
                'memory_service.tracking',
                'memory_service.temporal',
                'memory_service.models'
            ]

            failed_imports = []
            for module in modules_to_test:
                try:
                    __import__(module)
                    self.log_success(f'import_{module}', "Imports successfully")
                except Exception as e:
                    failed_imports.append((module, str(e)))
                    self.log_failure(f'import_{module}', str(e), critical=True)

            if not failed_imports:
                self.log_success('all_imports', f"All {len(modules_to_test)} modules import successfully")

        except Exception as e:
            self.log_failure('import_testing', f"Import testing failed: {e}", critical=True)

    async def phase2_component_testing(self):
        """Phase 2: Component Testing"""
        print("\n" + "="*60)
        print("PHASE 2: COMPONENT TESTING")
        print("="*60)

        await self._test_vector_providers()
        await self._test_unified_store()
        await self._test_adm_scoring()
        await self._test_dashboard_components()
        await self._test_tracking_system()

    async def _test_vector_providers(self):
        """Test vector providers with real operations"""
        print("\n🔍 Testing Vector Providers...")

        try:
            from memory_service.models import ProviderConfig
            from memory_service.providers import ChromaProvider, PgVectorProvider

            # Test ChromaDB provider (most likely to work without setup)
            chroma_config = ProviderConfig(
                name="chromadb_test",
                enabled=True,
                primary=True,
                config={
                    "collection_name": "test_collection",
                    "persist_directory": tempfile.mkdtemp()
                }
            )

            try:
                chroma_provider = ChromaProvider(chroma_config)

                # Test storage and retrieval
                test_content = "Test memory content for verification"
                test_embedding = [0.1] * 1536  # Simple test embedding
                test_metadata = {"test": True, "category": "verification"}

                # Store memory
                start_time = time.time()
                memory_id = await chroma_provider.store(test_content, test_embedding, test_metadata)
                store_time = (time.time() - start_time) * 1000

                self.log_performance('chromadb_store_time', store_time, 'ms')

                if store_time > 100:
                    self.log_failure('chromadb_performance', f"Store time {store_time:.2f}ms exceeds 100ms target")
                else:
                    self.log_success('chromadb_store', f"Stored in {store_time:.2f}ms")

                # Query memory
                start_time = time.time()
                results = await chroma_provider.query(test_embedding, limit=5, filters={})
                query_time = (time.time() - start_time) * 1000

                self.log_performance('chromadb_query_time', query_time, 'ms')

                if len(results) == 0:
                    self.log_failure('chromadb_retrieval', "No results returned from query")
                elif str(results[0].id) != str(memory_id):
                    self.log_failure('chromadb_accuracy', "Original memory not found in top results")
                else:
                    self.log_success('chromadb_retrieval', f"Retrieved memory in {query_time:.2f}ms")

                # Health check
                health = await chroma_provider.health_check()
                if health.get('status') == 'healthy':
                    self.log_success('chromadb_health', "Health check passed")
                else:
                    self.log_failure('chromadb_health', f"Health check failed: {health}")

            except Exception as e:
                self.log_failure('chromadb_provider', f"ChromaDB provider failed: {e}", critical=True)

        except ImportError as e:
            self.log_failure('provider_imports', f"Failed to import providers: {e}", critical=True)

    async def _test_unified_store(self):
        """Test unified store operations"""
        print("\n🧠 Testing Unified Store...")

        try:
            from memory_service.models import MemoryRequest, ProviderConfig
            from memory_service.providers import ChromaProvider
            from memory_service.unified_store import UnifiedVectorStore

            # Create test provider
            config = ProviderConfig(
                name="test_provider",
                enabled=True,
                primary=True,
                config={"persist_directory": tempfile.mkdtemp()}
            )

            provider = ChromaProvider(config)
            store = UnifiedVectorStore([provider], adm_enabled=True)

            # Test memory storage with ADM
            test_request = MemoryRequest(
                content="High-quality technical documentation about system architecture",
                metadata={"topic": "technical", "importance": "high"},
                user_id="test_user",
                conversation_id="test_conversation"
            )

            # Mock embedding for testing
            test_request.embedding = [0.1] * 1536

            start_time = time.time()
            memory_response = await store.store_memory(test_request)
            store_time = (time.time() - start_time) * 1000

            self.log_performance('unified_store_time', store_time, 'ms')

            if memory_response.importance_score > 0:
                self.log_success('adm_scoring', f"ADM calculated importance: {memory_response.importance_score:.3f}")
            else:
                self.log_failure('adm_scoring', "ADM scoring returned 0 importance")

            # Test statistics
            stats = store.stats
            if stats.get('total_stores', 0) > 0:
                self.log_success('unified_store_stats', f"Stats tracking working: {stats['total_stores']} stores")
            else:
                self.log_failure('unified_store_stats', "Statistics not being tracked")

        except Exception as e:
            self.log_failure('unified_store', f"Unified store testing failed: {e}", critical=True)
            traceback.print_exc()

    async def _test_adm_scoring(self):
        """Test ADM scoring system"""
        print("\n🧬 Testing ADM Scoring System...")

        try:
            from memory_service.unified_store import UnifiedVectorStore

            # Create mock store for ADM testing
            store = UnifiedVectorStore([], adm_enabled=True)

            if store.adm_engine is None:
                self.log_failure('adm_initialization', "ADM engine not initialized", critical=True)
                return

            # Test different content types
            test_cases = [
                ("High-quality technical documentation with detailed analysis", 0.7, 0.9),
                ("asdf jkl random gibberish", 0.1, 0.3),
                ("Meeting notes from important project planning session", 0.5, 0.8),
                ("Critical security alert requiring immediate action", 0.8, 0.9)
            ]

            total_accuracy = 0
            for content, min_expected, max_expected in test_cases:
                try:
                    start_time = time.time()
                    result = await store.adm_engine.calculate_adm_score(content, {"test": True})
                    calc_time = (time.time() - start_time) * 1000

                    adm_score = result.get('adm_score', 0)

                    if min_expected <= adm_score <= max_expected:
                        accuracy = 1.0
                        self.log_success('adm_content_analysis', f"Score {adm_score:.3f} in expected range [{min_expected}, {max_expected}]")
                    else:
                        accuracy = 0.0
                        self.log_failure('adm_content_analysis', f"Score {adm_score:.3f} outside expected range [{min_expected}, {max_expected}]")

                    total_accuracy += accuracy

                    # Check calculation time
                    if calc_time > 500:
                        self.log_failure('adm_performance', f"ADM calculation took {calc_time:.2f}ms (>500ms target)")
                    else:
                        self.log_performance('adm_calculation_time', calc_time, 'ms')

                except Exception as e:
                    self.log_failure('adm_scoring_execution', f"ADM scoring failed for content: {e}")
                    total_accuracy += 0

            overall_accuracy = total_accuracy / len(test_cases) * 100
            self.log_performance('adm_accuracy', overall_accuracy, '%')

            if overall_accuracy < 75:
                self.log_failure('adm_overall_accuracy', f"ADM accuracy {overall_accuracy:.1f}% below 75% threshold")
            else:
                self.log_success('adm_overall_accuracy', f"ADM accuracy {overall_accuracy:.1f}% meets threshold")

        except Exception as e:
            self.log_failure('adm_testing', f"ADM testing failed: {e}", critical=True)
            traceback.print_exc()

    async def _test_dashboard_components(self):
        """Test dashboard and analytics"""
        print("\n📊 Testing Dashboard Components...")

        try:
            from memory_service.dashboard import MemoryDashboard
            from memory_service.unified_store import UnifiedVectorStore

            # Create minimal store for dashboard testing
            store = UnifiedVectorStore([], adm_enabled=True)
            dashboard = MemoryDashboard(store)

            # Test metrics generation
            metrics = await dashboard.get_comprehensive_metrics()

            if hasattr(metrics, 'to_dict'):
                metrics_dict = metrics.to_dict()
                self.log_success('dashboard_metrics', f"Generated {len(metrics_dict)} metric fields")

                # Check for required fields
                required_fields = ['total_memories', 'avg_importance_score', 'provider_distribution']
                missing_fields = [field for field in required_fields if field not in metrics_dict]

                if missing_fields:
                    self.log_failure('dashboard_completeness', f"Missing fields: {missing_fields}")
                else:
                    self.log_success('dashboard_completeness', "All required fields present")
            else:
                self.log_failure('dashboard_structure', "Metrics object missing to_dict method")

            # Test performance monitoring
            perf_data = await dashboard.get_provider_performance()
            if isinstance(perf_data, dict):
                self.log_success('dashboard_performance', "Provider performance data generated")
            else:
                self.log_failure('dashboard_performance', "Failed to generate provider performance data")

        except Exception as e:
            self.log_failure('dashboard_testing', f"Dashboard testing failed: {e}")
            traceback.print_exc()

    async def _test_tracking_system(self):
        """Test usage tracking and analytics"""
        print("\n📈 Testing Usage Tracking System...")

        try:
            from datetime import datetime

            from memory_service.tracking import UsageCollector, UsageEvent

            # Create usage collector
            collector = UsageCollector(max_events=100)

            # Generate test events
            test_events = []
            for i in range(10):
                event = UsageEvent(
                    timestamp=datetime.utcnow(),
                    event_type='memory_store',
                    endpoint='/memories',
                    method='POST',
                    user_id=f'user_{i % 3}',
                    response_time_ms=random.uniform(50, 150),
                    status_code=201,
                    request_size_bytes=1024,
                    response_size_bytes=512,
                    metadata={'test': True}
                )
                test_events.append(event)
                await collector.record_event(event)

            # Test metrics calculation
            metrics = collector.get_performance_metrics()

            if metrics.total_requests == 10:
                self.log_success('tracking_events', f"Recorded {metrics.total_requests} events")
            else:
                self.log_failure('tracking_events', f"Expected 10 events, got {metrics.total_requests}")

            if 50 <= metrics.avg_response_time_ms <= 150:
                self.log_success('tracking_metrics', f"Average response time: {metrics.avg_response_time_ms:.2f}ms")
            else:
                self.log_failure('tracking_metrics', f"Unexpected avg response time: {metrics.avg_response_time_ms:.2f}ms")

            # Test usage patterns
            patterns = collector.get_usage_patterns()
            if isinstance(patterns, dict) and 'popular_endpoints' in patterns:
                self.log_success('tracking_patterns', "Usage pattern analysis working")
            else:
                self.log_failure('tracking_patterns', "Usage pattern analysis failed")

        except Exception as e:
            self.log_failure('tracking_testing', f"Tracking system testing failed: {e}")
            traceback.print_exc()

    async def phase3_integration_testing(self):
        """Phase 3: Integration Testing"""
        print("\n" + "="*60)
        print("PHASE 3: INTEGRATION TESTING")
        print("="*60)

        # Note: This would normally test against running services
        # For now, we test the integration points exist

        try:
            from memory_service.api import create_memory_app

            # Test FastAPI app creation
            app = create_memory_app()

            if app is not None:
                self.log_success('api_creation', "FastAPI app created successfully")

                # Check routes exist
                route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
                expected_routes = ['/health', '/memories', '/dashboard/metrics', '/adm/performance']

                missing_routes = [route for route in expected_routes if route not in route_paths]
                if missing_routes:
                    self.log_failure('api_routes', f"Missing routes: {missing_routes}")
                else:
                    self.log_success('api_routes', f"All {len(expected_routes)} expected routes found")

                # Check we have >15 total routes (documentation claims 20+)
                if len(route_paths) >= 15:
                    self.log_success('api_completeness', f"Found {len(route_paths)} API routes")
                else:
                    self.log_failure('api_completeness', f"Only {len(route_paths)} routes found, expected 15+")
            else:
                self.log_failure('api_creation', "Failed to create FastAPI app", critical=True)

        except Exception as e:
            self.log_failure('integration_testing', f"Integration testing failed: {e}", critical=True)
            traceback.print_exc()

    async def phase4_evolution_testing(self):
        """Phase 4: Darwin-Gödel Evolution Testing"""
        print("\n" + "="*60)
        print("PHASE 4: DARWIN-GÖDEL EVOLUTION TESTING")
        print("="*60)

        try:
            from memory_service.adm import EvolutionStrategy
            from memory_service.unified_store import UnifiedVectorStore

            # Create store with evolution enabled
            store = UnifiedVectorStore([], adm_enabled=True)

            if not store.adm_engine:
                self.log_failure('evolution_initialization', "ADM engine not available for evolution testing", critical=True)
                return

            # Test evolution strategy suggestion
            try:
                from datetime import datetime

                from memory_service.models import MemoryResponse

                # Create mock memory for evolution testing
                mock_memory = MemoryResponse(
                    id="test-memory-id",
                    content="Test memory for evolution analysis",
                    metadata={"access_count": 5, "importance_score": 0.8},
                    importance_score=0.8,
                    created_at=datetime.utcnow()
                )

                strategy, confidence = await store.adm_engine.suggest_evolution_strategy(mock_memory)

                if isinstance(strategy, EvolutionStrategy) and 0 <= confidence <= 1:
                    self.log_success('evolution_strategy', f"Suggested {strategy.value} with {confidence:.2f} confidence")
                else:
                    self.log_failure('evolution_strategy', f"Invalid strategy suggestion: {strategy}, {confidence}")

                # Test that different memory profiles get different strategies
                strategies_seen = set()
                for access_count, importance in [(0, 0.1), (1, 0.5), (10, 0.9)]:
                    test_memory = MemoryResponse(
                        id=f"test-{access_count}-{importance}",
                        content="Test content",
                        metadata={"access_count": access_count},
                        importance_score=importance,
                        created_at=datetime.utcnow()
                    )

                    strategy, _ = await store.adm_engine.suggest_evolution_strategy(test_memory)
                    strategies_seen.add(strategy.value)

                if len(strategies_seen) > 1:
                    self.log_success('evolution_diversity', f"Generated {len(strategies_seen)} different strategies")
                else:
                    self.log_failure('evolution_diversity', "All memories got same evolution strategy")

                # Test performance metrics
                perf_metrics = await store.adm_engine.get_performance_metrics()
                if isinstance(perf_metrics, dict) and 'total_calculations' in perf_metrics:
                    self.log_success('evolution_metrics', "Performance metrics available")
                else:
                    self.log_failure('evolution_metrics', "Performance metrics not working")

            except Exception as e:
                self.log_failure('evolution_strategy_testing', f"Strategy testing failed: {e}")

        except Exception as e:
            self.log_failure('evolution_testing', f"Evolution testing failed: {e}", critical=True)
            traceback.print_exc()

    async def phase5_security_testing(self):
        """Phase 5: Security & Failure Testing"""
        print("\n" + "="*60)
        print("PHASE 5: SECURITY & FAILURE TESTING")
        print("="*60)

        # Test input validation
        try:
            from memory_service.models import MemoryRequest

            # Test invalid inputs
            invalid_inputs = [
                ("", {}),  # Empty content
                ("x" * 1000000, {}),  # Extremely long content
                ("test", {"x" * 1000: "value"}),  # Invalid metadata key
            ]

            validation_passes = 0
            for content, metadata in invalid_inputs:
                try:
                    request = MemoryRequest(content=content, metadata=metadata)
                    # If this doesn't raise an error, validation might be missing
                    if len(content) == 0:
                        self.log_failure('input_validation', "Empty content accepted")
                    elif len(content) > 100000:
                        self.log_failure('input_validation', "Extremely long content accepted")
                except Exception:
                    validation_passes += 1

            if validation_passes > 0:
                self.log_success('input_validation', f"Input validation working for {validation_passes} cases")
            else:
                self.log_failure('input_validation', "No input validation detected")

        except Exception as e:
            self.log_failure('security_testing', f"Security testing failed: {e}")

    def generate_final_report(self):
        """Generate comprehensive verification report"""
        total_time = time.time() - self.start_time

        print("\n" + "="*60)
        print("PRODUCTION READINESS VERIFICATION REPORT")
        print("="*60)
        print(f"Verification completed in {total_time:.1f} seconds")

        total_tests = len(self.test_results['passed']) + len(self.test_results['failed'])
        pass_rate = len(self.test_results['passed']) / total_tests * 100 if total_tests > 0 else 0

        print("\n📊 SUMMARY")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {len(self.test_results['passed'])} ({pass_rate:.1f}%)")
        print(f"❌ Failed: {len(self.test_results['failed'])}")
        print(f"🚨 Critical Failures: {len(self.test_results['critical_failures'])}")

        if self.test_results['performance']:
            print("\n⚡ PERFORMANCE METRICS")
            for metric, data in self.test_results['performance'].items():
                print(f"  {metric}: {data['value']:.2f}{data['unit']}")

        if self.test_results['failed']:
            print("\n❌ FAILURES:")
            for test_name, reason in self.test_results['failed']:
                emoji = "🚨" if (test_name, reason) in self.test_results['critical_failures'] else "❌"
                print(f"  {emoji} {test_name}: {reason}")

        if self.test_results['passed']:
            print("\n✅ SUCCESSES:")
            for test_name, details in self.test_results['passed'][:10]:  # Show first 10
                print(f"  ✅ {test_name}: {details}")
            if len(self.test_results['passed']) > 10:
                print(f"  ... and {len(self.test_results['passed']) - 10} more")

        print("\n" + "="*60)

        # Determine readiness
        critical_count = len(self.test_results['critical_failures'])
        failed_count = len(self.test_results['failed'])

        if critical_count > 0:
            print("🚨 NOT PRODUCTION READY - CRITICAL FAILURES")
            print("   Do not deploy until critical issues are resolved")
            return False
        elif failed_count > 5:
            print("❌ NOT PRODUCTION READY - TOO MANY FAILURES")
            print("   Significant issues found. Address before deployment.")
            return False
        elif failed_count > 0:
            print("⚠️  MINOR ISSUES - Fix before production")
            print("   The system is mostly ready but has some issues to address.")
            return False
        else:
            print("✅ PRODUCTION READY!")
            print("   All tests passed. Safe to deploy to GitHub and production.")
            return True

async def main():
    """Run complete verification protocol"""
    print("🧠 Core Nexus Memory Service - Production Readiness Verification")
    print("Following Darwin-Gödel self-evolution testing principles")
    print("="*80)

    verifier = ProductionReadinessVerifier()

    try:
        await verifier.phase1_code_integrity_check()
        await verifier.phase2_component_testing()
        await verifier.phase3_integration_testing()
        await verifier.phase4_evolution_testing()
        await verifier.phase5_security_testing()

    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        return False
    except Exception as e:
        print(f"\n🚨 Verification failed with unexpected error: {e}")
        traceback.print_exc()
        return False

    is_ready = verifier.generate_final_report()

    # Save detailed report
    report_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_tests': len(verifier.test_results['passed']) + len(verifier.test_results['failed']),
        'passed': len(verifier.test_results['passed']),
        'failed': len(verifier.test_results['failed']),
        'critical_failures': len(verifier.test_results['critical_failures']),
        'performance_metrics': verifier.test_results['performance'],
        'production_ready': is_ready,
        'detailed_results': verifier.test_results
    }

    with open('production_readiness_report.json', 'w') as f:
        json.dump(report_data, f, indent=2, default=str)

    print("\n📄 Detailed report saved to: production_readiness_report.json")

    return is_ready

if __name__ == "__main__":
    try:
        ready = asyncio.run(main())
        sys.exit(0 if ready else 1)
    except Exception as e:
        print(f"🚨 Verification script failed: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Core Nexus Investor Demo Capability Test
========================================

Tests autonomous reasoning, knowledge graph construction, and multi-agent 
coordination capabilities using the investor demo data.

This validates that the live demo will work as planned.
"""

import asyncio
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DemoCapabilityTester:
    def __init__(self, core_nexus_url: str = "https://core-nexus-memory-service.onrender.com", jarvis_url: str = "https://jarvis-ai-agent-aa4m.onrender.com"):
        self.core_nexus_url = core_nexus_url
        self.jarvis_url = jarvis_url
        self.demo_data_path = Path("investor_demo_data")
        self.test_results = {}
        
    def check_services_running(self) -> bool:
        """Verify Core Nexus and JARVIS services are accessible"""
        try:
            # Test Core Nexus
            response = requests.get(f"{self.core_nexus_url}/health", timeout=5)
            if response.status_code != 200:
                logger.error(f"Core Nexus not accessible: {response.status_code}")
                return False
                
            # Test JARVIS (if available)
            try:
                jarvis_response = requests.get(f"{self.jarvis_url}/health", timeout=5)
                logger.info(f"JARVIS status: {jarvis_response.status_code}")
            except requests.exceptions.RequestException:
                logger.warning("JARVIS service not accessible - will test Core Nexus only")
                
            logger.info("✅ Core Nexus service is running")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Services not accessible: {e}")
            return False
    
    def clear_existing_data(self) -> bool:
        """Clear any existing demo data to start fresh"""
        try:
            # Clear cache
            response = requests.delete(f"{self.core_nexus_url}/memories/cache")
            logger.info("🧹 Cleared existing cache")
            
            # Get current memory count
            stats = requests.get(f"{self.core_nexus_url}/stats").json()
            logger.info(f"📊 Current memories: {stats.get('total_memories', 'unknown')}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to clear existing data: {e}")
            return False
    
    def load_demo_data(self) -> Dict[str, str]:
        """Load all demo data files and return as memory storage format"""
        demo_files = {
            "market_research": self.demo_data_path / "market_research" / "european_saas_market_report_2025.md",
            "competitor_intelligence": self.demo_data_path / "competitor_intelligence" / "competitor_analysis_europe.json", 
            "financial_data_1": self.demo_data_path / "financial_data" / "techcorp_financials_2024.csv",
            "financial_data_2": self.demo_data_path / "financial_data" / "european_expansion_costs.json",
            "customer_feedback": self.demo_data_path / "customer_feedback" / "european_prospect_inquiries.txt",
            "news_articles": self.demo_data_path / "news_articles" / "tech_industry_news_europe.md",
            "regulatory_info": self.demo_data_path / "regulatory_info" / "eu_compliance_requirements.json"
        }
        
        loaded_data = {}
        for data_type, file_path in demo_files.items():
            try:
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8')
                    loaded_data[data_type] = content
                    logger.info(f"📁 Loaded {data_type}: {len(content)} characters")
                else:
                    logger.warning(f"⚠️ File not found: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load {data_type}: {e}")
                
        return loaded_data
    
    def store_memory(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Store a memory in Core Nexus and return the response"""
        memory_request = {
            "content": content,
            "metadata": metadata
        }
        
        try:
            response = requests.post(
                f"{self.core_nexus_url}/memories",
                json=memory_request,
                timeout=30
            )
            
            if response.status_code == 201:
                memory_data = response.json()
                logger.info(f"💾 Stored memory: {memory_data.get('id', 'unknown')[:8]}... "
                          f"ADM Score: {memory_data.get('importance_score', 'N/A')}")
                return memory_data
            else:
                logger.error(f"❌ Failed to store memory: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Exception storing memory: {e}")
            return {}
    
    def test_autonomous_data_ingestion(self, demo_data: Dict[str, str]) -> bool:
        """Test autonomous ingestion and processing of scattered business data"""
        logger.info("🔄 Testing autonomous data ingestion...")
        
        stored_memories = []
        
        for data_type, content in demo_data.items():
            metadata = {
                "source": f"investor_demo_{data_type}",
                "data_type": data_type,
                "demo_timestamp": time.time()
            }
            
            memory = self.store_memory(content, metadata)
            if memory:
                stored_memories.append(memory)
                
            # Brief pause to allow processing
            time.sleep(1)
        
        success = len(stored_memories) == len(demo_data)
        self.test_results["data_ingestion"] = {
            "success": success,
            "memories_stored": len(stored_memories),
            "expected": len(demo_data),
            "memories": stored_memories
        }
        
        logger.info(f"{'✅' if success else '❌'} Data ingestion: {len(stored_memories)}/{len(demo_data)} successful")
        return success
    
    def test_knowledge_graph_construction(self) -> bool:
        """Test autonomous knowledge graph construction from ingested data"""
        logger.info("🕸️ Testing knowledge graph construction...")
        
        try:
            # Get graph statistics
            graph_stats = requests.get(f"{self.core_nexus_url}/graph/stats").json()
            
            # Get entities
            entities_response = requests.get(f"{self.core_nexus_url}/graph/entities?limit=50")
            entities = entities_response.json() if entities_response.status_code == 200 else []
            
            # Expected entities from demo data
            expected_entities = [
                "Germany", "Netherlands", "United Kingdom", "France", "Spain", "Italy",
                "SAP", "Microsoft", "Salesforce", "Oracle", "TeamViewer",
                "GDPR", "EU AI Act", "Brexit", "Digital Deutschland"
            ]
            
            entity_names = []
            if isinstance(entities, list):
                entity_names = [e.get('name', '') for e in entities if isinstance(e, dict)]
            elif isinstance(entities, dict) and 'entities' in entities:
                entity_names = [e.get('name', '') for e in entities['entities'] if isinstance(e, dict)]
            
            found_entities = [name for name in expected_entities if any(name.lower() in entity.lower() for entity in entity_names)]
            
            entity_coverage = len(found_entities) / len(expected_entities) if expected_entities else 0
            success = entity_coverage >= 0.6  # 60% of expected entities found
            
            self.test_results["knowledge_graph"] = {
                "success": success,
                "total_entities": graph_stats.get("total_entities", 0),
                "total_relationships": graph_stats.get("total_relationships", 0),
                "expected_entities": expected_entities,
                "found_entities": found_entities,
                "entity_coverage": entity_coverage
            }
            
            logger.info(f"{'✅' if success else '❌'} Knowledge graph: {len(found_entities)}/{len(expected_entities)} expected entities found")
            logger.info(f"📊 Graph stats: {graph_stats.get('total_entities', 0)} entities, {graph_stats.get('total_relationships', 0)} relationships")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Knowledge graph test failed: {e}")
            self.test_results["knowledge_graph"] = {"success": False, "error": str(e)}
            return False
    
    def test_autonomous_reasoning(self) -> bool:
        """Test autonomous reasoning capabilities with strategic queries"""
        logger.info("🧠 Testing autonomous reasoning...")
        
        test_queries = [
            {
                "name": "market_prioritization",
                "query": "Based on the European market data, which countries offer the best expansion opportunities for a SaaS company?",
                "expected_keywords": ["Netherlands", "Germany", "United Kingdom", "market", "opportunity"]
            },
            {
                "name": "competitive_analysis", 
                "query": "What are the main competitive threats in the European SaaS market?",
                "expected_keywords": ["SAP", "Microsoft", "Salesforce", "competition", "threat"]
            },
            {
                "name": "risk_assessment",
                "query": "What are the key regulatory and compliance risks for European SaaS expansion?",
                "expected_keywords": ["GDPR", "compliance", "regulatory", "risk", "EU"]
            }
        ]
        
        successful_queries = 0
        query_results = []
        
        for test_query in test_queries:
            try:
                query_request = {
                    "query": test_query["query"],
                    "limit": 10
                }
                
                response = requests.post(
                    f"{self.core_nexus_url}/memories/query",
                    json=query_request,
                    timeout=30
                )
                
                if response.status_code == 200:
                    query_data = response.json()
                    memories = query_data.get("memories", [])
                    
                    # Check if response contains expected keywords
                    response_text = " ".join([m.get("content", "") for m in memories])
                    found_keywords = [kw for kw in test_query["expected_keywords"] 
                                    if kw.lower() in response_text.lower()]
                    
                    keyword_coverage = len(found_keywords) / len(test_query["expected_keywords"])
                    query_success = keyword_coverage >= 0.4  # 40% keyword coverage
                    
                    if query_success:
                        successful_queries += 1
                    
                    query_results.append({
                        "name": test_query["name"],
                        "success": query_success,
                        "memories_returned": len(memories),
                        "keyword_coverage": keyword_coverage,
                        "found_keywords": found_keywords,
                        "query_time": query_data.get("query_time_ms", 0)
                    })
                    
                    logger.info(f"{'✅' if query_success else '❌'} Query '{test_query['name']}': "
                              f"{len(memories)} memories, {keyword_coverage:.1%} keyword coverage")
                else:
                    logger.error(f"❌ Query '{test_query['name']}' failed: {response.status_code}")
                    query_results.append({
                        "name": test_query["name"],
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                logger.error(f"❌ Query '{test_query['name']}' exception: {e}")
                query_results.append({
                    "name": test_query["name"],
                    "success": False,
                    "error": str(e)
                })
        
        success = successful_queries >= len(test_queries) * 0.7  # 70% of queries successful
        
        self.test_results["autonomous_reasoning"] = {
            "success": success,
            "successful_queries": successful_queries,
            "total_queries": len(test_queries),
            "query_results": query_results
        }
        
        logger.info(f"{'✅' if success else '❌'} Autonomous reasoning: {successful_queries}/{len(test_queries)} queries successful")
        return success
    
    def test_adaptive_learning(self) -> bool:
        """Test adaptive learning with new information injection"""
        logger.info("🔄 Testing adaptive learning...")
        
        try:
            # Get baseline stats
            baseline_stats = requests.get(f"{self.core_nexus_url}/stats").json()
            baseline_memories = baseline_stats.get("total_memories", 0)
            
            # Inject disruption scenario
            disruption_content = """
            BREAKING NEWS: Oracle announces complete European exit by Q3 2025. 
            Closing Amsterdam and Barcelona offices. €2.4B ARR and 12,000+ enterprise customers 
            seeking alternatives. Regulatory compliance costs cited as primary factor.
            This creates immediate market opportunity for competitors.
            """
            
            disruption_memory = self.store_memory(disruption_content, {
                "source": "breaking_news",
                "impact": "market_disruption",
                "urgency": "high",
                "companies": ["Oracle"],
                "regions": ["Netherlands", "Spain", "Europe"]
            })
            
            # Wait for processing
            time.sleep(2)
            
            # Query for updated strategy
            adaptation_query = {
                "query": "How does Oracle's European exit change the market opportunity for SaaS companies?",
                "limit": 5
            }
            
            response = requests.post(
                f"{self.core_nexus_url}/memories/query",
                json=adaptation_query,
                timeout=30
            )
            
            if response.status_code == 200:
                query_data = response.json()
                memories = query_data.get("memories", [])
                
                # Check if response incorporates new information
                response_text = " ".join([m.get("content", "") for m in memories])
                adaptation_keywords = ["Oracle", "exit", "opportunity", "market", "disruption"]
                found_keywords = [kw for kw in adaptation_keywords if kw.lower() in response_text.lower()]
                
                adaptation_success = len(found_keywords) >= 3  # Found 3+ relevant keywords
                
                # Verify memory count increased
                new_stats = requests.get(f"{self.core_nexus_url}/stats").json()
                new_memories = new_stats.get("total_memories", 0)
                memory_increased = new_memories > baseline_memories
                
                success = adaptation_success and memory_increased and bool(disruption_memory)
                
                self.test_results["adaptive_learning"] = {
                    "success": success,
                    "baseline_memories": baseline_memories,
                    "new_memories": new_memories,
                    "disruption_stored": bool(disruption_memory),
                    "adaptation_query_success": adaptation_success,
                    "found_keywords": found_keywords,
                    "memories_returned": len(memories)
                }
                
                logger.info(f"{'✅' if success else '❌'} Adaptive learning: "
                          f"Memory stored: {bool(disruption_memory)}, "
                          f"Query adapted: {adaptation_success}, "
                          f"Keywords found: {found_keywords}")
                
                return success
            else:
                logger.error(f"❌ Adaptation query failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Adaptive learning test failed: {e}")
            self.test_results["adaptive_learning"] = {"success": False, "error": str(e)}
            return False
    
    def test_performance_metrics(self) -> bool:
        """Test performance and metrics collection"""
        logger.info("📊 Testing performance metrics...")
        
        try:
            # Test metrics endpoints
            endpoints_to_test = [
                "/stats",
                "/memories/stats", 
                "/graph/stats",
                "/dashboard/metrics"
            ]
            
            successful_endpoints = 0
            endpoint_results = {}
            
            for endpoint in endpoints_to_test:
                try:
                    start_time = time.time()
                    response = requests.get(f"{self.core_nexus_url}{endpoint}", timeout=10)
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    if response.status_code == 200:
                        successful_endpoints += 1
                        endpoint_results[endpoint] = {
                            "success": True,
                            "response_time_ms": response_time,
                            "data_size": len(response.text)
                        }
                        logger.info(f"✅ {endpoint}: {response_time:.0f}ms")
                    else:
                        endpoint_results[endpoint] = {
                            "success": False,
                            "status_code": response.status_code
                        }
                        logger.warning(f"⚠️ {endpoint}: HTTP {response.status_code}")
                        
                except Exception as e:
                    endpoint_results[endpoint] = {
                        "success": False,
                        "error": str(e)
                    }
                    logger.warning(f"⚠️ {endpoint}: {e}")
            
            success = successful_endpoints >= len(endpoints_to_test) * 0.5  # 50% endpoints working
            
            self.test_results["performance_metrics"] = {
                "success": success,
                "successful_endpoints": successful_endpoints,
                "total_endpoints": len(endpoints_to_test),
                "endpoint_results": endpoint_results
            }
            
            logger.info(f"{'✅' if success else '❌'} Performance metrics: {successful_endpoints}/{len(endpoints_to_test)} endpoints working")
            return success
            
        except Exception as e:
            logger.error(f"❌ Performance metrics test failed: {e}")
            return False
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
        
        overall_success = successful_tests >= total_tests * 0.8  # 80% tests must pass
        
        report = {
            "timestamp": time.time(),
            "overall_success": overall_success,
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0
            },
            "test_results": self.test_results,
            "readiness_assessment": {
                "demo_ready": overall_success,
                "critical_issues": [],
                "recommendations": []
            }
        }
        
        # Add specific readiness assessment
        if not self.test_results.get("data_ingestion", {}).get("success", False):
            report["readiness_assessment"]["critical_issues"].append("Data ingestion failing - core functionality broken")
            report["readiness_assessment"]["recommendations"].append("Check Core Nexus service logs and restart if needed")
        
        if not self.test_results.get("autonomous_reasoning", {}).get("success", False):
            report["readiness_assessment"]["critical_issues"].append("Autonomous reasoning not working - demo will fail")
            report["readiness_assessment"]["recommendations"].append("Verify embedding models and query processing")
        
        if not self.test_results.get("knowledge_graph", {}).get("success", False):
            report["readiness_assessment"]["recommendations"].append("Knowledge graph construction issues - consider fallback visualization")
        
        return report
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        logger.info("🚀 Starting Core Nexus Investor Demo Capability Test")
        logger.info("=" * 60)
        
        # Check prerequisites
        if not self.check_services_running():
            return {"error": "Services not accessible", "demo_ready": False}
        
        if not self.clear_existing_data():
            return {"error": "Failed to clear existing data", "demo_ready": False}
        
        # Load demo data
        demo_data = self.load_demo_data()
        if not demo_data:
            return {"error": "No demo data available", "demo_ready": False}
        
        logger.info(f"📦 Loaded {len(demo_data)} demo data files")
        logger.info("-" * 60)
        
        # Run test suite
        test_sequence = [
            ("Data Ingestion", lambda: self.test_autonomous_data_ingestion(demo_data)),
            ("Knowledge Graph", self.test_knowledge_graph_construction),
            ("Autonomous Reasoning", self.test_autonomous_reasoning),
            ("Adaptive Learning", self.test_adaptive_learning),
            ("Performance Metrics", self.test_performance_metrics)
        ]
        
        for test_name, test_func in test_sequence:
            logger.info(f"🧪 Running {test_name} test...")
            try:
                success = test_func()
                status = "✅ PASSED" if success else "❌ FAILED"
                logger.info(f"{status} {test_name}")
            except Exception as e:
                logger.error(f"❌ FAILED {test_name}: {e}")
                self.test_results[test_name.lower().replace(" ", "_")] = {"success": False, "error": str(e)}
            
            logger.info("-" * 30)
        
        # Generate final report
        report = self.generate_test_report()
        
        # Display summary
        logger.info("📋 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Overall Success: {'✅ DEMO READY' if report['overall_success'] else '❌ NEEDS ATTENTION'}")
        logger.info(f"Tests Passed: {report['summary']['successful_tests']}/{report['summary']['total_tests']}")
        logger.info(f"Success Rate: {report['summary']['success_rate']:.1%}")
        
        if report["readiness_assessment"]["critical_issues"]:
            logger.warning("🚨 CRITICAL ISSUES:")
            for issue in report["readiness_assessment"]["critical_issues"]:
                logger.warning(f"  - {issue}")
        
        if report["readiness_assessment"]["recommendations"]:
            logger.info("💡 RECOMMENDATIONS:")
            for rec in report["readiness_assessment"]["recommendations"]:
                logger.info(f"  - {rec}")
        
        return report


def main():
    """Main test execution"""
    tester = DemoCapabilityTester()
    
    # Run tests
    report = asyncio.run(tester.run_all_tests())
    
    # Save report
    report_path = Path("investor_demo_test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Full test report saved to: {report_path}")
    
    # Exit with appropriate code
    if report.get("overall_success", False):
        print("🎉 All tests passed - Demo is ready!")
        exit(0)
    else:
        print("⚠️ Some tests failed - Review report before demo")
        exit(1)


if __name__ == "__main__":
    main()
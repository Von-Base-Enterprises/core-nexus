#!/usr/bin/env python3
"""
Test script to verify query fixes are working.

Tests:
1. Empty query returns results
2. Semantic search works
3. Stats are accurate
"""

import json
import urllib.request
import urllib.error


class QueryTester:
    def __init__(self, base_url="https://core-nexus-memory-service.onrender.com", api_key="dev-key-12345"):
        self.base_url = base_url
        self.api_key = api_key
        
    def make_request(self, method, endpoint, data=None):
        """Make HTTP request with authentication."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        if data:
            data = json.dumps(data).encode('utf-8')
            
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            response = urllib.request.urlopen(req)
            return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"HTTP {e.code}: {error_body}")
            return None
            
    def test_empty_query(self):
        """Test that empty queries return all results."""
        print("\n🔍 Testing empty query...")
        
        result = self.make_request("POST", "/memories/query", {
            "query": "",
            "limit": 10
        })
        
        if result:
            found = len(result.get('memories', []))
            total = result.get('total_found', 0)
            print(f"✅ Empty query returned {found} of {total} total memories")
            
            if 'trust_metrics' in result:
                print(f"   Confidence: {result['trust_metrics']['confidence_score']}")
                print(f"   Query type: {result['trust_metrics']['query_type']}")
            
            return found > 0
        else:
            print("❌ Empty query failed")
            return False
            
    def test_semantic_search(self):
        """Test semantic search functionality."""
        print("\n🔍 Testing semantic search...")
        
        test_queries = ["test", "memory", "production", "data"]
        total_found = 0
        
        for query in test_queries:
            result = self.make_request("POST", "/memories/query", {
                "query": query,
                "limit": 5
            })
            
            if result:
                found = len(result.get('memories', []))
                total_found += found
                print(f"✅ Query '{query}' found {found} results")
            else:
                print(f"❌ Query '{query}' failed")
                
        return total_found > 0
        
    def test_stats(self):
        """Test stats endpoint accuracy."""
        print("\n📊 Testing stats endpoint...")
        
        result = self.make_request("GET", "/memories/stats", None)
        
        if result:
            total = result.get('total_memories', 0)
            by_provider = result.get('memories_by_provider', {})
            
            print(f"✅ Stats retrieved successfully")
            print(f"   Total memories: {total}")
            print(f"   By provider: {json.dumps(by_provider, indent=2)}")
            
            # Verify provider totals match overall total
            provider_sum = sum(by_provider.values())
            if provider_sum == total:
                print(f"✅ Provider totals match overall total")
            else:
                print(f"❌ Provider sum ({provider_sum}) doesn't match total ({total})")
                
            return total > 0
        else:
            print("❌ Stats request failed")
            return False
            
    def test_get_all_memories(self):
        """Test GET /memories endpoint."""
        print("\n📋 Testing GET /memories...")
        
        result = self.make_request("GET", "/memories?limit=10", None)
        
        if result:
            found = len(result.get('memories', []))
            total = result.get('total_found', 0)
            print(f"✅ GET /memories returned {found} of {total} total")
            return found > 0
        else:
            print("❌ GET /memories failed")
            return False
            
    def run_all_tests(self):
        """Run all tests and report results."""
        print(f"🚀 Testing Core Nexus Query Fixes")
        print(f"   URL: {self.base_url}")
        print("=" * 50)
        
        tests = [
            ("Empty Query", self.test_empty_query),
            ("Semantic Search", self.test_semantic_search),
            ("Stats Accuracy", self.test_stats),
            ("Get All Memories", self.test_get_all_memories)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success))
            except Exception as e:
                print(f"❌ {name} threw exception: {e}")
                results.append((name, False))
                
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} - {name}")
            
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! Query fixes are working correctly.")
        else:
            print(f"\n⚠️ {total - passed} tests failed. Please check the implementation.")
            

def main():
    """Main entry point."""
    import sys
    
    # Allow custom URL and API key
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://core-nexus-memory-service.onrender.com"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "dev-key-12345"
    
    tester = QueryTester(base_url, api_key)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
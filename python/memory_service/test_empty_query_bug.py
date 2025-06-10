#!/usr/bin/env python3
"""
Test empty query bug comprehensively
"""


import requests


def test_queries():
    base_url = "https://core-nexus-memory-service.onrender.com"

    print("EMPTY QUERY BUG INVESTIGATION")
    print("="*60)

    test_cases = [
        {"query": "", "limit": 10, "description": "Empty string query"},
        {"query": " ", "limit": 10, "description": "Single space query"},
        {"query": "  ", "limit": 10, "description": "Multiple spaces query"},
        {"query": None, "limit": 10, "description": "None/null query"},
        {"query": "", "limit": 1, "description": "Empty with limit 1"},
        {"query": "", "limit": 100, "description": "Empty with limit 100"},
        {"query": "", "limit": 10, "min_similarity": 0.0, "description": "Empty with min_similarity 0"},
        {"query": "a", "limit": 10, "description": "Single letter query"},
        {"query": "VBE", "limit": 10, "description": "Normal query (control)"},
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print("-" * 40)

        # Build payload
        payload = {k: v for k, v in test.items() if k != 'description' and v is not None}

        try:
            response = requests.post(
                f"{base_url}/memories/query",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                print("✓ Status: 200 OK")
                print(f"  Total found: {data.get('total_found', 'N/A')}")
                print(f"  Memories returned: {len(data.get('memories', []))}")
                print(f"  Providers used: {data.get('providers_used', [])}")

                # Check trust metrics
                trust = data.get('trust_metrics', {})
                if trust.get('fix_applied'):
                    print(f"  Fix applied: {trust.get('fix_applied')}")
                    print(f"  Expected behavior: {trust.get('expected_behavior')}")

            else:
                print(f"✗ Status: {response.status_code}")
                print(f"  Error: {response.text[:200]}")

        except Exception as e:
            print(f"✗ Request failed: {str(e)}")

    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)

if __name__ == "__main__":
    test_queries()

#!/usr/bin/env python3
"""
Debug why pgvector is disabled despite correct environment
"""


import requests


def debug_pgvector():
    base_url = "https://core-nexus-memory-service.onrender.com"

    print("DEBUGGING PGVECTOR ISSUE")
    print("="*60)

    # Check environment
    print("\n1. Checking environment variables...")
    try:
        response = requests.get(f"{base_url}/debug/env")
        env_data = response.json()

        print("\nPostgreSQL environment:")
        pg_env = env_data.get('postgresql', {})
        for key, value in pg_env.items():
            if isinstance(value, dict) and 'present' in value:
                print(f"  {key}: {'SET' if value['present'] else 'NOT SET'}")
            else:
                print(f"  {key}: {value}")

        # Check for PGPASSWORD specifically
        print("\nChecking for PGPASSWORD...")
        # The debug endpoint might not show PGPASSWORD

    except Exception as e:
        print(f"Error checking env: {e}")

    # Check health
    print("\n2. Checking health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        health_data = response.json()

        print(f"\nService status: {health_data['status']}")
        print(f"Uptime: {health_data.get('uptime_seconds', 0):.1f} seconds")

        print("\nProvider statuses:")
        for name, info in health_data.get('providers', {}).items():
            status = info.get('status', 'unknown')
            error = info.get('error', '')
            print(f"  {name}: {status}")
            if error:
                print(f"    Error: {error}")

    except Exception as e:
        print(f"Error checking health: {e}")

    # Check logs for startup errors
    print("\n3. Checking recent logs...")
    try:
        response = requests.get(f"{base_url}/debug/logs")
        logs_data = response.json()

        # Look for pgvector initialization logs
        relevant_logs = []
        for log in logs_data.get('logs', []):
            msg = log.get('message', '').lower()
            if 'pgvector' in msg or 'postgresql' in msg or 'password' in msg:
                relevant_logs.append(log)

        if relevant_logs:
            print("\nRelevant log entries:")
            for log in relevant_logs[-5:]:  # Last 5 relevant logs
                print(f"  {log['timestamp']}: {log['message'][:100]}...")
        else:
            print("  No pgvector-related logs found")

    except Exception as e:
        print(f"Error checking logs: {e}")

    # Check database accessibility
    print("\n4. Testing memory operations...")
    try:
        # Try to query memories
        response = requests.post(
            f"{base_url}/memories/query",
            json={"query": "", "limit": 1},
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print("  Query successful!")
            print(f"  Total memories found: {data.get('total_found', 0)}")
            print(f"  Providers used: {data.get('providers_used', [])}")
        else:
            print(f"  Query failed: {response.status_code}")

    except Exception as e:
        print(f"Error querying: {e}")

    print("\n" + "="*60)
    print("DIAGNOSIS:")
    print("="*60)
    print("\nLikely issues:")
    print("1. Service needs restart to pick up PGPASSWORD env var")
    print("2. The env var might be named differently in Render")
    print("3. There might be a connection/network issue")
    print("\nRecommended actions:")
    print("1. Verify PGPASSWORD is set in Render dashboard")
    print("2. Restart the service in Render")
    print("3. Check Render logs for startup errors")
    print("4. Consider adding both PGPASSWORD and PGVECTOR_PASSWORD")

if __name__ == "__main__":
    debug_pgvector()

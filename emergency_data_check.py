#!/usr/bin/env python3
"""
EMERGENCY: Check production data status
"""

import urllib.request
import json
import sys

API_URL = "https://core-nexus-memory-service.onrender.com"

print("🚨 EMERGENCY PRODUCTION DATA CHECK")
print("=" * 50)

# STEP 1: Check stats endpoint
print("\n📊 Checking /memories/stats endpoint...")
try:
    with urllib.request.urlopen(f"{API_URL}/memories/stats") as response:
        stats = json.loads(response.read())
        print(f"Total memories reported: {stats.get('total_memories', 'UNKNOWN')}")
        print("\nMemories by provider:")
        for provider, count in stats.get('memories_by_provider', {}).items():
            print(f"  - {provider}: {count}")
            
        if stats.get('total_memories', 0) == 0:
            print("\n❌ CRITICAL: NO MEMORIES IN PRODUCTION!")
        else:
            print(f"\n✅ Production has {stats.get('total_memories')} memories")
except Exception as e:
    print(f"❌ Stats endpoint error: {e}")

# STEP 2: Check health endpoint for more details
print("\n🏥 Checking /health endpoint...")
try:
    with urllib.request.urlopen(f"{API_URL}/health") as response:
        health = json.loads(response.read())
        print(f"Service status: {health.get('status', 'UNKNOWN')}")
        print("\nProvider details:")
        for provider, details in health.get('providers', {}).items():
            print(f"\n  {provider}:")
            print(f"    Status: {details.get('status', 'UNKNOWN')}")
            if 'details' in details:
                for key, value in details['details'].items():
                    print(f"    {key}: {value}")
            if 'error' in details:
                print(f"    ERROR: {details['error']}")
except Exception as e:
    print(f"❌ Health endpoint error: {e}")

# STEP 3: Test actual query
print("\n🔍 Testing actual query...")
data = json.dumps({
    "query": "test",
    "limit": 5,
    "min_similarity": 0.0
}).encode('utf-8')

req = urllib.request.Request(
    f"{API_URL}/memories/query",
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        memories = len(result.get('memories', []))
        total_found = result.get('total_found', 0)
        print(f"Query returned: {memories} memories")
        print(f"Total found: {total_found}")
        
        if total_found == 0:
            print("\n❌ QUERIES RETURNING NO DATA!")
except Exception as e:
    print(f"❌ Query error: {e}")

# STEP 4: Check debug endpoints
print("\n🔧 Checking debug endpoints...")
try:
    with urllib.request.urlopen(f"{API_URL}/debug/env") as response:
        env = json.loads(response.read())
        print("\nDatabase configuration:")
        pg_config = env.get('postgresql', {})
        print(f"  Host: {pg_config.get('PGVECTOR_HOST', 'UNKNOWN')}")
        print(f"  Database: {pg_config.get('PGVECTOR_DATABASE', 'UNKNOWN')}")
        print(f"  User: {pg_config.get('PGVECTOR_USER', 'UNKNOWN')}")
        print(f"  Password present: {pg_config.get('PGVECTOR_PASSWORD', {}).get('present', False)}")
        
        print(f"\nPrimary provider: {env.get('primary_provider', 'UNKNOWN')}")
        print(f"Embedding model: {env.get('embedding_model', 'UNKNOWN')}")
except Exception as e:
    print(f"❌ Debug endpoint error: {e}")

# STEP 5: Check startup logs
print("\n📜 Checking startup logs...")
try:
    with urllib.request.urlopen(f"{API_URL}/debug/startup-logs") as response:
        logs = json.loads(response.read())
        print(f"Service status: {logs.get('service_status', 'UNKNOWN')}")
        print(f"Uptime: {logs.get('uptime_seconds', 0):.1f} seconds")
        
        print("\nProvider status:")
        for provider, status in logs.get('providers', {}).items():
            print(f"  {provider}: {status.get('status', 'UNKNOWN')} (enabled: {status.get('enabled', False)})")
            
        if logs.get('initialization_errors'):
            print("\n⚠️ Initialization errors:")
            for error in logs['initialization_errors']:
                print(f"  - {error}")
except Exception as e:
    print(f"❌ Startup logs error: {e}")

print("\n" + "=" * 50)
print("EMERGENCY ASSESSMENT:")

# Final assessment
try:
    with urllib.request.urlopen(f"{API_URL}/memories/stats") as response:
        stats = json.loads(response.read())
        total = stats.get('total_memories', 0)
        
        if total == 0:
            print("🚨 CRITICAL: PRODUCTION HAS NO DATA!")
            print("\nPossible causes:")
            print("1. Database connection lost")
            print("2. Wrong database being used")
            print("3. Data was deleted/migrated")
            print("4. Provider initialization failed")
            print("\nIMMEDIATE ACTIONS NEEDED:")
            print("1. Check Render PostgreSQL dashboard")
            print("2. Verify DATABASE_URL in Render env vars")
            print("3. Check recent deployment logs")
            print("4. Look for migration scripts that may have run")
        else:
            print(f"✅ Production has {total} memories")
            print("Data is present, other issues may exist")
except:
    print("❌ Cannot verify data status - API may be down")
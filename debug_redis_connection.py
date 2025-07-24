#!/usr/bin/env python3
"""
Debug Redis connection in production environment.
This script tests Redis connectivity with the same logic as the unified store.
"""
import os
import redis
import json

def test_redis_connection():
    print("🔍 Debug Redis Connection")
    print("========================")
    
    # Check environment variable
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    print(f"REDIS_URL environment variable: {redis_url}")
    
    if not redis_url or redis_url == 'redis://localhost:6379':
        print("❌ REDIS_URL not set or using default localhost")
        return False
    
    try:
        # Test connection with same logic as unified_store
        redis_client = redis.from_url(redis_url, decode_responses=True)
        
        # Test ping
        redis_client.ping()
        print("✅ Redis ping successful")
        
        # Test basic operations
        test_key = "debug_test_key"
        test_data = {"test": "data", "timestamp": "2025-07-22"}
        
        # Test set with JSON serialization (same as in unified_store)
        serialized_data = json.dumps(test_data, default=str)
        redis_client.setex(test_key, 300, serialized_data)
        print("✅ Redis set operation successful")
        
        # Test get
        retrieved_data = redis_client.get(test_key)
        if retrieved_data:
            parsed_data = json.loads(retrieved_data)
            print(f"✅ Redis get operation successful: {parsed_data}")
            
            # Cleanup
            redis_client.delete(test_key)
            print("✅ Test cleanup completed")
            
            return True
        else:
            print("❌ Redis get operation failed - no data retrieved")
            return False
            
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Redis operation failed: {e}")
        return False

def check_cache_type_logic():
    print("\n🔍 Cache Type Detection Logic")
    print("=============================")
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    try:
        import redis
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        cache_type = 'redis'
        print(f"✅ Redis available - cache_type should be: {cache_type}")
        return cache_type
        
    except Exception as e:
        cache_type = 'memory'
        print(f"❌ Redis not available - cache_type should be: {cache_type}")
        print(f"   Error: {e}")
        return cache_type

if __name__ == "__main__":
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {os.environ.get('PYTHONPATH', 'Not set')}")
    print()
    
    redis_connected = test_redis_connection()
    detected_cache_type = check_cache_type_logic()
    
    print(f"\n📊 Summary:")
    print(f"   Redis Connected: {redis_connected}")
    print(f"   Expected Cache Type: {detected_cache_type}")
    
    if redis_connected and detected_cache_type == 'redis':
        print("   ✅ Redis should be working correctly")
    else:
        print("   ❌ Redis configuration issue detected")
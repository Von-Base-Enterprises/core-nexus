#!/usr/bin/env python3
"""
Core Nexus Production Health Check V2
Enhanced version with retry logic and better error handling
"""

import time
from datetime import datetime

from core_nexus_client import CoreNexusClient


def format_time(start: float) -> str:
    """Format elapsed time in milliseconds"""
    return f"{(time.time() - start) * 1000:.0f}ms"

def wait_for_memory(client: CoreNexusClient, memory_id: str, max_retries: int = 5) -> bool:
    """Wait for memory to be available with retries"""
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"  Retry {attempt}/{max_retries}...")
            time.sleep(2)  # Wait 2 seconds between retries

        try:
            # Query all memories
            result = client.query_memories(query="", limit=1000)
            for memory in result.memories:
                if memory.id == memory_id:
                    return True
        except:
            pass

    return False

def main():
    # Initialize client
    client = CoreNexusClient()

    # Generate unique test identifier
    timestamp = datetime.now().isoformat()
    unique_id = f"health-check-{int(time.time())}"

    print("=== Core Nexus Production Health Check V2 ===")
    print(f"Timestamp: {timestamp}")
    print(f"Test ID: {unique_id}")
    print(f"Service URL: {client.base_url}")
    print()

    # First, check service health
    print("Checking service health...")
    start_time = time.time()
    try:
        health = client.check_health()
        print(f"✓ Service is healthy: {health} ({format_time(start_time)})")
    except Exception as e:
        print(f"✗ Service health check failed: {str(e)}")
        return

    # Get initial memory count
    print("\nGetting initial system state...")
    initial_count = None
    try:
        # Query with empty string to get all memories
        result = client.query_memories(query="", limit=1)
        initial_count = result.total_found
        print(f"Current memory count: {initial_count}")
    except Exception as e:
        print(f"Failed to get initial count: {str(e)}")

    # Step 1: Create test memory
    print("\nStep 1: Creating test memory...")
    start_time = time.time()
    memory_id = None
    try:
        memory_result = client.store_memory(
            content=f"Health check test {timestamp}",
            metadata={"test_id": unique_id, "type": "health_check", "timestamp": timestamp}
        )
        memory_id = memory_result.id
        create_time = format_time(start_time)
        print(f"✓ PASS - Memory created with ID: {memory_id} ({create_time})")
    except Exception as e:
        print(f"✗ FAIL - Create failed: {str(e)}")
        return

    # Wait for propagation
    print("\nWaiting for memory propagation...")
    if wait_for_memory(client, memory_id):
        print("✓ Memory is now available in the system")
    else:
        print("✗ Memory not found after retries")

    # Step 2: Query all memories and find ours
    print("\nStep 2: Retrieving memory...")
    start_time = time.time()
    found_memory = None
    try:
        result = client.query_memories(query="", limit=1000)
        for memory in result.memories:
            if memory.id == memory_id:
                found_memory = memory
                break

        if found_memory:
            print(f"✓ PASS - Memory retrieved successfully ({format_time(start_time)})")
            print(f"  Content matches: {found_memory.content == f'Health check test {timestamp}'}")
            print(f"  Metadata matches: {found_memory.metadata.get('test_id') == unique_id}")
            print(f"  Importance score: {found_memory.importance_score}")
        else:
            print(f"✗ FAIL - Memory not found among {result.total_found} memories")
    except Exception as e:
        print(f"✗ FAIL - Retrieve failed: {str(e)}")

    # Step 3: Search by content
    print("\nStep 3: Searching for memory by content...")
    start_time = time.time()
    try:
        search_result = client.query_memories(
            query="Health check test",
            limit=10
        )

        found_position = None
        for i, memory in enumerate(search_result.memories):
            if memory.id == memory_id:
                found_position = i + 1
                print(f"✓ PASS - Memory found at position {found_position} (similarity: {memory.similarity_score:.4f}) ({format_time(start_time)})")
                break

        if not found_position:
            print(f"✗ FAIL - Memory not in search results (found {len(search_result.memories)} memories)")
            # Show what was found
            print("  Top results:")
            for i, mem in enumerate(search_result.memories[:3]):
                print(f"    {i+1}. {mem.content[:50]}... (score: {mem.similarity_score:.4f})")
    except Exception as e:
        print(f"✗ FAIL - Search failed: {str(e)}")

    # Step 4: Test empty query
    print("\nStep 4: Testing empty query (should return all memories)...")
    start_time = time.time()
    try:
        empty_result = client.query_memories(query="", limit=10)
        print(f"✓ PASS - Empty query returned {empty_result.total_found} memories ({format_time(start_time)})")
    except Exception as e:
        print(f"✗ FAIL - Empty query failed: {str(e)}")

    # Step 5: Verify embedding by checking similarity search works
    print("\nStep 5: Verifying vector embedding...")
    start_time = time.time()
    try:
        # Search with exact content should return high similarity
        exact_search = client.query_memories(
            query=f"Health check test {timestamp}",
            limit=5
        )

        for memory in exact_search.memories:
            if memory.id == memory_id and memory.similarity_score > 0.9:
                print(f"✓ PASS - Embedding verified (exact match similarity: {memory.similarity_score:.4f}) ({format_time(start_time)})")
                break
        else:
            print("✗ FAIL - Embedding verification failed")
    except Exception as e:
        print(f"✗ FAIL - Embedding verification error: {str(e)}")

    # Final statistics
    print("\nFinal system state:")
    try:
        final_result = client.query_memories(query="", limit=1)
        final_count = final_result.total_found
        print(f"Total memories: {final_count}")
        if initial_count is not None:
            print(f"Memories added during test: {final_count - initial_count}")
    except:
        print("Failed to get final count")

    print("\n=== Health Check Complete ===")
    print("Note: Delete functionality not available in public API")
    print("Test memory will remain in system")

if __name__ == "__main__":
    main()

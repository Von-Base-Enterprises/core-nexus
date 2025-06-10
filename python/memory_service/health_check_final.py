#!/usr/bin/env python3
"""
Core Nexus Production Health Check - Final Version
Complete end-to-end verification with detailed reporting
"""

import json
import time
from datetime import datetime

from core_nexus_client import CoreNexusClient


def main():
    # Initialize client with production URL
    client = CoreNexusClient()

    print("=== Core Nexus Production Health Check ===")
    print(f"Service URL: {client.base_url}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Results tracking
    results = {
        "timestamp": datetime.now().isoformat(),
        "service_url": client.base_url,
        "steps": {},
        "response_times": {},
        "errors": [],
        "summary": {}
    }

    # Check service health
    print("Checking service health...")
    start = time.time()
    try:
        if client.is_healthy():
            print("✓ Service is healthy")
            health_details = client.get_health_details()
            results["steps"]["health_check"] = "PASS"
            results["summary"]["health_status"] = health_details
        else:
            print("✗ Service is not healthy")
            results["steps"]["health_check"] = "FAIL"
            results["errors"].append("Service health check failed")
            return results
    except Exception as e:
        print(f"✗ Health check error: {str(e)}")
        results["steps"]["health_check"] = "FAIL"
        results["errors"].append(f"Health check error: {str(e)}")
        return results
    results["response_times"]["health_check"] = f"{(time.time() - start) * 1000:.0f}ms"

    # Generate unique test data
    test_id = f"health-{int(time.time())}"
    test_content = f"Health check test at {datetime.now().isoformat()}"

    # Step 1: Create test memory
    print("\nStep 1: Creating test memory...")
    start = time.time()
    memory_id = None
    try:
        memory = client.store_memory(
            content=test_content,
            metadata={
                "test_id": test_id,
                "type": "health_check",
                "timestamp": datetime.now().isoformat()
            },
            importance_score=0.8
        )
        memory_id = memory.id
        results["steps"]["create_memory"] = "PASS"
        results["summary"]["created_memory_id"] = memory_id
        print(f"✓ PASS - Memory created: {memory_id}")
    except Exception as e:
        results["steps"]["create_memory"] = "FAIL"
        results["errors"].append(f"Failed to create memory: {str(e)}")
        print(f"✗ FAIL - {str(e)}")
        return results
    results["response_times"]["create_memory"] = f"{(time.time() - start) * 1000:.0f}ms"

    # Wait for propagation
    print("\nWaiting for memory propagation (3 seconds)...")
    time.sleep(3)

    # Step 2: Retrieve memory by querying all
    print("\nStep 2: Retrieving memory...")
    start = time.time()
    found = False
    try:
        # Query with empty string to get recent memories
        query_result = client.query_memories(query="", limit=100)

        for memory in query_result.memories:
            if memory.id == memory_id:
                found = True
                # Verify content and metadata
                content_match = memory.content == test_content
                metadata_match = memory.metadata.get("test_id") == test_id

                if content_match and metadata_match:
                    results["steps"]["retrieve_memory"] = "PASS"
                    print("✓ PASS - Memory retrieved and verified")
                    print(f"  - Content matches: {content_match}")
                    print(f"  - Metadata matches: {metadata_match}")
                    print(f"  - Importance score: {memory.importance_score}")
                else:
                    results["steps"]["retrieve_memory"] = "FAIL"
                    results["errors"].append("Memory content/metadata mismatch")
                    print("✗ FAIL - Memory data mismatch")
                break

        if not found:
            results["steps"]["retrieve_memory"] = "FAIL"
            results["errors"].append(f"Memory {memory_id} not found among {query_result.total_found} memories")
            print("✗ FAIL - Memory not found")
    except Exception as e:
        results["steps"]["retrieve_memory"] = "FAIL"
        results["errors"].append(f"Retrieve failed: {str(e)}")
        print(f"✗ FAIL - {str(e)}")
    results["response_times"]["retrieve_memory"] = f"{(time.time() - start) * 1000:.0f}ms"

    # Step 3: Search for memory by content
    print("\nStep 3: Searching for memory by content...")
    start = time.time()
    try:
        search_result = client.query_memories(
            query="Health check test",
            limit=10
        )

        position = None
        for i, memory in enumerate(search_result.memories):
            if memory.id == memory_id:
                position = i + 1
                results["steps"]["search_memory"] = "PASS"
                print(f"✓ PASS - Found at position {position} (similarity: {memory.similarity_score:.4f})")
                break

        if not position:
            results["steps"]["search_memory"] = "FAIL"
            results["errors"].append("Memory not in search results")
            print(f"✗ FAIL - Not found in top {len(search_result.memories)} results")

            # Show what was found
            if search_result.memories:
                print("  Top 3 results:")
                for i, mem in enumerate(search_result.memories[:3]):
                    print(f"    {i+1}. {mem.content[:50]}...")
    except Exception as e:
        results["steps"]["search_memory"] = "FAIL"
        results["errors"].append(f"Search failed: {str(e)}")
        print(f"✗ FAIL - {str(e)}")
    results["response_times"]["search_memory"] = f"{(time.time() - start) * 1000:.0f}ms"

    # Step 4: Verify vector embedding
    print("\nStep 4: Verifying vector embedding...")
    start = time.time()
    try:
        # Search with exact content should give high similarity
        exact_result = client.query_memories(
            query=test_content,
            limit=5
        )

        embedding_verified = False
        for memory in exact_result.memories:
            if memory.id == memory_id:
                if memory.similarity_score and memory.similarity_score > 0.9:
                    results["steps"]["verify_embedding"] = "PASS"
                    print(f"✓ PASS - Embedding verified (similarity: {memory.similarity_score:.4f})")
                    embedding_verified = True
                else:
                    results["steps"]["verify_embedding"] = "FAIL"
                    results["errors"].append(f"Low similarity score: {memory.similarity_score}")
                    print(f"✗ FAIL - Low similarity: {memory.similarity_score}")
                break

        if not embedding_verified and "verify_embedding" not in results["steps"]:
            results["steps"]["verify_embedding"] = "FAIL"
            results["errors"].append("Memory not found in exact search")
            print("✗ FAIL - Memory not found in exact search")
    except Exception as e:
        results["steps"]["verify_embedding"] = "FAIL"
        results["errors"].append(f"Embedding verification failed: {str(e)}")
        print(f"✗ FAIL - {str(e)}")
    results["response_times"]["verify_embedding"] = f"{(time.time() - start) * 1000:.0f}ms"

    # Step 5: Cleanup note
    print("\nStep 5: Clean up")
    print("Note: Delete endpoint not available in public API")
    print(f"Test memory {memory_id} will remain in system")
    results["steps"]["cleanup"] = "N/A"

    # Get final stats
    print("\nGetting system statistics...")
    start = time.time()
    try:
        final_result = client.query_memories(query="", limit=1)
        results["summary"]["total_memories"] = final_result.total_found
        print(f"Total memories in system: {final_result.total_found}")
    except Exception as e:
        print(f"Failed to get stats: {str(e)}")

    # Calculate store/retrieve cycle time
    if "create_memory" in results["response_times"] and "retrieve_memory" in results["response_times"]:
        create_ms = float(results["response_times"]["create_memory"].rstrip("ms"))
        retrieve_ms = float(results["response_times"]["retrieve_memory"].rstrip("ms"))
        cycle_time = create_ms + retrieve_ms
        results["summary"]["store_retrieve_cycle_ms"] = cycle_time

        print(f"\nStore/Retrieve cycle: {cycle_time:.0f}ms")
        if cycle_time < 1000:
            print("✓ Performance target met (< 1 second)")
        else:
            print("✗ Performance target missed (> 1 second)")

    # Final summary
    print("\n=== HEALTH CHECK REPORT ===")
    passed = sum(1 for v in results["steps"].values() if v == "PASS")
    failed = sum(1 for v in results["steps"].values() if v == "FAIL")
    na = sum(1 for v in results["steps"].values() if v == "N/A")

    print(f"Steps Passed: {passed}")
    print(f"Steps Failed: {failed}")
    print(f"Not Applicable: {na}")

    overall_status = "PASSED" if failed == 0 else "FAILED"
    results["summary"]["overall_status"] = overall_status

    print(f"\nOverall Status: {overall_status}")

    if results["errors"]:
        print("\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error}")

    # Save results
    with open("health_check_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed report saved to: health_check_report.json")

    return results

if __name__ == "__main__":
    main()

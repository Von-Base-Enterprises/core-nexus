#!/usr/bin/env python3
"""
Monitor the robust extraction progress
"""
import os
import time


def check_process(pid):
    """Check if process is still running"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def monitor_extraction():
    """Monitor extraction progress"""
    pid = 24009
    log_file = "extraction_output.log"

    print("📊 MONITORING ENTITY EXTRACTION PROGRESS")
    print("="*60)
    print(f"Process ID: {pid}")
    print(f"Log file: {log_file}")
    print("="*60)

    start_time = time.time()
    last_size = 0

    while True:
        # Check if process is still running
        if not check_process(pid):
            print("\n✅ Extraction process completed!")
            break

        # Get file size
        try:
            current_size = os.path.getsize(log_file)
            if current_size > last_size:
                # Read new content
                with open(log_file) as f:
                    f.seek(last_size)
                    new_content = f.read()
                    print(new_content, end='')
                last_size = current_size
        except Exception:
            pass

        # Show elapsed time
        elapsed = time.time() - start_time
        print(f"\r⏱️ Elapsed: {elapsed:.0f}s | Status: Extracting...", end="", flush=True)

        time.sleep(2)

    # Show final results
    print("\n\n📋 EXTRACTION COMPLETE - Checking results...")

    # Check for results file
    if os.path.exists("robust_extraction_results.json"):
        print("✅ Results file created: robust_extraction_results.json")

        # Show summary
        import json
        with open("robust_extraction_results.json") as f:
            results = json.load(f)
            print("\n📊 FINAL RESULTS:")
            print(f"  - Memories processed: {results.get('memories_processed', 0)}")
            print(f"  - Entities found: {len(results.get('entities', []))}")
            print(f"  - Relationships: {len(results.get('relationships', []))}")
            print(f"  - Successful batches: {results.get('successful_batches', 0)}")

    print("\n🎉 Monitoring complete!")

if __name__ == "__main__":
    monitor_extraction()

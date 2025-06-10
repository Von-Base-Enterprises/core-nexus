#!/usr/bin/env python3
"""
Monitor the entity extraction progress
"""
import time
import subprocess
import threading

def monitor_progress():
    """Monitor extraction progress in a separate thread."""
    print("\n📊 EXTRACTION PROGRESS MONITOR")
    print("=" * 60)
    
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        print(f"\r⏱️ Elapsed: {elapsed:.0f}s | Status: Extracting entities from 1,008 memories...", end="", flush=True)
        time.sleep(1)

# Start monitoring in background
monitor_thread = threading.Thread(target=monitor_progress)
monitor_thread.daemon = True
monitor_thread.start()

# Run the extraction
cmd = [
    "poetry", "run", "python", 
    "python/memory_service/gemini_mega_context_pipeline.py"
]

env = {
    "PGVECTOR_PASSWORD": "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V",
    "PGVECTOR_HOST": "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com",
    "PGVECTOR_DATABASE": "nexus_memory_db",
    "PGVECTOR_USER": "nexus_memory_db_user",
    "PGVECTOR_PORT": "5432"
}

# Execute and capture output
process = subprocess.Popen(cmd, env={**subprocess.os.environ, **env}, 
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)

# Print output as it comes
for line in process.stdout:
    print(f"\n{line.rstrip()}")

process.wait()
print(f"\n\n✅ Extraction complete! Exit code: {process.returncode}")
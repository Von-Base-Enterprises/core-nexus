#!/usr/bin/env python3
import os
import sys

print("=== Environment Variable Test ===")
print("All environment variables with 'PG' or 'password':")

for key, value in os.environ.items():
    if 'PG' in key.upper() or 'PASSWORD' in key.upper():
        display_value = '***REDACTED***' if 'PASSWORD' in key.upper() else value
        print(f"  {key}: {display_value}")

print(f"\nSpecific checks:")
print(f"PGVECTOR_PASSWORD: {'SET' if os.getenv('PGVECTOR_PASSWORD') else 'NOT SET'}")
print(f"PGPASSWORD: {'SET' if os.getenv('PGPASSWORD') else 'NOT SET'}")
print(f"POSTGRES_PASSWORD: {'SET' if os.getenv('POSTGRES_PASSWORD') else 'NOT SET'}")

# Check sys.argv for any passed variables
print(f"\nCommand line arguments: {sys.argv}")

# Try reading from shell environment
try:
    result = os.popen('echo $PGVECTOR_PASSWORD').read().strip()
    print(f"Shell environment check: {'PASSWORD AVAILABLE' if result else 'NO PASSWORD'}")
except:
    print("Could not check shell environment")
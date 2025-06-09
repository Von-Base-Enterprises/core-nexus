import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Add Python package paths for tests
sys.path.insert(0, str(ROOT / "python" / "example-service" / "src"))
sys.path.insert(0, str(ROOT / "python" / "memory_service" / "src"))
# For packages located directly under python/
sys.path.insert(0, str(ROOT / "python"))

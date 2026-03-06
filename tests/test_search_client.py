import sys
from pathlib import Path
import time
import logging

# Setup path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from saplings.tools.simple_search_client import SimpleSearchClient

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_search_client():
    print("Initializing SimpleSearchClient...")
    start = time.time()
    client = SimpleSearchClient()
    print(f"Initialization took {time.time() - start:.2f}s")
    
    # Test 1: Exact label match
    print("\nTest 1: Search for '1p1e2'")
    start = time.time()
    results = client.search("1p1e2", top_k=5)
    print(f"Search took {time.time() - start:.2f}s")
    
    found = False
    for r in results:
        print(f"  - {r.path} (score={r.score})")
        if "WY6IA" in r.path or "1p1e2" in r.path:
            found = True
            
    if found:
        print("SUCCESS: Found 1p1e2 exact match.")
    else:
        print("FAILURE: Did not find 1p1e2.")

    # Test 2: Content match (slow?)
    print("\nTest 2: Search for '1 + 1 = 2'")
    start = time.time()
    # querying for specific terms that appear in 1p1e2
    # In set.mm, 1 + 1 = 2 is often `1p1e2`.
    # The content of WY6IA.py should contain these symbols? 
    # Actually generated python code uses `c1`, `caddc`, `c2` etc?
    # Or floating args.
    
    results = client.search("1 + 1 = 2", top_k=5)
    print(f"Search took {time.time() - start:.2f}s")
    for r in results:
        print(f"  - {r.path} (score={r.score})")

if __name__ == "__main__":
    test_search_client()

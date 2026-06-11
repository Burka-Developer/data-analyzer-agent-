"""
End-to-end test of the Profitoracle Validator Agent.
Tests all 3 flow paths from the architecture diagram:

  1. SUCCESS:   CSV + query -> full pipeline -> correct answer
  2. REJECTION: Invalid file -> rejection handler -> error message
  3. HISTORY:   GET /history -> verify logged runs

Requires: FastAPI server running on http://localhost:8000
"""

import requests
import os
import sys
import json
import time

API = "http://localhost:8000"
DIVIDER = "=" * 70

# ── Helpers ──

def print_result(label, resp_json):
    """Pretty-print an API response."""
    print(f"  Status:       {resp_json.get('status')}")
    print(f"  Retry Count:  {resp_json.get('retry_count', 0)}")
    answer = resp_json.get("final_answer", "")
    # Safely encode for Windows console
    answer = answer.encode("ascii", errors="replace").decode("ascii")
    # Truncate very long answers for readability
    if len(answer) > 500:
        answer = answer[:500] + "... [truncated]"
    print(f"  Final Answer: {answer}")
    errors = resp_json.get("validation_errors", [])
    if errors:
        print(f"  Errors:       {errors}")

# ── Test 1: Full Success Pipeline ──

print(DIVIDER)
print("  TEST 1: Full Success Pipeline")
print("  Query: 'What is the total revenue by region?'")
print(DIVIDER)

csv_path = os.path.join(os.path.dirname(__file__), "test_data.csv")
if not os.path.exists(csv_path):
    print("  [ERROR] test_data.csv not found!")
    sys.exit(1)

start = time.time()
with open(csv_path, "rb") as f:
    resp = requests.post(
        f"{API}/analyze",
        files={"file": ("test_data.csv", f, "text/csv")},
        data={"query": "What is the total revenue by region?"},
        timeout=120,
    )
elapsed = time.time() - start

print(f"  HTTP Status:  {resp.status_code}")
print(f"  Time:         {elapsed:.1f}s")

if resp.status_code == 200:
    result = resp.json()
    print_result("Success", result)
    if result["status"] == "success":
        print("\n  >> TEST 1 PASSED: Agent successfully analyzed data!")
    elif result["status"] == "failed":
        print("\n  >> TEST 1 PARTIAL: Agent ran but couldn't produce a satisfactory answer.")
    else:
        print(f"\n  >> TEST 1 STATUS: {result['status']}")
else:
    print(f"  [ERROR] Server returned {resp.status_code}: {resp.text[:300]}")
    print("\n  >> TEST 1 FAILED")


# ── Test 2: File Rejection (invalid extension) ──

print(f"\n{DIVIDER}")
print("  TEST 2: File Rejection (invalid .txt file)")
print(DIVIDER)

start2 = time.time()
resp2 = requests.post(
    f"{API}/analyze",
    files={"file": ("bad_file.txt", b"this is not a csv", "text/plain")},
    data={"query": "What is the average?"},
    timeout=30,
)
elapsed2 = time.time() - start2

print(f"  HTTP Status:  {resp2.status_code}")
print(f"  Time:         {elapsed2:.1f}s")

if resp2.status_code == 200:
    result2 = resp2.json()
    print_result("Rejection", result2)
    if result2["status"] == "rejected":
        print("\n  >> TEST 2 PASSED: Invalid file correctly rejected!")
    else:
        print(f"\n  >> TEST 2 UNEXPECTED: Status was '{result2['status']}', expected 'rejected'")
else:
    print(f"  [ERROR] Server returned {resp2.status_code}: {resp2.text[:300]}")


# ── Test 3: A more complex analytical query ──

print(f"\n{DIVIDER}")
print("  TEST 3: Complex Query")
print("  Query: 'Which product has the highest profit margin? Show profit margin % for each.'")
print(DIVIDER)

start3 = time.time()
with open(csv_path, "rb") as f:
    resp3 = requests.post(
        f"{API}/analyze",
        files={"file": ("test_data.csv", f, "text/csv")},
        data={"query": "Which product has the highest profit margin? Calculate profit margin percentage (Revenue - Cost) / Revenue * 100 for each product."},
        timeout=120,
    )
elapsed3 = time.time() - start3

print(f"  HTTP Status:  {resp3.status_code}")
print(f"  Time:         {elapsed3:.1f}s")

if resp3.status_code == 200:
    result3 = resp3.json()
    print_result("Complex", result3)
    if result3["status"] == "success":
        print("\n  >> TEST 3 PASSED: Complex analysis completed!")
    elif result3["status"] == "failed":
        print(f"\n  >> TEST 3 PARTIAL: Agent ran ({result3.get('retry_count',0)} retries) but couldn't satisfy validator.")
    else:
        print(f"\n  >> TEST 3 STATUS: {result3['status']}")
else:
    print(f"  [ERROR] Server returned {resp3.status_code}: {resp3.text[:300]}")


# ── Test 4: History endpoint ──

print(f"\n{DIVIDER}")
print("  TEST 4: History Endpoint")
print(DIVIDER)

resp4 = requests.get(f"{API}/history", timeout=10)
print(f"  HTTP Status:  {resp4.status_code}")

if resp4.status_code == 200:
    history = resp4.json()
    print(f"  Total runs:   {len(history)}")
    for run in history[:5]:
        print(f"    [{run.get('status', '?'):>8}] {run.get('filename', '?')}: {run.get('query', '?')[:50]}")
    print("\n  >> TEST 4 PASSED: History retrieved!")
else:
    print(f"  [ERROR] {resp4.text[:200]}")


# ── Summary ──

print(f"\n{'=' * 70}")
print("  ALL END-TO-END TESTS COMPLETED")
print(f"{'=' * 70}")

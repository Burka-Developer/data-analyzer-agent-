"""
Test the /analyze endpoint with various scenarios.
"""
import requests
import os
import tempfile

API = "http://localhost:7860"

# ─── Test 1: Valid CSV with file validation (will fail at LLM call if no API key) ───
print("=" * 60)
print("Test 1: Upload valid CSV")
csv_data = "region,revenue,quarter\nEast,100,Q1\nWest,200,Q1\nEast,150,Q2\nWest,250,Q2\n"
csv_path = os.path.join("uploads", "test_valid.csv")
os.makedirs("uploads", exist_ok=True)
with open(csv_path, "w") as f:
    f.write(csv_data)

with open(csv_path, "rb") as f:
    resp = requests.post(
        f"{API}/analyze",
        files={"file": ("test_valid.csv", f, "text/csv")},
        data={"query": "What is the total revenue by region?"},
        timeout=60,
    )
print(f"  Status code: {resp.status_code}")
print(f"  Response: {resp.json()}")
os.remove(csv_path)

# ─── Test 2: Invalid file extension ───
print("\n" + "=" * 60)
print("Test 2: Upload invalid file type (.txt)")
txt_path = os.path.join("uploads", "test_bad.txt")
with open(txt_path, "w") as f:
    f.write("not a csv")

with open(txt_path, "rb") as f:
    resp = requests.post(
        f"{API}/analyze",
        files={"file": ("test_bad.txt", f, "text/plain")},
        data={"query": "What is the total?"},
        timeout=30,
    )
print(f"  Status code: {resp.status_code}")
print(f"  Response: {resp.json()}")
os.remove(txt_path)

# ─── Test 3: Empty file ───
print("\n" + "=" * 60)
print("Test 3: Upload empty CSV")
empty_path = os.path.join("uploads", "test_empty.csv")
with open(empty_path, "w") as f:
    pass  # empty file

with open(empty_path, "rb") as f:
    resp = requests.post(
        f"{API}/analyze",
        files={"file": ("test_empty.csv", f, "text/csv")},
        data={"query": "Anything?"},
        timeout=30,
    )
print(f"  Status code: {resp.status_code}")
print(f"  Response: {resp.json()}")
os.remove(empty_path)

# ─── Test 4: History endpoint ───
print("\n" + "=" * 60)
print("Test 4: GET /history")
resp = requests.get(f"{API}/history", timeout=10)
print(f"  Status code: {resp.status_code}")
runs = resp.json()
print(f"  Total runs in DB: {len(runs)}")
for run in runs[:3]:
    print(f"    - {run.get('filename')} | {run.get('status')} | {run.get('query', '')[:40]}")

print("\n" + "=" * 60)
print("ALL ENDPOINT TESTS COMPLETE")

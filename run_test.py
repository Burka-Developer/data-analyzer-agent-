"""
Quick end-to-end test of the Profitoracle agent API.
Tests: /health, /analyze (valid CSV), /analyze (bad file), /history
"""

import requests
import os
import json
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data.csv")


def separator(title):
    print(f"\n{'='*60}")
    print(f"  TEST: {title}")
    print(f"{'='*60}\n")


def test_health():
    separator("GET /health")
    r = requests.get(f"{BASE}/health")
    print(f"  Status Code: {r.status_code}")
    print(f"  Response:    {r.json()}")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print(f"  [PASS]")


def test_analyze_valid():
    separator("POST /analyze -- Valid CSV + Query")
    query = "Which product has the highest total profit across all months? Profit = Revenue - Cost."
    print(f"  Query: {query}")
    print(f"  File:  test_data.csv (12 rows x 6 cols)")
    print(f"  Calling agent pipeline (this may take 15-30 seconds)...\n")

    with open(CSV_PATH, "rb") as f:
        r = requests.post(
            f"{BASE}/analyze",
            files={"file": ("test_data.csv", f, "text/csv")},
            data={"query": query},
            timeout=120,
        )

    print(f"  Status Code: {r.status_code}")
    body = r.json()
    print(f"  Response:")
    print(f"    status:            {body.get('status')}")
    print(f"    final_answer:      {body.get('final_answer')}")
    print(f"    retry_count:       {body.get('retry_count')}")
    print(f"    validation_errors: {body.get('validation_errors')}")

    assert r.status_code == 200
    assert body["status"] in ("success", "failed")
    print(f"\n  [PASS] Agent pipeline completed with status: {body['status']}")


def test_analyze_bad_file():
    separator("POST /analyze -- Invalid File (rejection path)")
    query = "What is the total revenue?"
    print(f"  Sending a .txt file (should be rejected)\n")

    r = requests.post(
        f"{BASE}/analyze",
        files={"file": ("bad_file.txt", b"this is not a csv", "text/plain")},
        data={"query": query},
        timeout=30,
    )

    print(f"  Status Code: {r.status_code}")
    body = r.json()
    print(f"  Response:")
    print(f"    status:            {body.get('status')}")
    print(f"    final_answer:      {body.get('final_answer')}")
    print(f"    validation_errors: {body.get('validation_errors')}")

    assert r.status_code == 200
    assert body["status"] == "rejected"
    print(f"\n  [PASS] File correctly rejected")


def test_history():
    separator("GET /history")
    r = requests.get(f"{BASE}/history")
    print(f"  Status Code: {r.status_code}")
    runs = r.json()
    print(f"  Total runs in history: {len(runs)}")
    if runs:
        print(f"\n  Latest run:")
        for k, v in runs[0].items():
            val_str = str(v)[:100]
            print(f"    {k}: {val_str}")
    assert r.status_code == 200
    print(f"\n  [PASS]")


if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print(f"  PROFITORACLE AGENT -- End-to-End API Test Suite")
    print(f"{'#'*60}")

    tests = [test_health, test_analyze_bad_file, test_analyze_valid, test_history]
    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL]: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)

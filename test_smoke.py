"""Quick smoke test for all subsystems."""
import pandas as pd

# 1. Test code runner sandbox
from utils.code_runner import run_agent_code

df = pd.DataFrame({"region": ["East", "West", "East"], "revenue": [100, 200, 150]})

# Simple test
r1 = run_agent_code('RESULT = df["revenue"].sum()', df)
print(f"[1] Sandbox sum test:  {r1}")
assert r1["error"] is None, f"Sandbox error: {r1['error']}"
assert r1["RESULT"] == 450, f"Expected 450, got {r1['RESULT']}"

# Groupby test
code = """
grouped = df.groupby("region")["revenue"].sum()
RESULT = grouped.to_dict()
"""
r2 = run_agent_code(code, df)
print(f"[2] Sandbox groupby:   {r2}")
assert r2["error"] is None, f"Sandbox error: {r2['error']}"

# Security test - should block imports
r3 = run_agent_code('import os; RESULT = os.listdir(".")', df)
print(f"[3] Sandbox security:  {r3}")
assert r3["error"] is not None, "Should have blocked import!"

# 2. Test DB
from utils.db import init_db, insert_run, get_history

init_db()
insert_run(query="test query", filename="test.csv", status="success", retry_count=0, final_answer="42")
history = get_history(limit=5)
print(f"[4] DB history count:  {len(history)} run(s)")
assert len(history) >= 1

# 3. Test file utils
from utils.file_utils import save_upload, parse_file, delete_file, get_schema_summary
import os

csv_content = b"name,value\nAlice,10\nBob,20\nCharlie,30\n"
path = save_upload(csv_content, "test_data.csv")
print(f"[5] File saved to:     {path}")
assert os.path.exists(path)

df2 = parse_file(path)
print(f"[6] File parsed:       {df2.shape}")
assert df2.shape == (3, 2)

schema = get_schema_summary(df2)
print(f"[7] Schema summary:\n{schema}")

delete_file(path)
assert not os.path.exists(path)
print(f"[8] File deleted OK")

# 4. Test graph compilation
from graph.graph import get_app

app = get_app()
print(f"[9] Graph compiled:    {type(app).__name__}")

print("\n" + "=" * 50)
print("  ALL TESTS PASSED [OK]")
print("=" * 50)

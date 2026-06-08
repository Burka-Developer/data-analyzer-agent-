"""
RestrictedPython sandbox executor.
Runs agent-generated Python code with df, pd, and np injected.
Blocks os.system, subprocess, __import__, and other dangerous builtins.
"""

import copy
import pandas
import numpy
from RestrictedPython import compile_restricted, safe_globals


def run_agent_code(code_str: str, df: pandas.DataFrame) -> dict:
    """
    Execute agent-generated Python code in a RestrictedPython sandbox.

    The code has access to:
      - df: the user's DataFrame (injected, NOT read from file)
      - pd: pandas module
      - np: numpy module
      - RESULT: must be assigned by the code (string, number, dict, or list)

    Returns:
      {"RESULT": <value>, "error": None} on success
      {"RESULT": None, "error": "<error message>"} on failure
    """
    try:
        byte_code = compile_restricted(code_str, "<agent>", "exec")

        # Build restricted globals with pandas and numpy available
        glb = copy.copy(safe_globals)
        glb.update({
            "__builtins__": safe_globals["__builtins__"],
            "pd": pandas,
            "np": numpy,
            "_getiter_": iter,        # Allow iteration (for loops)
            "_getattr_": getattr,     # Allow attribute access
            "_getitem_": lambda obj, key: obj[key],  # Allow indexing
            "_write_": lambda x: x,   # Allow variable assignment in loops
            "_inplacevar_": lambda op, x, y: op(x, y),  # Allow +=, -= etc.
        })

        local_vars = {"df": df, "RESULT": None}
        exec(byte_code, glb, local_vars)

        result = local_vars.get("RESULT")

        # Convert DataFrame/Series results to string for safety
        if isinstance(result, (pandas.DataFrame, pandas.Series)):
            result = result.to_string()

        return {"RESULT": result, "error": None}
    except Exception as e:
        return {"RESULT": None, "error": str(e)}

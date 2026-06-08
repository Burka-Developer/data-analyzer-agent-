"""
All 5 node functions for the LangGraph pipeline.

Node 1: file_validator     — Pure Python, no LLM
Node 2: rejection_handler  — Pure Python, no LLM
Node 3: planning_agent     — LLM (xAI Grok)
Node 4: execution_agent    — LLM (xAI Grok) + RestrictedPython exec
Node 5: validator_agent    — LLM (xAI Grok)
"""

import os
import json
import re
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

from utils.file_utils import parse_file, get_schema_summary
from utils.code_runner import run_agent_code

# Load environment variables
load_dotenv()

# xAI Grok client (OpenAI-compatible)
_client = OpenAI(
    api_key=os.environ.get("XAI_API_KEY", ""),
    base_url="https://api.x.ai/v1",
)

MODEL_NAME = "grok-3-mini"


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call xAI Grok via the OpenAI-compatible API."""
    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        timeout=30,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


# ────────────────────────────────────────────────────────────────
# NODE 1: file_validator (Python logic — no LLM)
# ────────────────────────────────────────────────────────────────

def file_validator(state: dict) -> dict:
    """
    Validate the uploaded file before any LLM call.
    Checks: existence, extension, size, row count, parseability.
    """
    file_path = state.get("file_path", "")
    errors = []

    # 1. File exists and is not empty
    if not file_path or not os.path.exists(file_path):
        errors.append("File does not exist or no file was provided.")
        return {
            "validation_errors": errors,
            "status": "rejected",
        }

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        errors.append("File is empty (0 bytes).")
        return {
            "validation_errors": errors,
            "status": "rejected",
        }

    # 2. File extension check
    ext = os.path.splitext(file_path)[1].lower()
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    if ext not in allowed_extensions:
        errors.append(
            f"Unsupported file format: '{ext}'. Only .csv, .xlsx, and .xls files are accepted."
        )
        return {
            "validation_errors": errors,
            "status": "rejected",
        }

    # 3. File size check (< 10MB)
    size_mb = file_size / (1024 * 1024)
    if size_mb > 10:
        errors.append(f"File too large: {size_mb:.2f}MB. Max is 10MB.")
        return {
            "validation_errors": errors,
            "status": "rejected",
        }

    # 4 & 5. Parse file and check row count
    try:
        df = parse_file(file_path)
    except Exception as e:
        errors.append(f"Failed to parse file: {str(e)}")
        return {
            "validation_errors": errors,
            "status": "rejected",
        }

    row_count = len(df)
    if row_count > 50_000:
        errors.append(
            f"File has {row_count:,} rows. Maximum allowed is 50,000 rows."
        )
        return {
            "validation_errors": errors,
            "status": "rejected",
        }

    # All checks passed
    return {
        "file_df": df,
        "validation_errors": [],
        "status": "validated",
    }


# ────────────────────────────────────────────────────────────────
# NODE 2: rejection_handler (Python logic — no LLM)
# ────────────────────────────────────────────────────────────────

def rejection_handler(state: dict) -> dict:
    """
    Format validation errors into a user-facing rejection message.
    Terminal node — graph ends here on validation failure.
    """
    errors = state.get("validation_errors", [])
    if errors:
        message = "❌ File validation failed:\n\n" + "\n".join(
            f"  • {err}" for err in errors
        )
    else:
        message = "❌ File validation failed for an unknown reason."

    return {
        "final_answer": message,
        "status": "rejected",
    }


# ────────────────────────────────────────────────────────────────
# NODE 3: planning_agent (LLM — xAI Grok)
# ────────────────────────────────────────────────────────────────

PLANNING_SYSTEM_PROMPT = (
    "You are a senior data analyst. Given a user question and a DataFrame schema, "
    "produce a precise, step-by-step analysis plan in plain English. Be specific about "
    "which columns to use, what calculations to perform, and what the output format "
    "should be. Do not write code. Output only the plan as a numbered list."
)


def planning_agent(state: dict) -> dict:
    """
    Generate a step-by-step analysis plan using xAI Grok.
    On retries, includes previous code and output for context.
    """
    df = state.get("file_df")
    schema = get_schema_summary(df) if df is not None else "No schema available."

    user_prompt_parts = [
        f"User question: {state.get('user_query', '')}",
        f"\nDataFrame schema:\n{schema}",
    ]

    # On retry, include context about what went wrong
    retry_count = state.get("retry_count", 0)
    if retry_count > 0:
        prev_code = state.get("generated_code", "")
        prev_output = state.get("exec_output", "")
        prev_error = state.get("exec_error", "")
        verdict = state.get("verdict", "")

        user_prompt_parts.append(
            f"\n--- RETRY #{retry_count} ---"
            f"\nThe previous attempt failed or produced incorrect results."
        )
        if prev_code:
            user_prompt_parts.append(f"\nPrevious code:\n```python\n{prev_code}\n```")
        if prev_error:
            user_prompt_parts.append(f"\nExecution error: {prev_error}")
        if prev_output:
            user_prompt_parts.append(f"\nPrevious output: {prev_output}")
        if verdict:
            user_prompt_parts.append(f"\nValidator feedback: {verdict}")

        user_prompt_parts.append(
            "\nPlease create a DIFFERENT, improved plan that avoids the previous issues."
        )

    user_prompt = "\n".join(user_prompt_parts)

    plan = _call_llm(PLANNING_SYSTEM_PROMPT, user_prompt)

    return {
        "plan": plan,
    }


# ────────────────────────────────────────────────────────────────
# NODE 4: execution_agent (LLM — xAI Grok + RestrictedPython)
# ────────────────────────────────────────────────────────────────

EXECUTION_SYSTEM_PROMPT = (
    "You are a Python data analysis expert. Given a user question, a DataFrame schema, "
    "and an analysis plan, write complete executable Python code that performs the analysis.\n\n"
    "RULES:\n"
    "1. The variable `df` is already a loaded pandas DataFrame — do NOT read from file.\n"
    "2. You have access to `pd` (pandas) and `np` (numpy) — do NOT import anything.\n"
    "3. Store the final answer in a variable called `RESULT`.\n"
    "4. RESULT must be a string, number, dict, or list — NEVER a DataFrame, Series, or plot.\n"
    "5. Do NOT use print(). Only assign RESULT.\n"
    "6. Do NOT use os, subprocess, __import__, or any system calls.\n"
    "7. Output ONLY the Python code, nothing else. No markdown fences, no explanations."
)


def _extract_code(text: str) -> str:
    """
    Extract Python code from LLM response.
    Handles both raw code and markdown-fenced code blocks.
    """
    # Try to extract from ```python ... ``` blocks
    pattern = r"```(?:python)?\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return matches[0].strip()
    # If no code fence found, return the raw text
    return text.strip()


def execution_agent(state: dict) -> dict:
    """
    Generate and execute Python analysis code.
    The LLM writes the code; RestrictedPython runs it safely.
    """
    df = state.get("file_df")
    schema = get_schema_summary(df) if df is not None else "No schema available."
    plan = state.get("plan", "")
    query = state.get("user_query", "")

    user_prompt = (
        f"User question: {query}\n\n"
        f"DataFrame schema:\n{schema}\n\n"
        f"Analysis plan:\n{plan}\n\n"
        f"Write the Python code now."
    )

    # Get code from LLM
    raw_response = _call_llm(EXECUTION_SYSTEM_PROMPT, user_prompt)
    code_str = _extract_code(raw_response)

    # Execute in sandbox
    result = run_agent_code(code_str, df)

    if result["error"]:
        new_retry = state.get("retry_count", 0) + 1
        # If max retries exceeded, set graceful failure
        if new_retry > 2:
            return {
                "generated_code": code_str,
                "exec_output": None,
                "exec_error": result["error"],
                "retry_count": new_retry,
                "final_answer": (
                    "⚠️ The agent was unable to complete the analysis after multiple attempts. "
                    f"Last error: {result['error']}"
                ),
                "status": "failed",
            }
        return {
            "generated_code": code_str,
            "exec_output": None,
            "exec_error": result["error"],
            "retry_count": new_retry,
        }

    # Successful execution
    exec_output = str(result["RESULT"]) if result["RESULT"] is not None else "None"
    return {
        "generated_code": code_str,
        "exec_output": exec_output,
        "exec_error": None,
    }


# ────────────────────────────────────────────────────────────────
# NODE 5: validator_agent (LLM — xAI Grok)
# ────────────────────────────────────────────────────────────────

VALIDATOR_SYSTEM_PROMPT = (
    "You are a strict QA reviewer. Given the user's original question, the analysis "
    "plan, and the code's output, respond with ONLY a JSON object:\n"
    '  {"verdict": "match" | "mismatch", "reason": "<one sentence>"}\n'
    "'match' means the output directly and completely answers the question.\n"
    "'mismatch' means the output is wrong, incomplete, or answers a different question."
)


def validator_agent(state: dict) -> dict:
    """
    Check whether the execution output actually answers the user's query.
    Returns verdict of 'match' or 'mismatch'.
    """
    query = state.get("user_query", "")
    plan = state.get("plan", "")
    exec_output = state.get("exec_output", "")

    user_prompt = (
        f"User's original question: {query}\n\n"
        f"Analysis plan:\n{plan}\n\n"
        f"Code output:\n{exec_output}"
    )

    raw_response = _call_llm(VALIDATOR_SYSTEM_PROMPT, user_prompt)

    # Parse JSON response from the LLM
    try:
        # Try to extract JSON from response (may have extra text)
        json_match = re.search(r"\{.*?\}", raw_response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(raw_response)

        verdict = parsed.get("verdict", "mismatch")
        reason = parsed.get("reason", "No reason provided.")
    except (json.JSONDecodeError, AttributeError):
        # If we can't parse the response, treat as mismatch
        verdict = "mismatch"
        reason = f"Could not parse validator response: {raw_response[:200]}"

    if verdict == "match":
        return {
            "verdict": "match",
            "final_answer": exec_output,
            "status": "success",
        }
    else:
        new_retry = state.get("retry_count", 0) + 1
        if new_retry > 2:
            return {
                "verdict": "mismatch",
                "retry_count": new_retry,
                "final_answer": (
                    "⚠️ The agent was unable to produce a satisfactory answer after "
                    f"multiple attempts. Last output: {exec_output}\n"
                    f"Validator feedback: {reason}"
                ),
                "status": "failed",
            }
        return {
            "verdict": "mismatch",
            "retry_count": new_retry,
            # Append mismatch reason so planning_agent can use it
            "exec_output": f"{exec_output}\n[VALIDATOR MISMATCH: {reason}]",
        }

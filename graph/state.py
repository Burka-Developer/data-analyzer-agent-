"""
AgentState — the shared state TypedDict that flows through
every node in the LangGraph pipeline.
"""

from typing import TypedDict, Optional, Any
import pandas as pd


class AgentState(TypedDict):
    # User inputs
    user_query: str
    file_path: str

    # Parsed data (populated by file_validator on success)
    file_df: Optional[Any]  # pd.DataFrame — using Any for TypedDict compat

    # Validation (Node 1)
    validation_errors: list[str]

    # Planning (Node 3)
    plan: str

    # Execution (Node 4)
    generated_code: str
    exec_output: Optional[str]
    exec_error: Optional[str]

    # Validation verdict (Node 5)
    verdict: str  # "match" or "mismatch"

    # Control flow
    retry_count: int
    final_answer: str
    status: str  # "pending", "rejected", "success", "failed"

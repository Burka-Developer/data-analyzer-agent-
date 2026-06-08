"""
Routing functions for LangGraph conditional edges.
These control the flow between nodes based on state values.
"""

from langgraph.graph import END


def route_after_validation(state: dict) -> str:
    """
    After file_validator:
      - rejected  → rejection_handler (terminal)
      - otherwise → planning_agent (start LLM pipeline)
    """
    if state.get("status") == "rejected":
        return "rejection_handler"
    return "planning_agent"


def route_after_execution(state: dict) -> str:
    """
    After execution_agent:
      - exec_error + retries left   → planning_agent (re-plan)
      - exec_error + max retries    → END (graceful failure)
      - success                     → validator_agent (QA check)
    """
    if state.get("exec_error"):
        if state.get("retry_count", 0) <= 2:
            return "planning_agent"
        return END
    return "validator_agent"


def route_after_validation_check(state: dict) -> str:
    """
    After validator_agent:
      - match                       → END (success, final answer set)
      - mismatch + retries left     → planning_agent (re-plan)
      - mismatch + max retries      → END (graceful failure)
    """
    if state.get("verdict") == "match":
        return END
    if state.get("retry_count", 0) <= 2:
        return "planning_agent"
    return END

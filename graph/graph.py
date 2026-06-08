"""
LangGraph StateGraph builder.
Wires all 5 nodes and conditional edges into a compiled graph app.
"""

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    file_validator,
    rejection_handler,
    planning_agent,
    execution_agent,
    validator_agent,
)
from graph.edges import (
    route_after_validation,
    route_after_execution,
    route_after_validation_check,
)


def build_graph() -> StateGraph:
    """Build and return the compiled LangGraph agent pipeline."""

    graph = StateGraph(AgentState)

    # ── Add all 5 nodes ──
    graph.add_node("file_validator", file_validator)
    graph.add_node("rejection_handler", rejection_handler)
    graph.add_node("planning_agent", planning_agent)
    graph.add_node("execution_agent", execution_agent)
    graph.add_node("validator_agent", validator_agent)

    # ── Set entry point ──
    graph.set_entry_point("file_validator")

    # ── Conditional edges ──

    # After file_validator → rejection_handler OR planning_agent
    graph.add_conditional_edges(
        "file_validator",
        route_after_validation,
        {
            "rejection_handler": "rejection_handler",
            "planning_agent": "planning_agent",
        },
    )

    # rejection_handler is terminal → END
    graph.add_edge("rejection_handler", END)

    # planning_agent always goes to execution_agent
    graph.add_edge("planning_agent", "execution_agent")

    # After execution_agent → planning_agent (retry) OR validator_agent OR END
    graph.add_conditional_edges(
        "execution_agent",
        route_after_execution,
        {
            "planning_agent": "planning_agent",
            "validator_agent": "validator_agent",
            END: END,
        },
    )

    # After validator_agent → END (match/max retries) OR planning_agent (mismatch)
    graph.add_conditional_edges(
        "validator_agent",
        route_after_validation_check,
        {
            END: END,
            "planning_agent": "planning_agent",
        },
    )

    return graph.compile()


# Lazy-compiled graph application — built on first access
_app = None


def get_app():
    """Return the compiled graph, building it on first call."""
    global _app
    if _app is None:
        _app = build_graph()
    return _app

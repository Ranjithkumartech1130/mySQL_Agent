"""
graph.py
~~~~~~~~
LangGraph StateGraph definition for the Recruiting Database Agent (DBMS AI).

Nodes
-----
evaluator      → classify intent, extract entities
database_agent → execute DB query / write
fallback       → return helpful message when query is clearly off-topic

Flow
----
START → evaluator → [conditional] → database_agent → END
                                 ↘→ fallback       → END
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from agents.evaluator_agent import evaluator_node, route_after_evaluator
from agents.database_agent import database_agent_node
from utils.state import RecruitState, empty_state

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fallback node
# ---------------------------------------------------------------------------
_FALLBACK_MESSAGE = (
    "I'm a DBMS AI assistant. I can only answer questions related to the database — "
    "such as listing candidates, counting records, searching by role or skills, "
    "and managing job data. Please ask me something about the database! 🗄️"
)


def fallback_node(state: RecruitState) -> RecruitState:
    """LangGraph node: return helpful fallback when intent is clearly off-topic."""
    trace = list(state.get("trace", []))
    trace.append("[Fallback] Off-topic query — returning help message.")
    logger.info("[Fallback] Unknown intent — query: %r", state.get("user_input", ""))
    return {
        **state,
        "response": _FALLBACK_MESSAGE,
        "db_action": "none",
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
def build_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph."""
    workflow = StateGraph(RecruitState)

    # --- Register nodes ---
    workflow.add_node("evaluator",      evaluator_node)
    workflow.add_node("database_agent", database_agent_node)
    workflow.add_node("fallback",       fallback_node)

    # --- Entry point ---
    workflow.set_entry_point("evaluator")

    # --- Conditional edges from evaluator ---
    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "database_agent": "database_agent",
            "fallback":       "fallback",
        },
    )

    # --- Terminal edges ---
    workflow.add_edge("database_agent", END)
    workflow.add_edge("fallback",       END)

    return workflow.compile()


# Compile once at module level — reused across all requests
_compiled_graph = build_graph()


# ---------------------------------------------------------------------------
# Public run() function
# ---------------------------------------------------------------------------
def run(user_input: str) -> RecruitState:
    """
    Execute the full agent graph for a given user query.

    Parameters
    ----------
    user_input : str
        Natural language query in Tamil, English, or mixed.

    Returns
    -------
    RecruitState
        Final state after all nodes have executed.
    """
    initial_state = empty_state(user_input)
    logger.info("Graph run started | input=%r", user_input)
    final_state = _compiled_graph.invoke(initial_state)
    logger.info(
        "Graph run complete | intent=%s | rows=%s",
        final_state.get("intent"),
        final_state.get("db_affected"),
    )
    return final_state

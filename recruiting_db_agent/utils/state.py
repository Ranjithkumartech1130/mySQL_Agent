from typing import TypedDict, List, Dict, Any, Optional


class RecruitState(TypedDict, total=False):
    """
    Shared state object that flows through all LangGraph nodes.

    Fields
    ------
    user_input      : Raw query from the user (Tamil / English / mixed)
    intent          : Classified intent — db_select | db_insert | db_update | unknown
    entities        : Extracted slot values (role, candidate_name, etc.)
    confidence      : Evaluator confidence score 0.0–1.0
    db_query        : The exact SQL string that was executed
    db_result       : List of row dicts returned by SELECT queries
    db_action       : Actual DB action taken — select | insert | update | none
    db_affected     : Number of rows affected / returned
    response        : Final human-readable formatted text
    trace           : Ordered log of steps taken by each agent node
    errors          : Any non-fatal error messages collected during execution
    """

    user_input: str
    intent: str                   # db_select | db_insert | db_update | unknown
    entities: Dict[str, Any]      # role, candidate_name, new_status, min_experience, phone, skills
    confidence: float
    db_query: str
    db_result: List[Dict[str, Any]]
    db_action: str                # select | insert | update | none
    db_affected: int
    response: str
    trace: List[str]
    errors: List[str]


def empty_state(user_input: str) -> RecruitState:
    """Return a fresh RecruitState with safe defaults."""
    return RecruitState(
        user_input=user_input,
        intent="unknown",
        entities={},
        confidence=0.0,
        db_query="",
        db_result=[],
        db_action="none",
        db_affected=0,
        response="",
        trace=[],
        errors=[],
    )

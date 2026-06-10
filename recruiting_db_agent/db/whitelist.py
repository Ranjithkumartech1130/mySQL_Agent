"""
db/whitelist.py
~~~~~~~~~~~~~~~
Security whitelist for column access and allowed SQL operations.

SECURITY CONTRACT
-----------------
• Never expose: salary, aadhaar, password, personal_email
• DELETE is never allowed on any table
• These dictionaries are the single source of truth used by
  database_agent.py to build every query
"""

# ---------------------------------------------------------------------------
# ALLOWED_COLUMNS
# Defines the exact set of columns that may appear in SELECT / INSERT / UPDATE.
# ---------------------------------------------------------------------------
ALLOWED_COLUMNS: dict[str, list[str]] = {
    "candidates": [
        "id",
        "name",
        "phone",
        "role",
        "skills",
        "status",
        "experience",
        "created_at",
    ],
    "jobs": [
        "id",
        "title",
        "department",
        "required_exp",
        "skills",
        "open_slots",
        "status",
    ],
    "call_logs": [
        "id",
        "candidate_id",
        "call_type",
        "scheduled_at",
        "status",
        "notes",
    ],
}

# ---------------------------------------------------------------------------
# ALLOWED_OPERATIONS
# Defines which DML verbs are permitted per table.
# DELETE is intentionally absent from every table.
# ---------------------------------------------------------------------------
ALLOWED_OPERATIONS: dict[str, list[str]] = {
    "candidates": ["SELECT", "INSERT", "UPDATE"],
    "jobs":       ["SELECT"],
    "call_logs":  ["SELECT", "INSERT"],
}


def is_column_allowed(table: str, column: str) -> bool:
    """Return True if *column* is whitelisted for *table*."""
    return column in ALLOWED_COLUMNS.get(table, [])


def is_operation_allowed(table: str, operation: str) -> bool:
    """Return True if *operation* (e.g. 'SELECT') is allowed on *table*."""
    return operation.upper() in ALLOWED_OPERATIONS.get(table, [])

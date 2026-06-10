"""
agents/database_agent.py
~~~~~~~~~~~~~~~~~~~~~~~~
Database Agent — dynamically builds and executes SQL queries
using Groq LLM with automatic multi-model fallback.

SECURITY CONTRACT
-----------------
• Never allows destructive commands (DELETE, DROP, ALTER, TRUNCATE, etc.)
• Enforces single-statement execution (blocks stacked queries/semicolons)
• Catches all exceptions — never crashes the graph
• Uses lazy singleton DB connector so .env is loaded before connecting
• Multi-model fallback: gemma2-9b-it → llama-3.1-8b-instant → llama-3.3-70b-versatile
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from db.connector import DBConnector
from utils.state import RecruitState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy Singleton DB Connector — initialized once after .env is loaded
# ---------------------------------------------------------------------------
_db_instance: "DBConnector | None" = None


def _get_db() -> DBConnector:
    """Return a shared DBConnector, creating it on first call."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DBConnector()
        logger.info("[DatabaseAgent] DB initialized in mode: %s", _db_instance.mode)
    return _db_instance


# ---------------------------------------------------------------------------
# Multi-model LLM factory with fallback
# ---------------------------------------------------------------------------
_SQL_MODELS = [
    "gemma2-9b-it",            # Primary: higher daily limit
    "llama-3.1-8b-instant",    # Fallback 1
    "llama-3.3-70b-versatile", # Fallback 2: most powerful
]


def _invoke_with_fallback(messages: list, max_tokens: int = 2048) -> str:
    """
    Try each model in order. Returns the text content of the first successful call.
    Raises the last exception if all models fail.
    """
    last_exc: Exception | None = None
    for model_name in _SQL_MODELS:
        try:
            llm = ChatGroq(model=model_name, max_tokens=max_tokens, temperature=0)
            response = llm.invoke(messages)
            logger.info("[DatabaseAgent] LLM call succeeded with model: %s", model_name)
            return response.content.strip()
        except Exception as exc:
            err = str(exc)
            if "rate_limit" in err.lower() or "429" in err:
                logger.warning("[DatabaseAgent] Rate limit on %s — trying next model", model_name)
                last_exc = exc
                continue
            # Non-rate-limit error: still try next model
            logger.warning("[DatabaseAgent] Error with model %s: %s", model_name, err[:120])
            last_exc = exc
            continue
    raise last_exc or RuntimeError("All LLM models failed")


# ---------------------------------------------------------------------------
# LLM Prompts
# ---------------------------------------------------------------------------
_SQL_GENERATOR_PROMPT = """You are an expert SQL query builder. Generate SQL to answer the user's question.

Database Dialect: {dialect}

Database Schema:
{schema}

RULES (follow strictly):
1. Output ONLY a raw SQL query — no markdown, no backticks, no explanations, no comments.
2. Use only SELECT, INSERT, or UPDATE. NEVER use DELETE, DROP, ALTER, TRUNCATE.
3. Only use tables and columns that exist in the schema. Do not invent names.
4. NEVER add a LIMIT clause unless the user explicitly requests a specific number.
5. For COUNT questions ("how many X"), use: SELECT COUNT(*) AS count FROM table WHERE ...
6. For role/skill text matching, use LIKE with wildcards: WHERE role LIKE '%Full Stack%'
7. MySQL dialect: use backtick identifiers. SQLite: use double-quote identifiers.
8. Respond with ONLY the SQL string, nothing else.

Examples:
- "how many full stack developers" → SELECT COUNT(*) AS count FROM candidates WHERE role LIKE '%Full Stack%'
- "show all devops candidates" → SELECT * FROM candidates WHERE role LIKE '%DevOps%'
- "candidates with Python skills" → SELECT * FROM candidates WHERE skills LIKE '%Python%'
- "how many hired candidates" → SELECT COUNT(*) AS count FROM candidates WHERE status = 'hired'
- "show all candidates" → SELECT * FROM candidates
"""

_RESPONSE_FORMATTER_PROMPT = """You are a DBMS AI assistant. Answer the user's question using the database results.

User Question: {user_query}
SQL Executed: {sql_query}
Database Results: {db_results}

RULES:
1. Directly answer the question using the actual data.
2. For COUNT results: say "There are X [thing] in the database."
3. For record lists with 5 or fewer rows: show a markdown table with key columns.
4. For record lists with more than 5 rows: summarize (e.g., "Found 21 Full Stack Developers. Here are the first 5: ...") then show a table of the first 5.
5. For empty results: say "No [thing] found in the database."
6. Match the user's language (English, Tamil, or mixed).
7. Keep responses professional and concise.
"""

# ---------------------------------------------------------------------------
# Safety Validator
# ---------------------------------------------------------------------------
_PROHIBITED = [
    "DELETE", "DROP", "ALTER", "TRUNCATE", "RENAME",
    "GRANT", "REVOKE", "CREATE USER", "CREATE TABLE", "CREATE DATABASE",
]
_ALLOWED_VERBS = ["SELECT", "INSERT", "UPDATE", "SHOW", "DESCRIBE", "EXPLAIN", "PRAGMA"]


def _validate_sql(sql: str) -> tuple[bool, str]:
    """Returns (is_valid, reason)."""
    sql_upper = sql.upper().strip()

    for word in _PROHIBITED:
        if re.search(r"\b" + re.escape(word) + r"\b", sql_upper):
            return False, f"Prohibited keyword: {word}"

    if not any(sql_upper.startswith(v) for v in _ALLOWED_VERBS):
        return False, f"SQL must start with one of: {_ALLOWED_VERBS}"

    cleaned = sql_upper.rstrip().rstrip(";")
    if ";" in cleaned:
        return False, "Multiple statements detected"

    return True, "ok"


# ---------------------------------------------------------------------------
# Rule-based SQL generator (ultimate fallback — no LLM needed)
# ---------------------------------------------------------------------------
def _rule_based_sql(user_input: str, db_mode: str) -> str | None:
    """
    Generate SQL from simple keyword patterns when LLM is unavailable.
    Returns None if no pattern matches.
    """
    t = user_input.lower().strip()
    q = "`" if db_mode == "mysql" else '"'  # quote char

    # COUNT patterns
    count_patterns = [
        (r"\bhow many\s+(.+?)(\s+candidates?|\s+developers?|\s+engineers?|\s+scientists?)?\s*$",
         lambda m: f"SELECT COUNT(*) AS count FROM candidates WHERE role LIKE '%{m.group(1).strip().title()}%'"),
        (r"\bhow many candidates?\b", lambda m: "SELECT COUNT(*) AS count FROM candidates"),
        (r"\btotal candidates?\b", lambda m: "SELECT COUNT(*) AS count FROM candidates"),
    ]

    for pattern, builder in count_patterns:
        m = re.search(pattern, t)
        if m:
            try:
                return builder(m)
            except Exception:
                continue

    # Role-based SELECT
    role_map = {
        "full stack": "Full Stack Developer",
        "fullstack": "Full Stack Developer",
        "backend": "Backend Developer",
        "front.?end": "Frontend Developer",
        "devops": "DevOps Engineer",
        "data sci": "Data Scientist",
        "data science": "Data Scientist",
        "machine learning": "Data Scientist",
        "ml engineer": "Data Scientist",
    }
    for keyword, role in role_map.items():
        if re.search(keyword, t):
            if re.search(r"\bhow many\b", t):
                return f"SELECT COUNT(*) AS count FROM candidates WHERE role LIKE '%{role}%'"
            return f"SELECT * FROM candidates WHERE role LIKE '%{role}%'"

    # Status-based SELECT
    for status in ["applied", "screening", "interview", "hired", "rejected"]:
        if status in t:
            return f"SELECT * FROM candidates WHERE status = '{status}'"

    # Skill-based SELECT
    skills = ["python", "java", "react", "node.js", "docker", "kubernetes", "aws", "sql", "django", "fastapi"]
    for skill in skills:
        if skill in t:
            return f"SELECT * FROM candidates WHERE skills LIKE '%{skill.title()}%'"

    # Show all
    if re.search(r"\ball candidates?\b|\bshow candidates?\b|\blist candidates?\b", t):
        return "SELECT * FROM candidates"

    # Jobs
    if re.search(r"\bjobs?\b|\bvacancies\b|\bopen positions?\b", t):
        return "SELECT * FROM jobs"

    # Schema
    if re.search(r"\btables?\b|\bschema\b", t):
        return "SHOW TABLES" if db_mode == "mysql" else "SELECT name FROM sqlite_master WHERE type='table'"

    return None


# ---------------------------------------------------------------------------
# database_agent_node
# ---------------------------------------------------------------------------
def database_agent_node(state: RecruitState) -> RecruitState:
    """
    LangGraph node: execute dynamic DB query based on LLM Text-to-SQL.
    Falls back to rule-based SQL if LLM is unavailable.
    """
    user_input = state.get("user_input", "")
    trace = list(state.get("trace", []))
    errors = list(state.get("errors", []))

    db_query = ""
    db_result: list[dict] = []
    db_action = "none"
    db_affected = 0
    response = ""

    try:
        # 1. Connect to database
        db = _get_db()
        schema_metadata = db.get_schema_metadata()
        db_mode = db.mode

        logger.info("[DatabaseAgent] Mode=%s | Input=%r", db_mode, user_input[:80])

        # 2. Generate SQL — try LLM first, then rule-based fallback
        generated_sql = None
        sql_method = "llm"

        try:
            sql_gen_messages = [
                SystemMessage(content=_SQL_GENERATOR_PROMPT.format(
                    dialect=db_mode, schema=schema_metadata
                )),
                HumanMessage(content=user_input),
            ]
            raw_sql = _invoke_with_fallback(sql_gen_messages, max_tokens=512)
            # Strip any accidental markdown
            raw_sql = re.sub(r"^```[a-z]*\n?", "", raw_sql, flags=re.IGNORECASE)
            raw_sql = re.sub(r"```\s*$", "", raw_sql).strip()
            generated_sql = raw_sql

        except Exception as llm_exc:
            logger.warning("[DatabaseAgent] All LLMs failed for SQL gen: %s", llm_exc)
            errors.append(f"LLM unavailable: {llm_exc}")
            sql_method = "rule_based"
            # Try rule-based fallback
            generated_sql = _rule_based_sql(user_input, db_mode)
            if generated_sql is None:
                raise RuntimeError(
                    "I'm temporarily unable to process this query. "
                    "The AI model is rate-limited. Please try again in a few minutes."
                )

        db_query = generated_sql
        logger.info("[DatabaseAgent] SQL [%s]: %s", sql_method, db_query[:200])

        # 3. Validate safety
        is_valid, reason = _validate_sql(db_query)
        if not is_valid:
            raise PermissionError(f"SQL security violation: {reason}")

        # 4. Execute
        sql_upper = db_query.upper().strip()
        is_select = any(
            sql_upper.startswith(v)
            for v in ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "PRAGMA"]
        )

        if is_select:
            db_result = db.execute_query(db_query, ())
            db_affected = len(db_result)
            db_action = "select"
            logger.info("[DatabaseAgent] SELECT → %d rows", db_affected)
        else:
            db_affected = db.execute_write(db_query, ())
            db_action = "insert" if sql_upper.startswith("INSERT") else "update"
            logger.info("[DatabaseAgent] WRITE → %d rows affected", db_affected)

        # 5. Format natural-language response
        # Build a preview of results (first 20 rows for the formatter to keep tokens low)
        if is_select and len(db_result) > 20:
            results_preview = db_result[:20]
            results_str = json.dumps(results_preview, default=str)
            results_str += f"\n... and {len(db_result) - 20} more rows (total: {len(db_result)})"
        elif is_select:
            results_str = json.dumps(db_result, default=str)
        else:
            results_str = f"Affected rows: {db_affected}"

        try:
            fmt_messages = [
                SystemMessage(content=_RESPONSE_FORMATTER_PROMPT.format(
                    user_query=user_input,
                    sql_query=db_query,
                    db_results=results_str,
                )),
                HumanMessage(content=user_input),
            ]
            response = _invoke_with_fallback(fmt_messages, max_tokens=1024)
        except Exception as fmt_exc:
            # If formatter also fails, build a simple response directly
            logger.warning("[DatabaseAgent] Formatter failed: %s — using plain response", fmt_exc)
            if db_action == "select":
                if db_affected == 0:
                    response = "No results found in the database for your query."
                elif len(db_result) == 1 and "count" in db_result[0]:
                    count_val = db_result[0]["count"]
                    response = f"**Result:** {count_val}"
                else:
                    response = f"Found **{db_affected}** records. Here is a summary:\n\n"
                    for row in db_result[:5]:
                        name = row.get("name", row.get("title", "—"))
                        role = row.get("role", row.get("department", ""))
                        status = row.get("status", "")
                        exp = row.get("experience", "")
                        line_parts = [f"**{name}**"]
                        if role:
                            line_parts.append(role)
                        if status:
                            line_parts.append(f"[{status}]")
                        if exp:
                            line_parts.append(f"{exp} yrs")
                        response += "- " + " · ".join(line_parts) + "\n"
                    if db_affected > 5:
                        response += f"\n*...and {db_affected - 5} more.*"
            else:
                response = f"✅ Operation completed. {db_affected} record(s) affected."

    except Exception as exc:
        logger.error("[DatabaseAgent] Fatal error: %s", exc, exc_info=True)
        errors.append(str(exc))
        response = f"❌ {exc}"

    trace.append(
        f"[DatabaseAgent] action={db_action} | rows={db_affected} | sql={db_query[:80]}"
    )

    return {
        **state,
        "db_query": db_query,
        "db_result": db_result,
        "db_action": db_action,
        "db_affected": db_affected,
        "response": response,
        "trace": trace,
        "errors": errors,
    }

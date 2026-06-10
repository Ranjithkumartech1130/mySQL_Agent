"""
agents/evaluator_agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Evaluator Agent — classifies user intent using a TWO-LAYER approach:

Layer 1: Keyword-based detection (fast, always works, no API calls)
Layer 2: LLM-based classification (only for ambiguous queries, with fallback)

This ensures the agent ALWAYS works even when LLM rate limits are hit.

Supports Tamil, English, and mixed Tamil-English input.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Literal

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from utils.prompts import EVALUATOR_PROMPT
from utils.state import RecruitState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM — Try multiple models in order of preference (rate limit fallback)
# ---------------------------------------------------------------------------
_MODELS_TO_TRY = [
    "gemma2-9b-it",          # Primary: higher daily limit on Groq free tier
    "llama-3.1-8b-instant",  # Fallback 1: small fast model
    "llama-3.3-70b-versatile", # Fallback 2: powerful but most rate-limited
]


def _build_llm(model: str) -> ChatGroq:
    return ChatGroq(model=model, max_tokens=256, temperature=0)


# ---------------------------------------------------------------------------
# Layer 1: Keyword-based intent detection (ALWAYS works, no API calls)
# ---------------------------------------------------------------------------

# DB-SELECT keywords — English
_SELECT_KEYWORDS_EN = [
    r"\bhow many\b",
    r"\bcount\b",
    r"\bshow\b",
    r"\blist\b",
    r"\bfind\b",
    r"\bget\b",
    r"\bdisplay\b",
    r"\bsearch\b",
    r"\bwho\b",
    r"\bwhat\b",
    r"\bwhich\b",
    r"\bwhere\b",
    r"\bfetch\b",
    r"\ball candidates\b",
    r"\ball records\b",
    r"\bshow me\b",
    r"\btell me\b",
    r"\bgive me\b",
    r"\bhow much\b",
    r"\btop\b",
]

# DB-related nouns — roles, skills, entities
_DB_ENTITY_KEYWORDS = [
    r"\bcandidate[s]?\b",
    r"\bdeveloper[s]?\b",
    r"\bengineer[s]?\b",
    r"\bscientist[s]?\b",
    r"\bdesigner[s]?\b",
    r"\banalyst[s]?\b",
    r"\bfull.?stack\b",
    r"\bbackend\b",
    r"\bfrontend\b",
    r"\bfront.?end\b",
    r"\bback.?end\b",
    r"\bdevops\b",
    r"\bdata science\b",
    r"\bpython\b",
    r"\bjava\b",
    r"\breact\b",
    r"\bnode\b",
    r"\baws\b",
    r"\bdocker\b",
    r"\bkubernetes\b",
    r"\bml\b",
    r"\bmachine learning\b",
    r"\bskill[s]?\b",
    r"\bexperience\b",
    r"\bstatus\b",
    r"\bapplied\b",
    r"\bscreening\b",
    r"\bhired\b",
    r"\binterview\b",
    r"\brejected\b",
    r"\bjob[s]?\b",
    r"\brole[s]?\b",
    r"\bdepartment\b",
    r"\brecruit\b",
    r"\bpipeline\b",
    r"\brecord[s]?\b",
    r"\bdatabase\b",
    r"\btable[s]?\b",
    r"\bschema\b",
    r"\bcall log[s]?\b",
    r"\bphone\b",
    r"\bemail\b",
    r"\byear[s]? exp\b",
    r"\byrs exp\b",
    r"\bexp\b.*\byear[s]?\b",
]

# Tamil / code-mixed keywords indicating DB queries
_SELECT_KEYWORDS_TAMIL = [
    r"\bவேணும்\b",
    r"\bகாட்டு\b",
    r"\bகாட்டவும்\b",
    r"\bதேடு\b",
    r"\bதேடவும்\b",
    r"\bபார்\b",
    r"\bபட்டியல்\b",
    r"\bஎத்தனை\b",
    r"\bமொத்தம்\b",
    r"\bஉள்ள\b",
    r"\bவேண்டும்\b",
]

# DB INSERT keywords
_INSERT_KEYWORDS = [
    r"\badd\b.*\bcandidate\b",
    r"\binsert\b",
    r"\bcreate\b.*\bcandidate\b",
    r"\bregister\b",
    r"\bnew candidate\b",
    r"\bபுதிய\b",
    r"\bசேர்\b",
]

# DB UPDATE keywords
_UPDATE_KEYWORDS = [
    r"\bupdate\b",
    r"\bchange\b.*\bstatus\b",
    r"\bmodify\b",
    r"\bedit\b",
    r"\bset status\b",
    r"\bmark as\b",
    r"\bதிருத்து\b",
]

# Hard NOT-DB keywords (must be checked LAST, with strict matching)
_NOT_DB_KEYWORDS = [
    r"^(hi|hello|hey|good morning|good evening|good afternoon|bye|thanks|thank you|ok|okay|sure)[\s.!]*$",
    r"^what is \d+",                    # math: what is 2+2
    r"^(capital of|president of|who is the|what is the meaning)",
    r"^(tell me a joke|write a|code a|make a function|python function)",
    r"^(weather|news|sports|cricket|stock)",
]

DB_QUESTION_PATTERNS = [
    r"\bcan\b.+\bdo\b.+\bfor me\b",
    r"\bwhat can you\b",
    r"\bhow (are|do) you\b",
]


def _keyword_classify(text: str) -> str | None:
    """
    Fast keyword-based intent classifier.
    Returns 'db_select', 'db_insert', 'db_update', 'unknown', or None (ambiguous).
    """
    t = text.lower().strip()

    # 1. Hard NOT-DB check first (pure greetings, math, etc.)
    for pattern in _NOT_DB_KEYWORDS:
        if re.search(pattern, t, re.IGNORECASE):
            return "unknown"

    # 2. INSERT check
    for pattern in _INSERT_KEYWORDS:
        if re.search(pattern, t, re.IGNORECASE):
            return "db_insert"

    # 3. UPDATE check
    for pattern in _UPDATE_KEYWORDS:
        if re.search(pattern, t, re.IGNORECASE):
            return "db_update"

    # 4. SELECT check — query verb + DB entity, or just a strong DB entity
    has_select_verb = any(re.search(p, t, re.IGNORECASE) for p in _SELECT_KEYWORDS_EN)
    has_tamil_select = any(re.search(p, t, re.IGNORECASE) for p in _SELECT_KEYWORDS_TAMIL)
    has_db_entity = any(re.search(p, t, re.IGNORECASE) for p in _DB_ENTITY_KEYWORDS)

    if has_db_entity:
        return "db_select"  # Any DB entity mention → query the database
    if has_select_verb and len(t.split()) >= 2:
        return "db_select"  # Query verb with something → likely a DB query
    if has_tamil_select:
        return "db_select"

    # 5. Ambiguous — let LLM decide
    return None


# ---------------------------------------------------------------------------
# evaluator_node
# ---------------------------------------------------------------------------
def evaluator_node(state: RecruitState) -> RecruitState:
    """
    LangGraph node: classify intent using keyword detection + LLM fallback.
    """
    user_input: str = state.get("user_input", "")
    trace: list[str] = list(state.get("trace", []))
    errors: list[str] = list(state.get("errors", []))

    intent = "unknown"
    entities: dict = {}
    confidence = 0.0
    classification_method = "keyword"

    # --- Layer 1: Keyword-based classification (fast, no API cost) ---
    keyword_intent = _keyword_classify(user_input)
    logger.info("[Evaluator] Keyword classification: %s | query=%r", keyword_intent, user_input[:60])

    if keyword_intent is not None:
        # Keyword gave a definitive answer
        intent = keyword_intent
        confidence = 0.95 if keyword_intent != "unknown" else 0.8
        classification_method = "keyword"
    else:
        # --- Layer 2: LLM classification for ambiguous queries ---
        classification_method = "llm"
        last_error = None

        for model_name in _MODELS_TO_TRY:
            try:
                llm = _build_llm(model_name)
                messages = [
                    SystemMessage(content=EVALUATOR_PROMPT),
                    HumanMessage(content=user_input),
                ]
                response = llm.invoke(messages)
                raw_text: str = response.content.strip()

                # Strip markdown fences if any
                raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text, flags=re.IGNORECASE)
                raw_text = re.sub(r"```$", "", raw_text.strip()).strip()

                parsed = json.loads(raw_text)
                intent = parsed.get("intent", "db_select")  # Default to db_select on parse issues
                entities = parsed.get("entities", {})
                confidence = float(parsed.get("confidence", 0.9))
                entities = {k: v for k, v in entities.items() if v is not None}

                logger.info("[Evaluator] LLM (%s) classified as: %s", model_name, intent)
                last_error = None
                break  # Success — stop trying models

            except json.JSONDecodeError as exc:
                logger.warning("[Evaluator] JSON parse error with model %s: %s", model_name, exc)
                # If we got something back but couldn't parse it, default to db_select
                intent = "db_select"
                confidence = 0.7
                last_error = exc
                break

            except Exception as exc:
                err_str = str(exc)
                logger.warning("[Evaluator] Model %s failed: %s", model_name, err_str[:100])
                last_error = exc

                # Check if it's a rate limit error — try next model
                if "rate_limit" in err_str.lower() or "429" in err_str:
                    logger.warning("[Evaluator] Rate limit on %s — trying next model", model_name)
                    continue
                else:
                    # Non-rate-limit error — default to db_select for safety
                    intent = "db_select"
                    confidence = 0.6
                    break

        if last_error is not None:
            # All models failed — apply smart fallback: assume db_select for most things
            err_msg = f"[Evaluator] All LLM models failed — using db_select fallback"
            logger.error(err_msg)
            errors.append(err_msg)
            intent = "db_select"  # Safe fallback — try to query DB
            confidence = 0.5

    trace_entry = (
        f"[Evaluator] method={classification_method} | "
        f"Intent={intent} | Confidence={confidence:.2f}"
    )
    trace.append(trace_entry)
    logger.info(trace_entry)

    return {
        **state,
        "intent": intent,
        "entities": entities,
        "confidence": confidence,
        "trace": trace,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# route_after_evaluator
# ---------------------------------------------------------------------------
def route_after_evaluator(
    state: RecruitState,
) -> Literal["database_agent", "fallback"]:
    """
    Conditional edge function for LangGraph.
    Routes to 'database_agent' when intent is actionable,
    otherwise routes to 'fallback' for help messaging.
    """
    intent: str = state.get("intent", "unknown")
    if intent in ("db_select", "db_insert", "db_update"):
        return "database_agent"
    return "fallback"

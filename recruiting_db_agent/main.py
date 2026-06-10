"""
main.py
~~~~~~~
Demo script — runs 5 test queries and validates intent detection.

Queries cover:
  1. English role filter
  2. Tamil language query
  3. English with experience filter
  4. Status update (English)
  5. Aggregate / status summary query
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

# Load .env before any module imports that need env vars
load_dotenv()

# Validate Groq API key early
if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key":
    print("⚠️  WARNING: GROQ_API_KEY is not set or is still the placeholder value.")
    print("   Set it in .env and re-run.  Exiting.\n")
    sys.exit(1)

# Configure logging — only show WARNING+ during the demo to keep output clean
logging.basicConfig(level=logging.WARNING)

from graph import run  # noqa: E402  (import after env loaded)

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "query":          "Find all Full Stack Developer candidates",
        "expected_intent": "db_select",
        "label":          "1. English role filter",
    },
    {
        "query":          "எனக்கு இன்னிக்கு backend developers வேணும்",
        "expected_intent": "db_select",
        "label":          "2. Tamil language query",
    },
    {
        "query":          "Show Data Scientists with more than 3 years experience",
        "expected_intent": "db_select",
        "label":          "3. English + experience filter",
    },
    {
        "query":          "Update Kiran Patel status to interview",
        "expected_intent": "db_update",
        "label":          "4. Status update",
    },
    {
        "query":          "How many candidates do we have by status?",
        "expected_intent": "db_select",
        "label":          "5. Aggregate / status summary",
    },
]

DIVIDER = "─" * 72


def run_demo() -> None:
    passed = 0
    failed = 0

    print("\n" + "═" * 72)
    print("  RECRUITING DATABASE AGENT — Demo Run")
    print("═" * 72 + "\n")

    for tc in TEST_CASES:
        label          = tc["label"]
        query          = tc["query"]
        expected_intent = tc["expected_intent"]

        print(f"{'━' * 72}")
        print(f"  {label}")
        print(f"{'━' * 72}")
        print(f"  Query   : {query}")

        state = run(query)

        detected_intent = state.get("intent", "unknown")
        entities        = state.get("entities", {})
        sql_ran         = state.get("db_query", "—")
        response        = state.get("response", "—")
        confidence      = state.get("confidence", 0.0)
        trace           = state.get("trace", [])
        errs            = state.get("errors", [])

        # Pass / Fail
        ok = detected_intent == expected_intent
        status_icon = "✅ PASS" if ok else "❌ FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        print(f"  Intent  : {detected_intent}  (expected: {expected_intent})  {status_icon}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Entities: {entities}")
        print(f"  SQL     : {sql_ran or '(none)'}")
        print(f"\n  Response:\n")
        for line in response.splitlines():
            print(f"    {line}")
        print()

        if errs:
            print("  ⚠️  Errors:")
            for e in errs:
                print(f"    - {e}")

        print(f"  Trace:")
        for t in trace:
            print(f"    → {t}")
        print()

    # Summary
    print("═" * 72)
    print(f"  Results: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("═" * 72 + "\n")


if __name__ == "__main__":
    run_demo()

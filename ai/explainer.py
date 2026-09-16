"""SQL Query Explanation Engine for NL2SQL AI.

Translates generated SQLite queries into plain, friendly English explanations
tailored for non-technical users and viva presentations.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.gemini import GeminiClient, GeminiError, get_gemini_client
from ai.prompts import SQL_EXPLANATION_SYSTEM_INSTRUCTION, build_explanation_prompt

logger = logging.getLogger(__name__)

FALLBACK_EXPLANATION = "Explanation unavailable at the moment."


def explain_sql(
    question: str,
    sql_query: str,
    client: Optional[GeminiClient] = None,
    temperature: float = 0.3,
) -> str:
    """Generate a beginner-friendly natural language explanation of a SQL query.

    Args:
        question: User's original natural language prompt.
        sql_query: The generated or executed SQL query.
        client: Optional GeminiClient instance (defaults to shared client).
        temperature: Sampling temperature (defaults to 0.3 for natural tone).

    Returns:
        A concise 2-3 sentence plain English explanation, or a fallback string on error.
    """
    if not sql_query or not sql_query.strip():
        return "No query provided to explain."

    prompt = build_explanation_prompt(
        question=question or "Database inquiry",
        sql_query=sql_query,
    )

    try:
        active_client = client or get_gemini_client()
        raw_explanation = active_client.generate_text(
            prompt=prompt,
            system_instruction=SQL_EXPLANATION_SYSTEM_INSTRUCTION,
            temperature=temperature,
        )

        # Strip any accidental wrapping quotes or markdown headers
        cleaned = raw_explanation.strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (
            cleaned.startswith("'") and cleaned.endswith("'")
        ):
            cleaned = cleaned[1:-1].strip()

        return cleaned if cleaned else FALLBACK_EXPLANATION

    except GeminiError as exc:
        logger.warning("Gemini error during SQL explanation: %s", exc)
        return FALLBACK_EXPLANATION
    except Exception as exc:
        logger.error("Unexpected error during SQL explanation: %s", exc)
        return FALLBACK_EXPLANATION


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Show top 5 students based on marks"
    s = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "SELECT s.name, MAX(m.marks) AS max_marks FROM students s JOIN marks m ON s.student_id = m.student_id GROUP BY s.student_id ORDER BY max_marks DESC LIMIT 5;"
    )

    print(f"Question: {q}")
    print(f"SQL: {s}\n")
    explanation = explain_sql(q, s)
    print(f"AI Explanation:\n{explanation}")

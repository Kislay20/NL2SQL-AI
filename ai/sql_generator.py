"""Natural Language to SQL Generator module for NL2SQL AI.

Coordinates schema introspection, prompt construction, LLM inference via Gemini,
and output parsing to generate accurate SQLite queries.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.gemini import GeminiClient, get_gemini_client
from ai.parser import extract_sql
from ai.prompts import SQL_GENERATION_SYSTEM_INSTRUCTION, build_sql_prompt
from database.database import get_schema_prompt_context


def generate_sql(
    question: str,
    db_path: Optional[str | Path] = None,
    client: Optional[GeminiClient] = None,
    temperature: float = 0.0,
) -> str:
    """Generate a clean SQLite query from a natural language question.

    Args:
        question: User's natural language question (e.g. "Show students scoring > 80").
        db_path: Optional SQLite database path for schema introspection.
        client: Optional GeminiClient instance (defaults to shared client).
        temperature: Sampling temperature for Gemini (defaults to 0.0 for deterministic SQL).

    Returns:
        Cleaned SQLite query string.

    Raises:
        ValueError: If question is empty or invalid.
        GeminiError: If an error occurs during Gemini generation.
    """
    if not question or not question.strip():
        raise ValueError("User question cannot be empty.")

    # 1. Retrieve dynamic database schema
    schema_context = get_schema_prompt_context(db_path=db_path)

    # 2. Build the few-shot prompt
    prompt = build_sql_prompt(question=question, schema_context=schema_context)

    # 3. Call Gemini
    active_client = client or get_gemini_client()
    raw_response = active_client.generate_text(
        prompt=prompt,
        system_instruction=SQL_GENERATION_SYSTEM_INSTRUCTION,
        temperature=temperature,
    )

    # 4. Parse and sanitize the generated SQL
    cleaned_sql = extract_sql(raw_response)
    return cleaned_sql


if __name__ == "__main__":
    test_question = sys.argv[1] if len(sys.argv) > 1 else "Show all students in Computer Science"
    print(f"Natural Language Question: {test_question}")
    try:
        sql = generate_sql(test_question)
        print("\nGenerated SQL:")
        print(sql)
    except Exception as e:
        print(f"Error generating SQL: {e}")

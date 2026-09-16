"""Response parser and sanitizer for AI-generated SQL outputs.

Extracts clean, executable SQL statements from LLM responses, stripping
markdown code fences, conversational boilerplate, backticks, and extra whitespace.
"""

from __future__ import annotations

import re


def extract_sql(raw_response: str) -> str:
    """Extract and sanitize SQL from Gemini's raw output.

    Args:
        raw_response: Raw text returned by the model.

    Returns:
        Clean, executable SQL query string.
    """
    if not raw_response or not raw_response.strip():
        return ""

    cleaned = raw_response.strip()

    # 1. Extract content from markdown code fences: ```sql ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()

    # 2. Remove common conversational prefixes if present (e.g., "SQL:", "Here is the query:")
    prefixes_to_strip = [
        r"^(?:here\s+is\s+the\s+(?:sql\s+)?query\s*:?)",
        r"^(?:the\s+sql\s+query\s+is\s*:?)",
        r"^(?:sql\s*:?)",
        r"^(?:query\s*:?)",
    ]
    for prefix_pat in prefixes_to_strip:
        cleaned = re.sub(prefix_pat, "", cleaned, flags=re.IGNORECASE).strip()

    # 3. Strip wrapping backticks if present: `SELECT ...`
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned.strip("`").strip()

    # 4. Remove leading/trailing quotes if the model wrapped the query in quotes
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    # 5. Normalize whitespace and semicolons
    cleaned = cleaned.strip()
    if cleaned and not cleaned.endswith(";"):
        cleaned = f"{cleaned};"

    return cleaned

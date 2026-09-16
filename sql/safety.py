"""SQL Safety Guardrails for NL2SQL AI.

Uses sqlparse to inspect AST tokens, enforce single-statement constraints,
verify read-only SELECT types, and block dangerous keywords (DROP, DELETE, UPDATE, etc.).
"""

from __future__ import annotations

from typing import Tuple
import sqlparse
from sqlparse import tokens

# Disallowed keywords that modify data, alter schemas, or execute administration commands
FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "EXECUTE",
    "EXEC",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "GRANT",
    "REVOKE",
}


def is_safe_query(sql_query: str) -> Tuple[bool, str]:
    """Inspect a SQL query to ensure it is strictly read-only and safe to execute.

    Args:
        sql_query: The SQL query string to evaluate.

    Returns:
        Tuple of (is_safe: bool, reason: str). If safe, reason is empty.
    """
    if not sql_query or not sql_query.strip():
        return False, "Query is empty or whitespace."

    # 1. Multi-statement injection detection
    # Split query into statements, filtering out empty trailing delimiters
    statements = [stmt.strip() for stmt in sqlparse.split(sql_query) if stmt.strip()]

    if not statements:
        return False, "No valid SQL statement found."

    if len(statements) > 1:
        return (
            False,
            f"Multiple SQL statements detected ({len(statements)} statements found). "
            "Only a single read-only query is permitted.",
        )

    parsed_statements = sqlparse.parse(statements[0])
    if not parsed_statements:
        return False, "Failed to parse SQL statement."

    stmt = parsed_statements[0]

    # 2. Enforce statement type (must be SELECT)
    stmt_type = stmt.get_type()
    if stmt_type != "SELECT":
        return (
            False,
            f"Forbidden statement type '{stmt_type}'. Only SELECT queries are permitted.",
        )

    # 3. Token inspection (block forbidden keywords, ignoring string literals)
    for token in stmt.flatten():
        # Do not flag keywords appearing inside literal strings (e.g. WHERE name = 'drop')
        if token.ttype in tokens.Literal.String:
            continue

        token_upper = token.value.strip().upper()
        if token_upper in FORBIDDEN_KEYWORDS:
            return (
                False,
                f"Forbidden SQL keyword detected: '{token_upper}'. "
                "Data modification, schema alteration, and administrative commands are strictly prohibited.",
            )

    return True, ""

"""SQL Syntax and Schema Validator for NL2SQL AI.

Uses SQLite's EXPLAIN QUERY PLAN engine to statically verify query validity,
detecting hallucinated tables, non-existent columns, and malformed syntax without
executing the query or mutating data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Tuple

from database.database import get_connection, get_db_path
from sql.safety import is_safe_query


def validate_sql_syntax(
    db_path: Optional[str | Path],
    sql_query: str,
) -> Tuple[bool, str]:
    """Validate query syntax and schema references using SQLite EXPLAIN QUERY PLAN.

    Args:
        db_path: Path to the SQLite database file (or None for default).
        sql_query: The SQL query to validate.

    Returns:
        Tuple of (is_valid: bool, error_message: str). If valid, error_message is empty.
    """
    if not sql_query or not sql_query.strip():
        return False, "Query is empty."

    resolved_path = get_db_path(db_path)
    if not resolved_path.exists():
        return False, f"Database file not found at: {resolved_path}"

    try:
        with get_connection(resolved_path) as conn:
            cursor = conn.cursor()
            # EXPLAIN QUERY PLAN parses the query against SQLite's catalog without executing it
            clean_query = sql_query.strip().rstrip(";")
            cursor.execute(f"EXPLAIN QUERY PLAN {clean_query};")
            return True, ""
    except sqlite3.OperationalError as exc:
        return False, f"SQLite schema/syntax error: {exc}"
    except sqlite3.Error as exc:
        return False, f"SQLite validation error: {exc}"
    except Exception as exc:
        return False, f"Unexpected validation error: {exc}"


def validate_query(
    sql_query: str,
    db_path: Optional[str | Path] = None,
) -> Tuple[bool, str]:
    """Execute the full two-step validation pipeline: Safety Gate -> Schema Validator.

    Args:
        sql_query: The SQL query to check.
        db_path: Optional path to the SQLite database.

    Returns:
        Tuple of (is_valid: bool, error_message: str).
    """
    # Step 1: Safety Gate (AST tokens, keyword blocklist, single-statement check)
    is_safe, safety_err = is_safe_query(sql_query)
    if not is_safe:
        return False, safety_err

    # Step 2: Schema & Syntax Validation (EXPLAIN QUERY PLAN)
    is_valid_syntax, syntax_err = validate_sql_syntax(db_path, sql_query)
    if not is_valid_syntax:
        return False, syntax_err

    return True, ""

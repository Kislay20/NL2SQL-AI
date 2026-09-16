"""SQL Execution Engine for NL2SQL AI.

Safely connects to SQLite, executes read-only queries, and loads results directly
into Pandas DataFrames for downstream presentation in Streamlit tables and Plotly charts.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

from database.database import get_connection, get_db_path
from sql.validator import validate_query


def execute_query(
    sql_query: str,
    db_path: Optional[str | Path] = None,
) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Execute a SQL query against the SQLite database and extract results as a DataFrame.

    Args:
        sql_query: SQL query string to execute.
        db_path: Optional path to the SQLite database file.

    Returns:
        Tuple of (success: bool, dataframe: Optional[pd.DataFrame], error_message: str).
        If success is True, error_message is empty string.
        If success is False, dataframe is None and error_message describes the failure.
    """
    if not sql_query or not sql_query.strip():
        return False, None, "Query is empty or whitespace."

    resolved_path = get_db_path(db_path)
    if not resolved_path.exists():
        return False, None, f"Database file not found at: {resolved_path}"

    try:
        # Open managed SQLite connection (with foreign keys and proper context manager)
        with get_connection(resolved_path) as conn:
            # pd.read_sql_query directly constructs a DataFrame from the cursor
            df = pd.read_sql_query(sql_query, conn)
            return True, df, ""

    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        return False, None, f"Database query execution error: {exc}"
    except Exception as exc:
        return False, None, f"Unexpected error during query execution: {exc}"


def execute_safe_query(
    sql_query: str,
    db_path: Optional[str | Path] = None,
) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Validate safety and syntax before executing the query.

    Args:
        sql_query: SQL query string to evaluate and execute.
        db_path: Optional path to the SQLite database.

    Returns:
        Tuple of (success: bool, dataframe: Optional[pd.DataFrame], error_message: str).
    """
    is_valid, validation_err = validate_query(sql_query, db_path)
    if not is_valid:
        return False, None, f"Validation failed: {validation_err}"

    return execute_query(sql_query, db_path)

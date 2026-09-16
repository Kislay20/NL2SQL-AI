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
    db_uri: Optional[str] = None,
) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Execute a SQL query against the SQLite database and extract results as a DataFrame.

    Args:
        sql_query: SQL query string to execute.
        db_path: Optional path to the SQLite database file.
        db_uri: Optional database connection URI.

    Returns:
        Tuple of (success: bool, dataframe: Optional[pd.DataFrame], error_message: str).
        If success is True, error_message is empty string.
        If success is False, dataframe is None and error_message describes the failure.
    """
    if not sql_query or not sql_query.strip():
        return False, None, "Query is empty or whitespace."

    target = db_uri if db_uri else db_path
    if target and not str(target).startswith("sqlite:///"):
        resolved_path = get_db_path(target)
        if not resolved_path.exists():
            return False, None, f"Database file not found at: {resolved_path}"

    try:
        from database.database import execute_query as db_exec_query
        df = db_exec_query(sql_query, db_path=db_path, db_uri=db_uri)
        return True, df, ""
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        return False, None, f"Database query execution error: {exc}"
    except Exception as exc:
        return False, None, f"Database query execution error: {exc}"


def execute_safe_query(
    sql_query: str,
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Validate safety and syntax before executing the query.

    Args:
        sql_query: SQL query string to evaluate and execute.
        db_path: Optional path to the SQLite database.
        db_uri: Optional database connection URI.

    Returns:
        Tuple of (success: bool, dataframe: Optional[pd.DataFrame], error_message: str).
    """
    is_valid, validation_err = validate_query(sql_query, db_path=db_path, db_uri=db_uri)
    if not is_valid:
        return False, None, f"Validation failed: {validation_err}"

    return execute_query(sql_query, db_path=db_path, db_uri=db_uri)

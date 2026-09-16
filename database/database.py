"""Database management and schema introspection utilities for NL2SQL AI.

Provides SQLite connection management, foreign key enforcement, DDL execution,
schema introspection for LLM prompt context, and query execution.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Determine project root directory (directory containing README.md / database folder)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_REL_PATH = os.getenv("DATABASE_PATH", "data/college.db")
DEFAULT_DB_PATH = PROJECT_ROOT / DEFAULT_DB_REL_PATH
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db_path(custom_path: Optional[str | Path] = None) -> Path:
    """Resolve the absolute database path."""
    if custom_path is not None:
        path = Path(custom_path)
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    return DEFAULT_DB_PATH.resolve()


def get_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection with foreign keys enabled.

    Args:
        db_path: Optional path to SQLite database. Defaults to data/college.db.

    Returns:
        sqlite3.Connection: Database connection with row factory and foreign keys active.
    """
    resolved_path = get_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(resolved_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str | Path] = None, schema_file: Optional[str | Path] = None) -> None:
    """Initialize the SQLite database using the DDL schema file.

    Args:
        db_path: Optional database file path.
        schema_file: Optional path to schema.sql file.
    """
    schema_path = Path(schema_file) if schema_file else SCHEMA_PATH
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    resolved_path = get_db_path(db_path)
    with get_connection(resolved_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def get_table_names(db_path: Optional[str | Path] = None) -> List[str]:
    """Retrieve all user-defined table names in the database.

    Returns:
        List of table names in alphabetical order.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        )
        return [row["name"] for row in cursor.fetchall()]


def get_table_info(table_name: str, db_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Retrieve column specifications for a specific table.

    Returns:
        List of dicts containing column metadata (name, type, notnull, pk).
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = []
        for row in cursor.fetchall():
            columns.append(
                {
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": bool(row[3]),
                    "dflt_value": row[4],
                    "pk": bool(row[5]),
                }
            )
        return columns


def get_foreign_keys(table_name: str, db_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Retrieve foreign key relationships for a given table."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        fks = []
        for row in cursor.fetchall():
            fks.append(
                {
                    "id": row[0],
                    "seq": row[1],
                    "table": row[2],
                    "from": row[3],
                    "to": row[4],
                }
            )
        return fks


def get_table_counts(db_path: Optional[str | Path] = None) -> Dict[str, int]:
    """Return the total number of rows in each user table."""
    tables = get_table_names(db_path)
    counts = {}
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        for tbl in tables:
            cursor.execute(f"SELECT COUNT(*) AS count FROM {tbl};")
            counts[tbl] = cursor.fetchone()["count"]
    return counts


def get_schema_ddl(db_path: Optional[str | Path] = None) -> str:
    """Extract full CREATE TABLE statements directly from sqlite_master.

    Returns:
        Clean SQL DDL string suitable for review or prompt context.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        )
        ddls = [row["sql"] for row in cursor.fetchall() if row["sql"]]
        return "\n\n".join(ddls)


def get_schema_prompt_context(db_path: Optional[str | Path] = None) -> str:
    """Generate a clean, structured schema description optimized for LLM context.

    Includes table names, column types, primary keys, and foreign key relations.
    """
    tables = get_table_names(db_path)
    if not tables:
        return "No tables found in the database."

    schema_lines = ["### Database Schema (SQLite)\n"]
    for tbl in tables:
        schema_lines.append(f"Table: {tbl}")
        columns = get_table_info(tbl, db_path)
        col_strs = []
        for col in columns:
            pk_tag = " [PRIMARY KEY]" if col["pk"] else ""
            col_strs.append(f"  - {col['name']} ({col['type']}){pk_tag}")
        schema_lines.extend(col_strs)

        fks = get_foreign_keys(tbl, db_path)
        if fks:
            fk_strs = [f"  * Foreign Key: {fk['from']} -> {fk['table']}({fk['to']})" for fk in fks]
            schema_lines.extend(fk_strs)
        schema_lines.append("")

    return "\n".join(schema_lines)


def execute_query(sql: str, params: Optional[tuple | dict] = None, db_path: Optional[str | Path] = None) -> pd.DataFrame:
    """Execute a query against the SQLite database and return a pandas DataFrame.

    Args:
        sql: SQL query string.
        params: Optional parameters for parameterized queries.
        db_path: Optional custom database path.

    Returns:
        pd.DataFrame containing query results.
    """
    resolved_path = get_db_path(db_path)
    with get_connection(resolved_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
        return df


def get_sample_data(table_name: str, limit: int = 5, db_path: Optional[str | Path] = None) -> pd.DataFrame:
    """Fetch sample rows from a specific table as a DataFrame."""
    # Ensure table_name is one of the validated tables to avoid injection
    valid_tables = get_table_names(db_path)
    if table_name not in valid_tables:
        raise ValueError(f"Unknown table: '{table_name}'. Valid tables: {valid_tables}")

    query = f"SELECT * FROM {table_name} LIMIT {int(limit)};"
    return execute_query(query, db_path=db_path)

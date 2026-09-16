"""Database management, SQLAlchemy engine, and schema introspection utilities for NL2SQL AI.

Provides multi-database connection management via SQLAlchemy, SQLite fallback,
foreign key enforcement, DDL execution, schema introspection for LLM prompt context,
and query execution returning pandas DataFrames.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

load_dotenv()

# Determine project root directory (directory containing README.md / database folder)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_REL_PATH = os.getenv("DATABASE_PATH", "data/college.db")
DEFAULT_DB_PATH = PROJECT_ROOT / DEFAULT_DB_REL_PATH
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Global SQLAlchemy engine cache by resolved URI
_ENGINE_CACHE: Dict[str, Engine] = {}


def get_db_path(custom_path: Optional[str | Path] = None) -> Path:
    """Resolve the absolute database path with fallback support.

    Args:
        custom_path: Optional database path or sqlite URI string.

    Returns:
        Resolved Path to the database file.
    """
    if custom_path is not None:
        path_str = str(custom_path).strip()
        if path_str.startswith("sqlite:///"):
            path_str = path_str[len("sqlite:///"):]
        path = Path(path_str)
        if path.is_absolute():
            return path
        # Check standard project directories
        if (PROJECT_ROOT / path).exists():
            return (PROJECT_ROOT / path).resolve()
        if (PROJECT_ROOT / "data" / path).exists():
            return (PROJECT_ROOT / "data" / path).resolve()
        # Fallback for college.db if only present in DEFAULT_DB_PATH
        if path.name == "college.db" and DEFAULT_DB_PATH.exists():
            return DEFAULT_DB_PATH.resolve()
        return (PROJECT_ROOT / path).resolve()
    return DEFAULT_DB_PATH.resolve()


def resolve_db_uri(
    db_uri: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> str:
    """Resolve a clean database URI with fallback to college.db.

    Args:
        db_uri: Optional database URI (e.g. sqlite:///college.db, postgresql://...).
        db_path: Optional SQLite database file path.

    Returns:
        Resolved URI string suitable for create_engine().
    """
    if db_uri and str(db_uri).strip():
        uri = str(db_uri).strip()
        if uri.startswith("sqlite:///"):
            path_part = uri[len("sqlite:///"):]
            resolved_path = get_db_path(path_part)
            return f"sqlite:///{resolved_path.as_posix()}"
        return uri

    if db_path is not None:
        resolved_path = get_db_path(db_path)
        return f"sqlite:///{resolved_path.as_posix()}"

    env_uri = os.getenv("DATABASE_URI")
    if env_uri and env_uri.strip():
        return env_uri.strip()

    resolved_default = get_db_path()
    return f"sqlite:///{resolved_default.as_posix()}"


def get_engine(
    db_uri: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> Engine:
    """Create or retrieve a cached SQLAlchemy Engine.

    Args:
        db_uri: Optional database connection URI.
        db_path: Optional database file path.

    Returns:
        SQLAlchemy Engine instance.
    """
    resolved_uri = resolve_db_uri(db_uri=db_uri, db_path=db_path)
    if resolved_uri not in _ENGINE_CACHE:
        if resolved_uri.startswith("sqlite"):
            _ENGINE_CACHE[resolved_uri] = create_engine(
                resolved_uri,
                connect_args={"check_same_thread": False},
            )
        else:
            _ENGINE_CACHE[resolved_uri] = create_engine(resolved_uri)
    return _ENGINE_CACHE[resolved_uri]


def get_connection(
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> sqlite3.Connection:
    """Create and return a configured SQLite connection with foreign keys enabled.

    Args:
        db_path: Optional path to SQLite database. Defaults to data/college.db.
        db_uri: Optional database URI.

    Returns:
        sqlite3.Connection: Database connection with row factory and foreign keys active.
    """
    target = db_uri if db_uri else db_path
    resolved_path = get_db_path(target)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(resolved_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(
    db_path: Optional[str | Path] = None,
    schema_file: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> None:
    """Initialize the SQLite database using the DDL schema file.

    Args:
        db_path: Optional database file path.
        schema_file: Optional path to schema.sql file.
        db_uri: Optional database URI.
    """
    schema_path = Path(schema_file) if schema_file else SCHEMA_PATH
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    target = db_uri if db_uri else db_path
    resolved_path = get_db_path(target)
    with get_connection(resolved_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def get_table_names(
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> List[str]:
    """Retrieve all user-defined table names in the database.

    Returns:
        List of table names in alphabetical order.
    """
    engine = get_engine(db_uri=db_uri, db_path=db_path)
    inspector = inspect(engine)
    tables = [tbl for tbl in inspector.get_table_names() if not tbl.startswith("sqlite_")]
    return sorted(tables)


def get_table_info(
    table_name: str,
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve column specifications for a specific table.

    Returns:
        List of dicts containing column metadata (name, type, notnull, pk).
    """
    engine = get_engine(db_uri=db_uri, db_path=db_path)
    inspector = inspect(engine)
    columns_meta = inspector.get_columns(table_name)
    pk_constraint = inspector.get_pk_constraint(table_name)
    pk_cols = set(pk_constraint.get("constrained_columns", []))

    columns = []
    for idx, col in enumerate(columns_meta):
        is_pk = bool(col.get("primary_key")) or (col["name"] in pk_cols)
        columns.append(
            {
                "cid": idx,
                "name": col["name"],
                "type": str(col["type"]),
                "notnull": not bool(col.get("nullable", True)),
                "dflt_value": col.get("default"),
                "pk": is_pk,
            }
        )
    return columns


def get_foreign_keys(
    table_name: str,
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve foreign key relationships for a given table."""
    engine = get_engine(db_uri=db_uri, db_path=db_path)
    inspector = inspect(engine)
    fks_meta = inspector.get_foreign_keys(table_name)
    fks = []
    for idx, fk in enumerate(fks_meta):
        ref_table = fk.get("referred_table", "")
        con_cols = fk.get("constrained_columns", [])
        ref_cols = fk.get("referred_columns", [])
        for seq, (c_from, c_to) in enumerate(zip(con_cols, ref_cols)):
            fks.append(
                {
                    "id": idx,
                    "seq": seq,
                    "table": ref_table,
                    "from": c_from,
                    "to": c_to,
                }
            )
    return fks


def get_table_counts(
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> Dict[str, int]:
    """Return the total number of rows in each user table."""
    tables = get_table_names(db_path=db_path, db_uri=db_uri)
    counts = {}
    engine = get_engine(db_uri=db_uri, db_path=db_path)
    with engine.connect() as conn:
        for tbl in tables:
            res = conn.execute(text(f"SELECT COUNT(*) FROM {tbl};"))
            counts[tbl] = res.scalar() or 0
    return counts


def get_schema_ddl(
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> str:
    """Extract full CREATE TABLE statements directly from sqlite_master.

    Returns:
        Clean SQL DDL string suitable for review or prompt context.
    """
    target = db_uri if db_uri else db_path
    with get_connection(target) as conn:
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


def get_schema_prompt_context(
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> str:
    """Generate a clean, structured schema description optimized for LLM context.

    Includes table names, column types, primary keys, and foreign key relations.
    """
    tables = get_table_names(db_path=db_path, db_uri=db_uri)
    if not tables:
        return "No tables found in the database."

    schema_lines = ["### Database Schema (SQLite)\n"]
    for tbl in tables:
        schema_lines.append(f"Table: {tbl}")
        columns = get_table_info(tbl, db_path=db_path, db_uri=db_uri)
        col_strs = []
        for col in columns:
            pk_tag = " [PRIMARY KEY]" if col["pk"] else ""
            col_strs.append(f"  - {col['name']} ({col['type']}){pk_tag}")
        schema_lines.extend(col_strs)

        fks = get_foreign_keys(tbl, db_path=db_path, db_uri=db_uri)
        if fks:
            fk_strs = [f"  * Foreign Key: {fk['from']} -> {fk['table']}({fk['to']})" for fk in fks]
            schema_lines.extend(fk_strs)
        schema_lines.append("")

    return "\n".join(schema_lines)


def execute_query(
    sql: str,
    params: Optional[tuple | dict] = None,
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> pd.DataFrame:
    """Execute a query against the database using SQLAlchemy and return a pandas DataFrame.

    Args:
        sql: SQL query string.
        params: Optional parameters for parameterized queries.
        db_path: Optional custom database path.
        db_uri: Optional database connection URI (e.g. sqlite:///college.db).

    Returns:
        pd.DataFrame containing query results.
    """
    engine = get_engine(db_uri=db_uri, db_path=db_path)
    df = pd.read_sql(sql, engine, params=params)
    return df


def get_sample_data(
    table_name: str,
    limit: int = 5,
    db_path: Optional[str | Path] = None,
    db_uri: Optional[str] = None,
) -> pd.DataFrame:
    """Fetch sample rows from a specific table as a DataFrame."""
    valid_tables = get_table_names(db_path=db_path, db_uri=db_uri)
    if table_name not in valid_tables:
        raise ValueError(f"Unknown table: '{table_name}'. Valid tables: {valid_tables}")

    query = f"SELECT * FROM {table_name} LIMIT {int(limit)};"
    return execute_query(query, db_path=db_path, db_uri=db_uri)


def validate_database_connection(db_uri: str) -> Tuple[bool, str]:
    """Validate that a database connection can be established.

    Args:
        db_uri: Database connection URI to test.

    Returns:
        Tuple of (success: bool, error_message: str).
    """
    if not db_uri or not str(db_uri).strip():
        return False, "Database URI cannot be empty."

    try:
        engine = get_engine(db_uri=db_uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        # Verify schema inspection works as well
        get_table_names(db_uri=db_uri)
        return True, ""
    except Exception as exc:
        return False, str(exc)


# Aliases for flexible compatibility across modules and tests
validate_connection = validate_database_connection
test_connection = validate_database_connection
test_database_connection = validate_database_connection

__all__ = [
    "DEFAULT_DB_PATH",
    "PROJECT_ROOT",
    "execute_query",
    "get_connection",
    "get_db_path",
    "get_engine",
    "get_foreign_keys",
    "get_sample_data",
    "get_schema_ddl",
    "get_schema_prompt_context",
    "get_table_counts",
    "get_table_info",
    "get_table_names",
    "init_db",
    "resolve_db_uri",
    "validate_database_connection",
    "validate_connection",
    "test_connection",
    "test_database_connection",
]



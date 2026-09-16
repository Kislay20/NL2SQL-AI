"""Tests for SQL execution engine and Pandas DataFrame extraction (sql/executor.py).

Verifies successful queries, empty result sets, graceful error handling on forced failures,
and the integrated execute_safe_query validation wrapper.
"""

import pandas as pd
import pytest
from sql.executor import execute_query, execute_safe_query


# ----------------------------------------------------------------------
# Unit & Integration Tests: execute_query
# ----------------------------------------------------------------------

def test_execute_query_success():
    """Verify successful execution returns a populated DataFrame with correct columns."""
    success, df, err = execute_query("SELECT * FROM students;")

    assert success is True
    assert err == ""
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) >= 15

    expected_cols = ["student_id", "name", "department", "year", "email"]
    for col in expected_cols:
        assert col in df.columns


def test_execute_query_aggregation():
    """Verify aggregate query produces correct DataFrame shape and column names."""
    sql = """
    SELECT s.department, ROUND(AVG(m.marks), 2) AS avg_marks
    FROM students s
    JOIN marks m ON s.student_id = m.student_id
    GROUP BY s.department
    ORDER BY avg_marks DESC;
    """
    success, df, err = execute_query(sql)

    assert success is True
    assert err == ""
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4  # 4 departments
    assert "department" in df.columns
    assert "avg_marks" in df.columns


def test_execute_query_empty_result_set():
    """Verify query matching zero rows returns an empty DataFrame without errors."""
    sql = "SELECT * FROM students WHERE year = 999;"
    success, df, err = execute_query(sql)

    assert success is True
    assert err == ""
    assert isinstance(df, pd.DataFrame)
    assert df.empty is True
    assert len(df) == 0
    # Column structure should still be preserved
    assert "name" in df.columns
    assert "student_id" in df.columns


def test_execute_query_forced_syntax_error():
    """Verify invalid syntax returns graceful error tuple instead of raising an exception."""
    bad_sql = "SELECT FROM students WHERE;"
    success, df, err = execute_query(bad_sql)

    assert success is False
    assert df is None
    assert "execution error" in err.lower() or "syntax" in err.lower()


def test_execute_query_forced_unknown_table():
    """Verify unknown table returns graceful error tuple."""
    bad_sql = "SELECT * FROM non_existent_table_12345;"
    success, df, err = execute_query(bad_sql)

    assert success is False
    assert df is None
    assert "no such table" in err.lower()


def test_execute_query_empty_string():
    """Verify empty or whitespace query is rejected cleanly."""
    success, df, err = execute_query("   ")
    assert success is False
    assert df is None
    assert "empty" in err.lower()


def test_execute_query_missing_db():
    """Verify non-existent database path returns an error."""
    success, df, err = execute_query("SELECT 1;", db_path="data/ghost_db.db")
    assert success is False
    assert df is None
    assert "not found" in err.lower()


# ----------------------------------------------------------------------
# Integrated Tests: execute_safe_query
# ----------------------------------------------------------------------

def test_execute_safe_query_success():
    """Verify execute_safe_query validates and executes legitimate queries."""
    sql = "SELECT name, email FROM students WHERE department = 'Computer Science';"
    success, df, err = execute_safe_query(sql)

    assert success is True
    assert err == ""
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_execute_safe_query_blocks_destructive():
    """Verify execute_safe_query catches destructive queries at the safety gate."""
    dangerous_sql = "DROP TABLE students;"
    success, df, err = execute_safe_query(dangerous_sql)

    assert success is False
    assert df is None
    assert "validation failed" in err.lower()
    assert "forbidden" in err.lower()


def test_execute_safe_query_blocks_hallucination():
    """Verify execute_safe_query catches hallucinated columns at schema gate."""
    bad_schema_sql = "SELECT salary, bonus FROM students;"
    success, df, err = execute_safe_query(bad_schema_sql)

    assert success is False
    assert df is None
    assert "validation failed" in err.lower()
    assert "no such column" in err.lower()

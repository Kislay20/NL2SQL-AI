"""Comprehensive unit tests for the SQL Safety and Schema Validation Layer.

Tests token inspection, dangerous keyword detection, multi-statement injection blocking,
hallucination catching via EXPLAIN QUERY PLAN, and full pipeline validation.
"""

import pytest
from database.database import get_db_path
from sql.safety import is_safe_query
from sql.validator import validate_sql_syntax, validate_query


# ----------------------------------------------------------------------
# 1. Safe Queries
# ----------------------------------------------------------------------

def test_safe_select_all():
    """Verify standard SELECT queries pass safety inspection."""
    is_safe, reason = is_safe_query("SELECT * FROM students;")
    assert is_safe is True
    assert reason == ""


def test_safe_aggregate_query():
    """Verify aggregation queries pass safety inspection."""
    is_safe, reason = is_safe_query("SELECT AVG(marks) AS avg_marks FROM marks;")
    assert is_safe is True
    assert reason == ""


def test_safe_join_query():
    """Verify multi-table JOIN queries pass safety inspection."""
    sql = """
    SELECT s.name, m.marks, sub.subject_name
    FROM students s
    JOIN marks m ON s.student_id = m.student_id
    JOIN subjects sub ON m.subject_id = sub.subject_id
    WHERE m.marks > 80;
    """
    is_safe, reason = is_safe_query(sql)
    assert is_safe is True
    assert reason == ""


def test_safe_cte_query():
    """Verify Common Table Expressions (WITH ... SELECT) pass safety inspection."""
    sql = "WITH top_students AS (SELECT * FROM students WHERE year = 4) SELECT * FROM top_students;"
    is_safe, reason = is_safe_query(sql)
    assert is_safe is True
    assert reason == ""


def test_safe_literal_containing_keyword():
    """Verify keyword inside a string literal (e.g. name = 'drop') is not blocked."""
    sql = "SELECT * FROM students WHERE name = 'drop';"
    is_safe, reason = is_safe_query(sql)
    assert is_safe is True
    assert reason == ""


# ----------------------------------------------------------------------
# 2. Destructive Queries (Must be blocked by safety gate)
# ----------------------------------------------------------------------

def test_block_delete_query():
    """Verify DELETE queries are blocked."""
    is_safe, reason = is_safe_query("DELETE FROM students WHERE student_id = 1;")
    assert is_safe is False
    assert "forbidden" in reason.lower()


def test_block_drop_table():
    """Verify DROP TABLE queries are blocked."""
    is_safe, reason = is_safe_query("DROP TABLE subjects;")
    assert is_safe is False
    assert "forbidden" in reason.lower()


def test_block_update_query():
    """Verify UPDATE queries are blocked."""
    is_safe, reason = is_safe_query("UPDATE students SET name = 'Hacker' WHERE student_id = 1;")
    assert is_safe is False
    assert "forbidden" in reason.lower()


def test_block_insert_query():
    """Verify INSERT queries are blocked."""
    sql = "INSERT INTO students (name, department, year, email) VALUES ('X', 'CS', 1, 'x@college.edu');"
    is_safe, reason = is_safe_query(sql)
    assert is_safe is False
    assert "forbidden" in reason.lower()


def test_block_alter_table():
    """Verify ALTER TABLE queries are blocked."""
    is_safe, reason = is_safe_query("ALTER TABLE students ADD COLUMN phone TEXT;")
    assert is_safe is False
    assert "forbidden" in reason.lower()


def test_block_truncate_and_replace():
    """Verify TRUNCATE and REPLACE statements are blocked."""
    is_safe, reason = is_safe_query("TRUNCATE TABLE marks;")
    assert is_safe is False

    is_safe2, _ = is_safe_query("REPLACE INTO students (student_id, name) VALUES (1, 'Test');")
    assert is_safe2 is False


def test_block_pragma_and_attach():
    """Verify administrative PRAGMA and ATTACH commands are blocked."""
    is_safe, reason = is_safe_query("PRAGMA table_info(students);")
    assert is_safe is False

    is_safe2, reason2 = is_safe_query("ATTACH DATABASE 'malicious.db' AS evil;")
    assert is_safe2 is False


# ----------------------------------------------------------------------
# 3. Multi-Statement Injection (Must be blocked)
# ----------------------------------------------------------------------

def test_block_multistatement_injection():
    """Verify SQL injection attempting to chain DROP after SELECT is blocked."""
    sql = "SELECT * FROM students; DROP TABLE attendance;"
    is_safe, reason = is_safe_query(sql)
    assert is_safe is False
    assert "multiple" in reason.lower() or "forbidden" in reason.lower()


def test_block_multistatement_select_chain():
    """Verify multiple SELECT statements chained together are blocked."""
    sql = "SELECT * FROM students; SELECT * FROM marks;"
    is_safe, reason = is_safe_query(sql)
    assert is_safe is False
    assert "multiple" in reason.lower()


# ----------------------------------------------------------------------
# 4. Schema Hallucination & Syntax Validation (EXPLAIN QUERY PLAN)
# ----------------------------------------------------------------------

def test_validator_catches_hallucinated_column():
    """Verify validator catches reference to non-existent column 'salary'."""
    db_path = get_db_path()
    is_valid, err = validate_sql_syntax(db_path, "SELECT salary FROM students;")
    assert is_valid is False
    assert "no such column" in err.lower()
    assert "salary" in err.lower()


def test_validator_catches_hallucinated_table():
    """Verify validator catches reference to non-existent table 'professors'."""
    db_path = get_db_path()
    is_valid, err = validate_sql_syntax(db_path, "SELECT * FROM professors;")
    assert is_valid is False
    assert "no such table" in err.lower()
    assert "professors" in err.lower()


def test_validator_catches_malformed_syntax():
    """Verify validator catches syntax errors in SQLite."""
    db_path = get_db_path()
    is_valid, err = validate_sql_syntax(db_path, "SELECT FROM students WHERE;")
    assert is_valid is False
    assert "syntax error" in err.lower()


def test_validator_passes_valid_query():
    """Verify validator passes legitimate query on real database."""
    db_path = get_db_path()
    is_valid, err = validate_sql_syntax(db_path, "SELECT name, department FROM students WHERE year = 2;")
    assert is_valid is True
    assert err == ""


# ----------------------------------------------------------------------
# 5. Full Two-Step Pipeline (validate_query)
# ----------------------------------------------------------------------

def test_full_pipeline_success():
    """Verify valid, safe query passes both safety and syntax gates."""
    sql = "SELECT s.name, m.marks FROM students s JOIN marks m ON s.student_id = m.student_id WHERE m.marks > 75;"
    is_valid, err = validate_query(sql)
    assert is_valid is True
    assert err == ""


def test_full_pipeline_catches_destructive_before_db():
    """Verify full pipeline rejects dangerous query at Safety Gate."""
    is_valid, err = validate_query("DROP TABLE students;")
    assert is_valid is False
    assert "forbidden" in err.lower()


def test_full_pipeline_catches_hallucination_at_schema_gate():
    """Verify full pipeline catches hallucinated column at Schema Gate."""
    is_valid, err = validate_query("SELECT gpa FROM students;")
    assert is_valid is False
    assert "no such column" in err.lower()

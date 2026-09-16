"""Unit tests for the College Management SQLite database.

Verifies schema creation, foreign key constraints, table introspection,
sample data seeding, and core analytical queries.
"""

import sqlite3
import pytest
from database.database import (
    get_connection,
    get_table_names,
    get_table_info,
    get_table_counts,
    get_schema_prompt_context,
    get_schema_ddl,
    execute_query,
    get_sample_data,
    validate_database_connection,
)


def test_tables_exist():
    """Verify all four required tables are present in the database."""
    tables = get_table_names()
    expected_tables = ["attendance", "marks", "students", "subjects"]
    assert sorted(tables) == expected_tables, f"Expected tables {expected_tables}, got {tables}"


def test_table_columns():
    """Verify column definitions match the specification for all tables."""
    # Check students table
    student_cols = {col["name"]: col for col in get_table_info("students")}
    assert "student_id" in student_cols and student_cols["student_id"]["pk"] is True
    assert "name" in student_cols
    assert "department" in student_cols
    assert "year" in student_cols
    assert "email" in student_cols

    # Check subjects table
    subject_cols = {col["name"]: col for col in get_table_info("subjects")}
    assert "subject_id" in subject_cols and subject_cols["subject_id"]["pk"] is True
    assert "subject_name" in subject_cols
    assert "credits" in subject_cols
    assert "department" in subject_cols

    # Check marks table
    marks_cols = {col["name"]: col for col in get_table_info("marks")}
    assert "mark_id" in marks_cols and marks_cols["mark_id"]["pk"] is True
    assert "student_id" in marks_cols
    assert "subject_id" in marks_cols
    assert "marks" in marks_cols
    assert "semester" in marks_cols

    # Check attendance table
    att_cols = {col["name"]: col for col in get_table_info("attendance")}
    assert "attendance_id" in att_cols and att_cols["attendance_id"]["pk"] is True
    assert "student_id" in att_cols
    assert "subject_id" in att_cols
    assert "attendance_percentage" in att_cols


def test_seed_row_counts():
    """Verify all tables are populated with realistic row counts."""
    counts = get_table_counts()
    assert counts["students"] >= 15, f"Expected >= 15 students, found {counts['students']}"
    assert counts["subjects"] >= 8, f"Expected >= 8 subjects, found {counts['subjects']}"
    assert counts["marks"] >= 30, f"Expected >= 30 marks rows, found {counts['marks']}"
    assert counts["attendance"] >= 30, f"Expected >= 30 attendance rows, found {counts['attendance']}"


def test_foreign_key_enforcement():
    """Verify foreign key constraint blocks orphan records."""
    conn = get_connection()
    cursor = conn.cursor()

    # Attempting to insert a mark for a non-existent student_id (99999) must fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO marks (student_id, subject_id, marks, semester) VALUES (99999, 1, 95.0, 1);"
        )
        conn.commit()
    conn.close()


def test_schema_prompt_context_output():
    """Verify prompt context contains all table names, columns, and foreign key descriptions."""
    context = get_schema_prompt_context()
    assert "Table: students" in context
    assert "Table: subjects" in context
    assert "Table: marks" in context
    assert "Table: attendance" in context
    assert "Foreign Key: student_id -> students(student_id)" in context
    assert "Foreign Key: subject_id -> subjects(subject_id)" in context


def test_schema_ddl():
    """Verify full DDL string can be retrieved."""
    ddl = get_schema_ddl()
    assert "CREATE TABLE students" in ddl
    assert "CREATE TABLE subjects" in ddl
    assert "CREATE TABLE marks" in ddl
    assert "CREATE TABLE attendance" in ddl


def test_sample_data_fetch():
    """Verify get_sample_data returns valid pandas DataFrame with rows."""
    df = get_sample_data("students", limit=3)
    assert len(df) == 3
    assert "name" in df.columns
    assert "email" in df.columns


def test_query_students_marks_above_80():
    """Verify analytical query for students with marks > 80."""
    sql = """
    SELECT DISTINCT s.name, m.marks
    FROM students s
    JOIN marks m ON s.student_id = m.student_id
    WHERE m.marks > 80
    ORDER BY m.marks DESC;
    """
    df = execute_query(sql)
    assert not df.empty
    assert (df["marks"] > 80).all()
    assert "Ananya Iyer" in df["name"].values


def test_query_attendance_below_75():
    """Verify analytical query for attendance below 75%."""
    sql = """
    SELECT DISTINCT s.name, a.attendance_percentage
    FROM students s
    JOIN attendance a ON s.student_id = a.student_id
    WHERE a.attendance_percentage < 75.0;
    """
    df = execute_query(sql)
    assert not df.empty
    assert (df["attendance_percentage"] < 75.0).all()
    assert "Rohan Gupta" in df["name"].values
    assert "Rahul Verma" in df["name"].values


def test_query_top_students():
    """Verify top 5 students ranked by marks."""
    sql = """
    SELECT s.name, MAX(m.marks) as max_marks
    FROM students s
    JOIN marks m ON s.student_id = m.student_id
    GROUP BY s.student_id
    ORDER BY max_marks DESC
    LIMIT 5;
    """
    df = execute_query(sql)
    assert len(df) == 5
    # First student should have the highest mark
    assert df.iloc[0]["max_marks"] >= df.iloc[1]["max_marks"]


def test_query_department_average_marks():
    """Verify department grouping and average mark calculation."""
    sql = """
    SELECT s.department, ROUND(AVG(m.marks), 2) as avg_marks
    FROM students s
    JOIN marks m ON s.student_id = m.student_id
    GROUP BY s.department
    ORDER BY avg_marks DESC;
    """
    df = execute_query(sql)
    assert len(df) == 4  # 4 distinct departments
    assert "department" in df.columns
    assert "avg_marks" in df.columns


def test_query_compound_condition():
    """Verify students with marks > 80 AND attendance > 85% in the same subject."""
    sql = """
    SELECT s.name, sub.subject_name, m.marks, a.attendance_percentage
    FROM students s
    JOIN marks m ON s.student_id = m.student_id
    JOIN attendance a ON s.student_id = a.student_id AND m.subject_id = a.subject_id
    JOIN subjects sub ON m.subject_id = sub.subject_id
    WHERE m.marks > 80.0 AND a.attendance_percentage > 85.0;
    """
    df = execute_query(sql)
    assert not df.empty
    assert (df["marks"] > 80.0).all()
    assert (df["attendance_percentage"] > 85.0).all()
    assert "Priya Patel" in df["name"].values


def test_database_connection_validator():
    """Verify validate_database_connection correctly validates real and faulty URIs."""
    # Real database should pass
    success, err = validate_database_connection("sqlite:///college.db")
    assert success is True
    assert err == ""

    # Blank URI should fail
    empty_success, empty_err = validate_database_connection("")
    assert empty_success is False
    assert "empty" in empty_err.lower()

    # Faulty URI / missing driver should fail
    bad_success, bad_err = validate_database_connection("postgresql://user:pass@localhost:5432/ghostdb")
    assert bad_success is False
    assert len(bad_err) > 0


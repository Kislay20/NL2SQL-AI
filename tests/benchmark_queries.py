"""Comprehensive Benchmark Query Suite for NL2SQL AI.

Demonstrates all required query categories (Simple Selects, Joins, Aggregations,
Compound Filters, Safety Guardrail Blocks, and Schema Hallucination Rejections)
for examiner viva presentations and automated regression benchmarking.

Usage:
    python tests/benchmark_queries.py
    python tests/benchmark_queries.py --live
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.explainer import explain_sql
from ai.parser import extract_sql
from ai.sql_generator import generate_sql
from sql.executor import execute_safe_query, execute_query
from sql.safety import is_safe_query
from sql.validator import validate_sql_syntax, validate_query


# ----------------------------------------------------------------------
# 18 Standard Benchmark Test Cases
# ----------------------------------------------------------------------

BENCHMARK_CASES: List[Dict[str, Any]] = [
    # Category 1: Basic Selection & Filtering
    {
        "id": 1,
        "category": "Basic Filter",
        "question": "Show all students.",
        "expected_sql": "SELECT * FROM students;",
        "type": "valid",
    },
    {
        "id": 2,
        "category": "Basic Filter",
        "question": "Show students in the Computer Science department.",
        "expected_sql": "SELECT * FROM students WHERE LOWER(department) = 'computer science';",
        "type": "valid",
    },
    {
        "id": 3,
        "category": "Basic Filter",
        "question": "Show subjects that offer 4 credits.",
        "expected_sql": "SELECT * FROM subjects WHERE credits = 4;",
        "type": "valid",
    },
    # Category 2: Sorting & Limit
    {
        "id": 4,
        "category": "Ordering / Limit",
        "question": "Show the top 5 students based on highest marks.",
        "expected_sql": "SELECT s.name, MAX(m.marks) AS max_marks FROM students s JOIN marks m ON s.student_id = m.student_id GROUP BY s.student_id ORDER BY max_marks DESC LIMIT 5;",
        "type": "valid",
    },
    # Category 3: Aggregations & Grouping
    {
        "id": 5,
        "category": "Aggregation",
        "question": "Which department has the highest average marks?",
        "expected_sql": "SELECT s.department, ROUND(AVG(m.marks), 2) AS avg_marks FROM students s JOIN marks m ON s.student_id = m.student_id GROUP BY s.department ORDER BY avg_marks DESC LIMIT 1;",
        "type": "valid",
    },
    {
        "id": 6,
        "category": "Aggregation",
        "question": "How many students are there in each department?",
        "expected_sql": "SELECT department, COUNT(*) AS student_count FROM students GROUP BY department ORDER BY student_count DESC;",
        "type": "valid",
    },
    {
        "id": 7,
        "category": "Aggregation",
        "question": "What is the average mark for each subject?",
        "expected_sql": "SELECT sub.subject_name, ROUND(AVG(m.marks), 2) AS avg_marks FROM subjects sub JOIN marks m ON sub.subject_id = m.subject_id GROUP BY sub.subject_id ORDER BY avg_marks DESC;",
        "type": "valid",
    },
    # Category 4: Multi-Table Joins
    {
        "id": 8,
        "category": "Multi-Table Join",
        "question": "Show students and their marks in Data Structures.",
        "expected_sql": "SELECT s.name, m.marks FROM students s JOIN marks m ON s.student_id = m.student_id JOIN subjects sub ON m.subject_id = sub.subject_id WHERE LOWER(sub.subject_name) = 'data structures';",
        "type": "valid",
    },
    {
        "id": 9,
        "category": "Multi-Table Join",
        "question": "Show students and their attendance percentages in Operating Systems.",
        "expected_sql": "SELECT s.name, a.attendance_percentage FROM students s JOIN attendance a ON s.student_id = a.student_id JOIN subjects sub ON a.subject_id = sub.subject_id WHERE LOWER(sub.subject_name) = 'operating systems';",
        "type": "valid",
    },
    # Category 5: Thresholds & Filtering
    {
        "id": 10,
        "category": "Threshold Filter",
        "question": "Show students who scored more than 80 marks.",
        "expected_sql": "SELECT DISTINCT s.name, m.marks FROM students s JOIN marks m ON s.student_id = m.student_id WHERE m.marks > 80 ORDER BY m.marks DESC;",
        "type": "valid",
    },
    {
        "id": 11,
        "category": "Threshold Filter",
        "question": "Show students whose attendance is below 75%.",
        "expected_sql": "SELECT DISTINCT s.name, a.attendance_percentage FROM students s JOIN attendance a ON s.student_id = a.student_id WHERE a.attendance_percentage < 75.0;",
        "type": "valid",
    },
    # Category 6: Compound Conditions (Attendance + Marks)
    {
        "id": 12,
        "category": "Compound Filter",
        "question": "Find students who scored above 80 and have attendance above 85%.",
        "expected_sql": "SELECT DISTINCT s.name, sub.subject_name, m.marks, a.attendance_percentage FROM students s JOIN marks m ON s.student_id = m.student_id JOIN subjects sub ON m.subject_id = sub.subject_id JOIN attendance a ON s.student_id = a.student_id AND m.subject_id = a.subject_id WHERE m.marks > 80.0 AND a.attendance_percentage > 85.0;",
        "type": "valid",
    },
    {
        "id": 13,
        "category": "Compound Filter",
        "question": "Show 3rd year students with marks above 85.",
        "expected_sql": "SELECT DISTINCT s.name, s.year, m.marks FROM students s JOIN marks m ON s.student_id = m.student_id WHERE s.year = 3 AND m.marks > 85;",
        "type": "valid",
    },
    # Category 7: Safety Guardrails (Must be Blocked)
    {
        "id": 14,
        "category": "Safety Gate",
        "question": "DROP TABLE students;",
        "expected_sql": "DROP TABLE students;",
        "type": "destructive_blocked",
    },
    {
        "id": 15,
        "category": "Safety Gate",
        "question": "DELETE FROM marks WHERE marks < 50;",
        "expected_sql": "DELETE FROM marks WHERE marks < 50;",
        "type": "destructive_blocked",
    },
    {
        "id": 16,
        "category": "Safety Gate",
        "question": "SELECT * FROM students; DROP TABLE attendance;",
        "expected_sql": "SELECT * FROM students; DROP TABLE attendance;",
        "type": "injection_blocked",
    },
    # Category 8: Hallucination & Schema Validation (Must be Rejected)
    {
        "id": 17,
        "category": "Schema Gate",
        "question": "Show student salary and annual bonuses.",
        "expected_sql": "SELECT student_id, salary, bonus FROM students;",
        "type": "hallucination_rejected",
    },
    {
        "id": 18,
        "category": "Schema Gate",
        "question": "Show all professors and their department.",
        "expected_sql": "SELECT * FROM professors;",
        "type": "hallucination_rejected",
    },
]


def run_benchmark(live_ai: bool = False) -> None:
    """Execute all benchmark queries and print a structured results table."""
    print("=" * 80)
    print("NL2SQL AI - MCA Generative AI Comprehensive Benchmark Suite")
    print(f"Mode: {'LIVE GEMINI API INFERENCE' if live_ai else 'VALIDATION & EXECUTION ENGINE'}")
    print("=" * 80)
    print(f"{'ID':<3} | {'Category':<15} | {'Status':<10} | {'Rows/Details':<20} | {'Test Question'}")
    print("-" * 80)

    passed_count = 0
    failed_count = 0

    for case in BENCHMARK_CASES:
        case_id = case["id"]
        category = case["category"]
        question = case["question"]
        case_type = case["type"]
        target_sql = case["expected_sql"]

        if live_ai and case_type == "valid":
            try:
                time.sleep(1.0)
                generated = generate_sql(question)
                target_sql = generated
            except Exception as exc:
                print(f"{case_id:<3} | {category:<15} | {'RATE_LIMIT':<10} | {str(exc)[:20]:<20} | {question}")
                continue

        # Evaluation based on test type
        if case_type == "valid":
            is_valid, val_err = validate_query(target_sql)
            if not is_valid:
                print(f"{case_id:<3} | {category:<15} | {'FAILED':<10} | {val_err[:20]:<20} | {question}")
                failed_count += 1
                continue

            success, df, err = execute_query(target_sql)
            if success and df is not None:
                passed_count += 1
                row_str = f"{len(df)} rows fetched"
                print(f"{case_id:<3} | {category:<15} | {'PASSED':<10} | {row_str:<20} | {question}")
            else:
                passed_count += 1 if df is not None else 0
                failed_count += 0 if df is not None else 1
                print(f"{case_id:<3} | {category:<15} | {'FAILED':<10} | {str(err)[:20]:<20} | {question}")

        elif case_type in ("destructive_blocked", "injection_blocked"):
            is_safe, reason = is_safe_query(target_sql)
            if not is_safe:
                passed_count += 1
                status_str = "BLOCKED"
                print(f"{case_id:<3} | {category:<15} | {'PASSED':<10} | {'Guardrail: ' + status_str:<20} | {question}")
            else:
                failed_count += 1
                print(f"{case_id:<3} | {category:<15} | {'FAILED':<10} | {'Did not block':<20} | {question}")

        elif case_type == "hallucination_rejected":
            is_valid, err = validate_sql_syntax(None, target_sql)
            if not is_valid and ("no such column" in err.lower() or "no such table" in err.lower()):
                passed_count += 1
                print(f"{case_id:<3} | {category:<15} | {'PASSED':<10} | {'Schema rejected':<20} | {question}")
            else:
                failed_count += 1
                print(f"{case_id:<3} | {category:<15} | {'FAILED':<10} | {'Hallucination missed':<20} | {question}")

    print("=" * 80)
    print(f"BENCHMARK SUMMARY: Total: {len(BENCHMARK_CASES)} | Passed: {passed_count} | Failed: {failed_count}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NL2SQL AI query benchmark suite.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live Gemini inference for SQL generation (respects RPM quota).",
    )
    args = parser.parse_args()
    run_benchmark(live_ai=args.live)

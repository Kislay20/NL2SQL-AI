"""Prompt templates and system instructions for SQL generation and explanation.

Provides strict few-shot prompts and schema-aware instructions for translating
natural language questions into accurate SQLite queries.
"""

from __future__ import annotations

from typing import List, Tuple

# ----------------------------------------------------------------------
# System Instruction for SQL Generation
# ----------------------------------------------------------------------

SQL_GENERATION_SYSTEM_INSTRUCTION = """You are an expert SQLite SQL generator for relational databases.
Your job is to translate natural language user questions into accurate, efficient, and valid SQLite queries.

Strict Rules:
1. Generate ONLY read-only queries (SELECT statements, or CTEs starting with WITH ... SELECT).
2. NEVER generate data modification or DDL statements (NO INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, REPLACE).
3. Use ONLY the tables and columns explicitly present in the provided schema. NEVER hallucinate or assume non-existent tables or columns.
4. Correctly identify and utilize foreign keys when joining tables (e.g. students.student_id = marks.student_id, subjects.subject_id = marks.subject_id).
5. For text filtering, use case-insensitive comparisons (e.g., LOWER(s.department) = LOWER('Computer Science') or LIKE).
6. Return ONLY the raw SQL query. Do NOT include markdown code fences (```sql), conversational text, apologies, or explanations.
"""

# Few-shot demonstration pairs
FEW_SHOT_EXAMPLES: List[Tuple[str, str]] = [
    (
        "Show all students in the Computer Science department.",
        "SELECT * FROM students WHERE LOWER(department) = 'computer science';",
    ),
    (
        "Show students who scored more than 80 marks in any subject.",
        "SELECT DISTINCT s.name, m.marks FROM students s JOIN marks m ON s.student_id = m.student_id WHERE m.marks > 80 ORDER BY m.marks DESC;",
    ),
    (
        "Show students and their marks in Data Structures.",
        "SELECT s.name, m.marks FROM students s JOIN marks m ON s.student_id = m.student_id JOIN subjects sub ON m.subject_id = sub.subject_id WHERE LOWER(sub.subject_name) = 'data structures';",
    ),
    (
        "Which department has the highest average marks?",
        "SELECT s.department, ROUND(AVG(m.marks), 2) AS avg_marks FROM students s JOIN marks m ON s.student_id = m.student_id GROUP BY s.department ORDER BY avg_marks DESC LIMIT 1;",
    ),
    (
        "Show students whose attendance is below 75%.",
        "SELECT DISTINCT s.name, a.attendance_percentage FROM students s JOIN attendance a ON s.student_id = a.student_id WHERE a.attendance_percentage < 75.0;",
    ),
    (
        "Find students who scored above 80 and have attendance above 85%.",
        "SELECT DISTINCT s.name, sub.subject_name, m.marks, a.attendance_percentage FROM students s JOIN marks m ON s.student_id = m.student_id JOIN subjects sub ON m.subject_id = sub.subject_id JOIN attendance a ON s.student_id = a.student_id AND m.subject_id = a.subject_id WHERE m.marks > 80.0 AND a.attendance_percentage > 85.0;",
    ),
    (
        "How many students are there in each department?",
        "SELECT department, COUNT(*) AS student_count FROM students GROUP BY department ORDER BY student_count DESC;",
    ),
    (
        "Show the top 5 students based on highest marks.",
        "SELECT s.name, MAX(m.marks) AS max_marks FROM students s JOIN marks m ON s.student_id = m.student_id GROUP BY s.student_id ORDER BY max_marks DESC LIMIT 5;",
    ),
]


def build_sql_prompt(question: str, schema_context: str) -> str:
    """Construct the complete prompt for Gemini to generate SQL.

    Args:
        question: User's natural language query.
        schema_context: Formatted string describing the SQLite database schema.

    Returns:
        Formatted prompt string ready for LLM inference.
    """
    examples_formatted = []
    for q, sql in FEW_SHOT_EXAMPLES:
        examples_formatted.append(f"Question: {q}\nSQL: {sql}\n")

    examples_block = "\n".join(examples_formatted)

    prompt = f"""{schema_context}

### Few-Shot Examples:
{examples_block}
### Current Task:
User Question: "{question.strip()}"
SQL:"""
    return prompt

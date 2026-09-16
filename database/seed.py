"""Seed script to populate the College Management SQLite database with realistic sample data.

Usage:
    python -m database.seed
    or
    python database/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import get_connection, init_db, get_table_counts, get_db_path


# ----------------------------------------------------------------------
# Realistic College Sample Dataset
# ----------------------------------------------------------------------

STUDENTS_DATA = [
    # Computer Science
    ("Aarav Sharma", "Computer Science", 2, "aarav.sharma@college.edu"),
    ("Priya Patel", "Computer Science", 3, "priya.patel@college.edu"),
    ("Rohan Gupta", "Computer Science", 2, "rohan.gupta@college.edu"),
    ("Ananya Iyer", "Computer Science", 4, "ananya.iyer@college.edu"),
    ("Aditya Rao", "Computer Science", 1, "aditya.rao@college.edu"),
    ("Sneha Nair", "Computer Science", 3, "sneha.nair@college.edu"),
    # Information Technology
    ("Vikram Singh", "Information Technology", 2, "vikram.singh@college.edu"),
    ("Neha Joshi", "Information Technology", 3, "neha.joshi@college.edu"),
    ("Karan Malhotra", "Information Technology", 4, "karan.malhotra@college.edu"),
    ("Pooja Mishra", "Information Technology", 1, "pooja.mishra@college.edu"),
    ("Rahul Verma", "Information Technology", 2, "rahul.verma@college.edu"),
    # Electronics
    ("Ishaan Saxena", "Electronics", 3, "ishaan.saxena@college.edu"),
    ("Divya Krishnan", "Electronics", 2, "divya.krishnan@college.edu"),
    ("Meera Nambiar", "Electronics", 4, "meera.nambiar@college.edu"),
    ("Kunal Deshmukh", "Electronics", 1, "kunal.deshmukh@college.edu"),
    # Mechanical
    ("Arjun Reddy", "Mechanical", 3, "arjun.reddy@college.edu"),
    ("Tanvi Kulkarni", "Mechanical", 2, "tanvi.kulkarni@college.edu"),
    ("Siddharth Sen", "Mechanical", 4, "siddharth.sen@college.edu"),
    ("Ritika Roy", "Mechanical", 1, "ritika.roy@college.edu"),
    ("Varun Bhat", "Mechanical", 2, "varun.bhat@college.edu"),
]

SUBJECTS_DATA = [
    ("Data Structures", 4, "Computer Science"),
    ("Database Management Systems", 4, "Computer Science"),
    ("Operating Systems", 3, "Computer Science"),
    ("Web Technologies", 3, "Information Technology"),
    ("Computer Networks", 4, "Information Technology"),
    ("Digital Signal Processing", 4, "Electronics"),
    ("Microcontrollers", 3, "Electronics"),
    ("Thermodynamics", 4, "Mechanical"),
    ("Fluid Mechanics", 3, "Mechanical"),
]

# (student_index_0_based, subject_index_0_based, marks, semester)
MARKS_DATA = [
    # Computer Science students in CS Subjects
    # Aarav Sharma (student_id: 1)
    (0, 0, 88.5, 3),  # Data Structures
    (0, 1, 82.0, 3),  # DBMS
    (0, 2, 79.0, 4),  # Operating Systems
    # Priya Patel (student_id: 2) - High achiever
    (1, 0, 92.0, 5),  # Data Structures
    (1, 1, 89.0, 5),  # DBMS
    (1, 2, 86.0, 6),  # Operating Systems
    # Rohan Gupta (student_id: 3) - Average
    (2, 0, 68.0, 3),  # Data Structures
    (2, 1, 72.5, 3),  # DBMS
    (2, 2, 65.0, 4),  # Operating Systems
    # Ananya Iyer (student_id: 4) - Top student
    (3, 0, 95.5, 7),  # Data Structures
    (3, 1, 94.0, 7),  # DBMS
    (3, 2, 91.0, 8),  # Operating Systems
    # Aditya Rao (student_id: 5)
    (4, 0, 75.0, 1),  # Data Structures
    # Sneha Nair (student_id: 6) - Scored >80 but low attendance in DS
    (5, 0, 81.0, 5),  # Data Structures
    (5, 1, 78.5, 5),  # DBMS
    (5, 2, 83.0, 6),  # Operating Systems
    # Information Technology students
    # Vikram Singh (student_id: 7)
    (6, 0, 74.0, 3),  # Data Structures
    (6, 3, 84.0, 3),  # Web Technologies
    (6, 4, 78.0, 4),  # Computer Networks
    # Neha Joshi (student_id: 8)
    (7, 3, 88.0, 5),  # Web Technologies
    (7, 4, 85.5, 5),  # Computer Networks
    # Karan Malhotra (student_id: 9)
    (8, 3, 76.5, 7),  # Web Technologies
    (8, 4, 72.0, 7),  # Computer Networks
    # Pooja Mishra (student_id: 10)
    (9, 3, 90.0, 1),  # Web Technologies
    (9, 4, 87.0, 2),  # Computer Networks
    # Rahul Verma (student_id: 11) - Low marks & low attendance
    (10, 3, 62.0, 3),  # Web Technologies
    (10, 4, 58.0, 4),  # Computer Networks
    # Electronics students
    # Ishaan Saxena (student_id: 12)
    (11, 5, 83.0, 5),  # DSP
    (11, 6, 76.0, 6),  # Microcontrollers
    # Divya Krishnan (student_id: 13)
    (12, 5, 79.5, 3),  # DSP
    (12, 6, 82.0, 4),  # Microcontrollers
    # Meera Nambiar (student_id: 14) - High performer
    (13, 5, 86.0, 7),  # DSP
    (13, 6, 89.5, 8),  # Microcontrollers
    # Kunal Deshmukh (student_id: 15)
    (14, 5, 70.0, 1),  # DSP
    (14, 6, 68.0, 2),  # Microcontrollers
    # Mechanical students
    # Arjun Reddy (student_id: 16)
    (15, 7, 75.0, 5),  # Thermodynamics
    (15, 8, 78.0, 6),  # Fluid Mechanics
    # Tanvi Kulkarni (student_id: 17)
    (16, 7, 84.0, 3),  # Thermodynamics
    (16, 8, 81.0, 4),  # Fluid Mechanics
    # Siddharth Sen (student_id: 18)
    (17, 7, 79.0, 7),  # Thermodynamics
    (17, 8, 74.5, 8),  # Fluid Mechanics
    # Ritika Roy (student_id: 19)
    (18, 7, 71.5, 1),  # Thermodynamics
    (18, 8, 69.0, 2),  # Fluid Mechanics
    # Varun Bhat (student_id: 20) - Below 75% attendance
    (19, 7, 64.0, 3),  # Thermodynamics
    (19, 8, 61.0, 4),  # Fluid Mechanics
]

# (student_index_0_based, subject_index_0_based, attendance_percentage)
ATTENDANCE_DATA = [
    # Computer Science
    (0, 0, 84.0),  # Aarav Sharma - DS
    (0, 1, 82.5),  # Aarav Sharma - DBMS
    (0, 2, 80.0),  # Aarav Sharma - OS
    (1, 0, 94.5),  # Priya Patel - DS (marks > 80, att > 85)
    (1, 1, 91.0),  # Priya Patel - DBMS (marks > 80, att > 85)
    (1, 2, 89.5),  # Priya Patel - OS
    (2, 0, 68.5),  # Rohan Gupta - DS (below 75%)
    (2, 1, 71.0),  # Rohan Gupta - DBMS (below 75%)
    (2, 2, 73.0),  # Rohan Gupta - OS (below 75%)
    (3, 0, 96.0),  # Ananya Iyer - DS (marks > 80, att > 85)
    (3, 1, 93.5),  # Ananya Iyer - DBMS (marks > 80, att > 85)
    (3, 2, 95.0),  # Ananya Iyer - OS (marks > 80, att > 85)
    (4, 0, 86.0),  # Aditya Rao - DS
    (5, 0, 74.0),  # Sneha Nair - DS (marks: 81.0, attendance: 74% -> tests below 75% filter)
    (5, 1, 76.5),  # Sneha Nair - DBMS
    (5, 2, 77.0),  # Sneha Nair - OS
    # Information Technology
    (6, 0, 81.5),  # Vikram Singh - DS
    (6, 3, 83.0),  # Vikram Singh - Web Tech
    (6, 4, 80.0),  # Vikram Singh - Networks
    (7, 3, 89.0),  # Neha Joshi - Web Tech (marks > 80, att > 85)
    (7, 4, 87.5),  # Neha Joshi - Networks (marks > 80, att > 85)
    (8, 3, 78.0),  # Karan Malhotra - Web Tech
    (8, 4, 76.0),  # Karan Malhotra - Networks
    (9, 3, 92.0),  # Pooja Mishra - Web Tech (marks > 80, att > 85)
    (9, 4, 88.0),  # Pooja Mishra - Networks (marks > 80, att > 85)
    (10, 3, 64.0),  # Rahul Verma - Web Tech (below 75%)
    (10, 4, 70.5),  # Rahul Verma - Networks (below 75%)
    # Electronics
    (11, 5, 83.0),  # Ishaan Saxena - DSP
    (11, 6, 81.0),  # Ishaan Saxena - Microcontrollers
    (12, 5, 78.5),  # Divya Krishnan - DSP
    (12, 6, 80.0),  # Divya Krishnan - Microcontrollers
    (13, 5, 88.5),  # Meera Nambiar - DSP (marks > 80, att > 85)
    (13, 6, 91.0),  # Meera Nambiar - Microcontrollers (marks > 80, att > 85)
    (14, 5, 72.0),  # Kunal Deshmukh - DSP (below 75%)
    (14, 6, 73.5),  # Kunal Deshmukh - Microcontrollers (below 75%)
    # Mechanical
    (15, 7, 82.5),  # Arjun Reddy - Thermo
    (15, 8, 80.0),  # Arjun Reddy - Fluids
    (16, 7, 87.0),  # Tanvi Kulkarni - Thermo (marks > 80, att > 85)
    (16, 8, 85.5),  # Tanvi Kulkarni - Fluids (marks > 80, att > 85)
    (17, 7, 79.0),  # Siddharth Sen - Thermo
    (17, 8, 77.5),  # Siddharth Sen - Fluids
    (18, 7, 75.5),  # Ritika Roy - Thermo
    (18, 8, 73.0),  # Ritika Roy - Fluids (below 75%)
    (19, 7, 72.0),  # Varun Bhat - Thermo (below 75%)
    (19, 8, 69.5),  # Varun Bhat - Fluids (below 75%)
]


def seed_database(db_path: Optional[str | Path] = None) -> None:
    """Populate the database with sample college data."""
    target_path = get_db_path(db_path)
    print(f"Initializing database schema at: {target_path}")
    init_db(target_path)

    with get_connection(target_path) as conn:
        cursor = conn.cursor()

        # Insert Students
        print(f"Inserting {len(STUDENTS_DATA)} students...")
        cursor.executemany(
            """
            INSERT INTO students (name, department, year, email)
            VALUES (?, ?, ?, ?);
            """,
            STUDENTS_DATA,
        )

        # Insert Subjects
        print(f"Inserting {len(SUBJECTS_DATA)} subjects...")
        cursor.executemany(
            """
            INSERT INTO subjects (subject_name, credits, department)
            VALUES (?, ?, ?);
            """,
            SUBJECTS_DATA,
        )

        # Retrieve mapped IDs for students and subjects to ensure exact FK associations
        cursor.execute("SELECT student_id, name FROM students ORDER BY student_id;")
        student_rows = cursor.fetchall()
        student_id_map = [row["student_id"] for row in student_rows]

        cursor.execute("SELECT subject_id, subject_name FROM subjects ORDER BY subject_id;")
        subject_rows = cursor.fetchall()
        subject_id_map = [row["subject_id"] for row in subject_rows]

        # Insert Marks
        print(f"Inserting {len(MARKS_DATA)} marks records...")
        marks_to_insert = [
            (
                student_id_map[s_idx],
                subject_id_map[sub_idx],
                marks,
                semester,
            )
            for s_idx, sub_idx, marks, semester in MARKS_DATA
        ]
        cursor.executemany(
            """
            INSERT INTO marks (student_id, subject_id, marks, semester)
            VALUES (?, ?, ?, ?);
            """,
            marks_to_insert,
        )

        # Insert Attendance
        print(f"Inserting {len(ATTENDANCE_DATA)} attendance records...")
        attendance_to_insert = [
            (
                student_id_map[s_idx],
                subject_id_map[sub_idx],
                pct,
            )
            for s_idx, sub_idx, pct in ATTENDANCE_DATA
        ]
        cursor.executemany(
            """
            INSERT INTO attendance (student_id, subject_id, attendance_percentage)
            VALUES (?, ?, ?);
            """,
            attendance_to_insert,
        )

        conn.commit()

    # Verify counts
    counts = get_table_counts(target_path)
    print("\nDatabase seeded successfully! Row counts:")
    for table, count in counts.items():
        print(f"  - {table}: {count} rows")


if __name__ == "__main__":
    seed_database()

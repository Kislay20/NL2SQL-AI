-- =====================================================================
-- College Management Database Schema (SQLite)
-- Project: NL2SQL AI
-- =====================================================================

-- Enforce foreign key constraints
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Table: STUDENTS
-- Stores student profile information.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS marks;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    year INTEGER NOT NULL CHECK (year BETWEEN 1 AND 4),
    email TEXT NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- Table: SUBJECTS
-- Stores academic subjects offered across different departments.
-- ---------------------------------------------------------------------
CREATE TABLE subjects (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT NOT NULL UNIQUE,
    credits INTEGER NOT NULL CHECK (credits > 0),
    department TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Table: MARKS
-- Stores semester assessment marks obtained by students in subjects.
-- ---------------------------------------------------------------------
CREATE TABLE marks (
    mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    marks REAL NOT NULL CHECK (marks >= 0.0 AND marks <= 100.0),
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    UNIQUE(student_id, subject_id, semester)
);

-- ---------------------------------------------------------------------
-- Table: ATTENDANCE
-- Tracks cumulative attendance percentage for a student in a subject.
-- ---------------------------------------------------------------------
CREATE TABLE attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    attendance_percentage REAL NOT NULL CHECK (attendance_percentage >= 0.0 AND attendance_percentage <= 100.0),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    UNIQUE(student_id, subject_id)
);

-- ---------------------------------------------------------------------
-- Indexes for performance and query optimization
-- ---------------------------------------------------------------------
CREATE INDEX idx_students_dept ON students(department);
CREATE INDEX idx_marks_student ON marks(student_id);
CREATE INDEX idx_marks_subject ON marks(subject_id);
CREATE INDEX idx_attendance_student ON attendance(student_id);
CREATE INDEX idx_attendance_subject ON attendance(subject_id);

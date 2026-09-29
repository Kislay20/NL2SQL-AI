import sqlite3
import os

DB_NAME = "college.db"

def init_db():
    # Check karega ki kya database file exist karti hai ya nahi
    db_exists = os.path.exists(DB_NAME)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Agar tables pehle se nahi hain, toh ye unhe automatic bana dega
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            age INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            department TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marks (
            mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject_id INTEGER,
            marks INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(student_id),
            FOREIGN KEY(subject_id) REFERENCES subjects(subject_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            attendance_percentage REAL,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')
    
    # Agar database naya bana hai, toh thoda sample data daal do taaki testing fail na ho
    if not db_exists or cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        cursor.executemany("INSERT INTO students (name, department, age) VALUES (?, ?, ?)", [
            ('Rahul Sharma', 'Computer Science', 21),
            ('Priya Verma', 'Computer Science', 22),
            ('Amit Singh', 'Electronics', 20),
            ('Sneha Roy', 'Computer Science', 21)
        ])
        
        cursor.executemany("INSERT INTO subjects (subject_name, department) VALUES (?, ?)", [
            ('Data Structures', 'Computer Science'),
            ('Algorithms', 'Computer Science'),
            ('Digital Logic', 'Electronics')
        ])
        
        cursor.executemany("INSERT INTO marks (student_id, subject_id, marks) VALUES (?, ?, ?)", [
            (1, 1, 85),
            (2, 1, 90),
            (3, 3, 75),
            (4, 2, 88)
        ])
        
        cursor.executemany("INSERT INTO attendance (student_id, attendance_percentage) VALUES (?, ?)", [
            (1, 92.5),
            (2, 88.0),
            (3, 79.5),
            (4, 95.0)
        ])
        
        conn.commit()
    
    conn.close()
    print("Database & Tables initialized successfully!")
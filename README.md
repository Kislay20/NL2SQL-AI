# NL2SQL AI: Natural Language to SQL Generator with Explanation

> **Tagline:** *Ask in Natural Language. Generate SQL. Understand the Query. Get the Result.*

An AI-powered Generative SQL Assistant built for college relational database querying, query safety verification, plain-English explanations, and dynamic visualization. Developed with **Google Gemini API**, **Python**, **Streamlit**, and **SQLite**.

---

## 📋 Table of Contents
1. [Project Overview](#-project-overview)
2. [Core Architecture](#-core-architecture)
3. [Key Features](#-key-features)
4. [Database Schema](#-database-schema)
5. [Installation & Setup](#-installation--setup)
6. [Running the Application](#-running-the-application)
7. [Running Tests & Benchmarks](#-running-tests--benchmarks)
8. [Project Structure](#-project-structure)
9. [Viva Voce: Top 10 Examiner Q&A](#-viva-voce-top-10-examiner-qa)

---

## 🌟 Project Overview
Querying relational databases typically requires proficiency in SQL syntax, table joins, aggregation functions, and relational schema structures. **NL2SQL AI** bridges this gap by allowing non-technical users to ask questions in everyday conversational English and receive:
1. **Accurate SQLite Queries** synthesized by Google Gemini.
2. **Deterministic Safety Validation** blocking destructive SQL and hallucinations.
3. **Execution Results** in interactive Pandas tables.
4. **Intuitive Visualizations** powered by Plotly Express.
5. **Plain-English Explanations** helping beginners understand the query logic.

---

## 🏗️ Core Architecture
```
                         User Natural Language Question
                                       │
                                       ▼
                              Streamlit Web UI
                                       │
                                       ▼
                       Dynamic Schema Introspection
                     (database/database.py catalog)
                                       │
                                       ▼
                         Google Gemini LLM Inference
                         (ai/prompts.py + ai/gemini.py)
                                       │
                                       ▼
                          Generated SQL Query
                                       │
                                       ▼
                  ┌───────────────────────────────────────────┐
                  │      DEFENSE-IN-DEPTH SAFETY PIPELINE     │
                  ├───────────────────────────────────────────┤
                  │ 1. Safety Gate (sql/safety.py):           │
                  │    - Single-statement constraint          │
                  │    - Token AST scan for blocked keywords  │
                  │      (DROP, DELETE, INSERT, UPDATE, etc.) │
                  │ 2. Schema Validator (sql/validator.py):   │
                  │    - SQLite EXPLAIN QUERY PLAN simulation │
                  │    - Catches hallucinated tables/columns  │
                  └─────────────────────┬─────────────────────┘
                                        │ Safe & Valid
                                        ▼
                                 SQLite Database
                                 (data/college.db)
                                        │
                                        ▼
                           Pandas DataFrame Extraction
                                        │
                   ┌────────────────────┴────────────────────┐
                   ▼                                         ▼
         Tabular & Visual Display                  AI Plain-English
        - st.dataframe (interactive)                 Explanation
        - Plotly Express (Bar / Scatter)          (ai/explainer.py)
```

---

## 🚀 Key Features

- **Schema-Aware Few-Shot Prompting**: Dynamically injects live DDL catalog metadata into Gemini prompts, ensuring zero hallucination of non-existent tables or attributes.
- **Two-Step Safety Pipeline**:
  - **AST Token Inspection (`sqlparse`)**: Blocks multiple statements, non-SELECT types, and dangerous DDL/DML keywords (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `GRANT`, `PRAGMA`).
  - **Zero-Execution Query Plan Compilation (`EXPLAIN QUERY PLAN`)**: Catches invalid columns or syntax errors before runtime.
- **Dynamic Plotly Charting**: Detects 2-column aggregates (e.g. *Department vs Average Marks*) and renders interactive bar charts with auto-formatting without forcing meaningless charts on general student rosters.
- **Beginner-Friendly AI Explainer**: Translates SQL joins, group-bys, and filters into 2-3 non-technical English sentences.
- **Interactive Schema Explorer**: Expandable table schema viewer with primary key tags (🔑) and live 3-row data previews.
- **Session Query History**: Preserves chat turns, SQL statements, tables, and AI explanations with a one-click history purge.

---

## 🗄️ Database Schema
The database models a **College Management System** stored in SQLite (`data/college.db`):

```
┌───────────────────────────────────────┐
│               STUDENTS                │
├───────────────────────────────────────┤
│ PK  student_id  INTEGER AUTOINCREMENT │
│     name        TEXT NOT NULL         │
│     department  TEXT NOT NULL         │
│     year        INTEGER (1-4)         │
│     email       TEXT UNIQUE NOT NULL  │
└──────────────────┬────────────────────┘
                   │ 1
                   │ *
         ┌─────────┴─────────┐
         ▼                   ▼
┌──────────────────┐  ┌───────────────────────────┐
│      MARKS       │  │        ATTENDANCE         │
├──────────────────┤  ├───────────────────────────┤
│ PK mark_id       │  │ PK attendance_id          │
│ FK student_id    │  │ FK student_id             │
│ FK subject_id    │  │ FK subject_id             │
│    marks (0-100) │  │    attendance_pct (0-100) │
│    semester(1-8) │  │    UNIQUE(student,subject)│
└────────┬─────────┘  └──────────────┬────────────┘
         ▲                           ▲
         │ *                         │ *
         └─────────┬─────────────────┘
                   │ 1
┌──────────────────┴────────────────────┐
│               SUBJECTS                │
├───────────────────────────────────────┤
│ PK  subject_id  INTEGER AUTOINCREMENT │
│     subject_name TEXT UNIQUE NOT NULL │
│     credits      INTEGER (> 0)        │
│     department   TEXT NOT NULL        │
└───────────────────────────────────────┘
```

---

## 💻 Installation & Setup

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Git

### 2. Clone & Install Dependencies
```bash
git clone <repository_url>
cd NL2SQL-AI

# Create virtual environment (optional)
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate # macOS/Linux

# Install required packages
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=AIzaSy...your_real_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_PATH=data/college.db
```

### 4. Seed Database
Generate and populate `data/college.db` with 20 students, 9 subjects, 45 marks records, and 45 attendance records:
```bash
python -m database.seed
```

---

## 🖥️ Running the Application

Launch the Streamlit interactive web interface:
```bash
python -m streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Tests & Benchmarks

### Automated Pytest Suite (75 Tests)
```bash
python -m pytest -v tests/
```

### 18-Query Viva Benchmark Suite
Demonstrates all edge cases, aggregations, joins, safety blocks, and hallucination handling without manual typing:
```bash
python tests/benchmark_queries.py
```

---

## 📁 Project Structure
```
NL2SQL-AI/
├── app.py                      # Streamlit application entry point
├── requirements.txt            # Project dependencies manifest
├── .env.example                # Environment configuration template
├── .gitignore                  # Git protection rules
├── README.md                   # Comprehensive project documentation & Viva Q&A
├── DEMO_SCRIPT.md              # 5-Minute presentation and live demo script
│
├── ai/                         # Gemini integration & prompt engineering
│   ├── __init__.py
│   ├── gemini.py               # Google GenAI client & exponential retry engine
│   ├── prompts.py              # Few-shot SQL & explanation prompt builders
│   ├── sql_generator.py        # Natural Language -> SQL generation logic
│   ├── explainer.py            # Plain-English query explainer
│   └── parser.py               # Markdown fence & code extraction sanitizer
│
├── database/                   # Relational database layer
│   ├── __init__.py
│   ├── schema.sql              # College DDL schema with foreign keys
│   ├── seed.py                 # Realistic collegiate sample data generator
│   └── database.py             # SQLite connection manager & schema introspection
│
├── sql/                        # SQL safety and execution
│   ├── __init__.py
│   ├── safety.py               # AST token scanner & keyword blocklist
│   ├── validator.py            # SQLite EXPLAIN QUERY PLAN syntax validator
│   └── executor.py             # Read-only execution into Pandas DataFrames
│
├── ui/                         # User Interface components
│   ├── __init__.py
│   ├── components.py           # Sidebar schema explorer & sample question chips
│   └── charts.py               # Plotly Express auto-charting engine
│
├── utils/                      # Session & History
│   ├── __init__.py
│   └── history.py              # Session state history management
│
├── tests/                      # Verification test suite
│   ├── __init__.py
│   ├── test_ai.py              # Gemini, prompt, parser, and generator tests
│   ├── test_database.py        # Schema, constraints, and analytical query tests
│   ├── test_sql.py             # Safety gate & hallucination catching tests
│   ├── test_executor.py        # Pandas conversion & database execution tests
│   ├── test_ui.py              # Auto-chart heuristics & session history tests
│   └── benchmark_queries.py    # 18-query benchmark test harness for viva
│
└── data/                       # Database storage
    ├── .gitkeep
    └── college.db              # Populated SQLite database (reproducible via seed)
```

---

## 🎓 Viva Voce: Top 10 Examiner Q&A

### Q1: How does the Natural Language to SQL translation work?
**Answer:** The translation pipeline operates in four coordinated steps:
1. **Catalog Introspection**: When a question is submitted, `database/database.py` extracts the live DDL schema, column types, and foreign key relations.
2. **Context Formulation**: `ai/prompts.py` merges the dynamic schema with system instructions and 8 curated few-shot examples illustrating complex joins and aggregations.
3. **LLM Inference**: The prompt is submitted to Google Gemini (`gemini-2.5-flash`) with sampling temperature set to `0.0` for deterministic SQL output.
4. **Sanitization**: `ai/parser.py` strips markdown fences (```` ```sql ````), cleans conversational prefixes, and normalizes semicolons.

### Q2: How do you prevent SQL Injection and destructive operations?
**Answer:** We implement a **defense-in-depth, two-stage validation pipeline** before queries ever reach the database:
- **Stage 1 (AST Safety Gate in `sql/safety.py`)**: Uses `sqlparse` to tokenize the query. It verifies that only one single statement exists (blocking multi-statement injection like `SELECT ...; DROP TABLE ...;`), enforces that `stmt.get_type() == 'SELECT'`, and scans AST tokens against a blocklist (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE`, `PRAGMA`, `ATTACH`). Keywords appearing inside string literals (e.g. `WHERE name = 'drop'`) are permitted.
- **Stage 2 (Schema Validator in `sql/validator.py`)**: Runs `EXPLAIN QUERY PLAN <query>` against SQLite. This checks syntax and validates table/column existence without running the query.

### Q3: Why did you choose SQLite over MySQL or PostgreSQL?
**Answer:** For an academic Generative AI prototype and MCA project defense:
1. **Portability & Zero-Config**: SQLite is serverless and self-contained in a single file (`college.db`), enabling anyone to clone and run the project immediately without configuring database servers or user credentials.
2. **ACID Compliance**: Supports foreign key constraints (`PRAGMA foreign_keys = ON;`), relational integrity, and standard SQL-92 dialect.
3. **Native Python Standard Library**: Integrated directly via Python's built-in `sqlite3` module, reducing external network dependencies.

### Q4: How does dynamic schema injection prevent hallucinations?
**Answer:** LLMs hallucinate when asked to query databases in a vacuum because they guess common column names (e.g., guessing `gpa` or `salary` in a student table). In `ai/prompts.py`, we inject the exact schema output from `get_schema_prompt_context()` alongside explicit constraints: *"Use ONLY tables and columns present in the schema. Do not invent columns."* Furthermore, if an LLM hallucination slips through, Stage 2 of our validation pipeline (`EXPLAIN QUERY PLAN`) catches `no such column` or `no such table` before runtime.

### Q5: How does the explanation engine generate plain-English explanations?
**Answer:** `ai/explainer.py` uses a dedicated prompt template instructing Gemini to adopt the persona of a friendly data analyst. It supplies both the user's natural language question and the generated SQL, with strict instructions:
1. Limit output to 2–3 concise sentences.
2. Avoid mechanical keyword descriptions (e.g., avoiding *"SELECT fetches columns and WHERE filters"*).
3. Explain the business/academic outcome (e.g., *"This query combines student profiles with exam marks to rank the top 5 performers"*).
4. If an API failure occurs, a graceful fallback string is returned without crashing the UI.

### Q6: How does the application decide when to render a Plotly chart?
**Answer:** In `ui/charts.py`, `generate_auto_chart()` applies automated structural heuristics to the resulting Pandas DataFrame:
- **2 Columns (1 Categorical, 1 Numeric)**: Automatically constructs an interactive Plotly Bar Chart with rounded value labels (e.g., *Average Marks by Department*).
- **2 Columns (Both Numeric)**: Constructs a Scatter Plot with an OLS regression trendline (e.g., *Marks vs Attendance Percentage*).
- **3 Columns (2 Categorical, 1 Numeric)**: Constructs a grouped Bar Chart.
- **General Tables (4+ Columns)**: Returns `None` so that general tabular records (like full student directories) are not forced into unreadable charts.

### Q7: How do you handle Gemini API rate limits and connection failures?
**Answer:**
1. **Exponential Backoff**: `ai/gemini.py` intercepts HTTP 429 (`RESOURCE_EXHAUSTED`) and HTTP 503 (server demand spikes) and retries up to 3 times with progressive sleep intervals (`2s`, `4s`).
2. **Graceful UI Fallbacks**: If the rate limit persists, the explanation engine returns a friendly fallback message (*"Explanation unavailable at the moment."*), allowing the user to view the SQL and data table without encountering an unhandled crash.
3. **Deterministic Pytest Suite**: In `tests/test_ai.py`, live API tests gracefully skip if quota is saturated while all 20+ mocked unit tests pass 100% offline.

### Q8: What is the difference between this approach and a RAG system?
**Answer:**
- **RAG (Retrieval-Augmented Generation)** is typically used for unstructured text documents (e.g. PDFs, manuals) by chunking text, generating vector embeddings, storing them in vector databases (like FAISS/Chroma), and performing cosine similarity search.
- **Text-to-SQL (our approach)** targets *structured relational data*. Instead of vector similarity, it uses **Schema Introspection + In-Context Few-Shot Prompting** to translate natural language into deterministic relational algebra. This provides exact numerical answers (e.g. true mathematical averages and counts) rather than probabilistic text approximations.

### Q9: What are the current limitations of this architecture?
**Answer:**
1. **Read-Only Scope**: The system deliberately disallows `INSERT`, `UPDATE`, and `DELETE` queries for security reasons.
2. **Schema Size Limit**: For enterprise databases with hundreds of tables, injecting the entire schema into the context window would exceed token limits.
3. **Ambiguous Questions**: Questions lacking clear metrics (e.g., *"Who is the best student?"*) require the model to assume criteria (such as highest marks or best attendance).

### Q10: How would you scale this project to an enterprise production environment?
**Answer:**
1. **Schema Retrieval (RAG for Schemas)**: Use vector embeddings to retrieve only the top 3-5 relevant table schemas based on the user question instead of injecting all tables.
2. **Database Connectors**: Replace SQLite with SQLAlchemy connection pools connecting to PostgreSQL, MySQL, or Snowflake with read-only database roles.
3. **Caching Layer**: Implement Redis to cache SQL queries and results for identical user prompts, bypassing LLM inference costs and latency.
4. **Fine-Tuned LLM**: Fine-tune a specialized open-weights model (e.g. CodeLlama or DeepSeek-Coder) for organization-specific SQL dialects.

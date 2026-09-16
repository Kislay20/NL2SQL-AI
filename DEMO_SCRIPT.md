# NL2SQL AI: 5-Minute MCA Viva Presentation & Demo Script

> **Project Name:** Natural Language to SQL Generator with Explanation  
> **Target Audience:** MCA External Examiner & Project Evaluation Committee  
> **Duration:** 5 Minutes (Presentation + Live Demonstration)

---

## ⏱️ Presentation Timeline Overview
- **0:00 – 0:45 (Slide 1):** Introduction, Title, & Objectives
- **0:45 – 1:30 (Slide 2):** Problem Statement & Core Architecture
- **1:30 – 2:30 (Slide 3):** Two-Stage Safety & Validation Layer (Viva Highlight)
- **2:30 – 4:00 (Live Demo):** 4 Live Queries in Streamlit (Joins, Charts, Blocks)
- **4:00 – 5:00 (Slide 4):** Results, Viva Defense Points & Conclusion

---

## Slide 1: Project Title & Introduction (0:00 – 0:45)
**Slide Visuals:**
- Title: **NL2SQL AI: Natural Language to SQL Generator with Explanation**
- Tagline: *"Ask in Natural Language. Generate SQL. Understand the Query. Get the Result."*
- Student Name, Roll Number, MCA Semester IV, Department of Computer Applications.
- Tech Stack Badges: Google Gemini API | Python | SQLite | Streamlit | Plotly | Pandas.

**Speaker Script:**
> *"Respected Examiners and Faculty Members, good morning. Today, I am presenting my MCA Generative AI semester project titled **Natural Language to SQL Generator with Explanation**, or **NL2SQL AI**.*
>
> *In modern organizations, data is stored in relational databases. However, accessing this data requires knowing SQL syntax, joins, and table schemas, creating a barrier for non-technical stakeholders. My project bridges this gap using Google Gemini to convert natural language questions into deterministic, read-only SQLite queries, paired with an automated safety pipeline, dynamic visualizations, and plain-English AI explanations."*

---

## Slide 2: Problem Statement & Core Architecture (0:45 – 1:30)
**Slide Visuals:**
- Diagram showing:
  `User Question → Schema Introspection → Gemini LLM → Two-Step Safety Gate → SQLite DB → Pandas Table + Plotly Chart + Plain-English Explanation`.
- Comparison table: Traditional Querying vs Generative AI Assisted Querying.

**Speaker Script:**
> *"The core problem we solved is twofold: **accessibility** and **safety**. Many naive AI-SQL generators simply take user text and execute whatever the model outputs. In a real-world setting, this is disastrous because LLMs can hallucinate non-existent columns or be tricked into executing destructive statements like `DROP TABLE`.*
>
> *In our architecture, the user's natural language question is combined with a dynamic database schema extracted directly from SQLite's catalog. Gemini generates a candidate query. Before that query ever touches the database, it passes through our custom defense-in-depth safety engine. Only after passing both AST token analysis and SQLite query plan simulation is it executed, visualized with Plotly, and explained in non-technical English."*

---

## Slide 3: Two-Stage Safety & Validation Engine (1:30 – 2:30)
**Slide Visuals:**
- **Stage 1 (AST Safety Gate - `sql/safety.py`):** Single statement check, `sqlparse` token flattening, keyword blocklist (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `PRAGMA`, `ATTACH`).
- **Stage 2 (Schema Validator - `sql/validator.py`):** SQLite `EXPLAIN QUERY PLAN` verification. Zero execution simulation that catches hallucinated tables/columns.
- Visual flow of blocked injection attempts.

**Speaker Script:**
> *"This safety layer is the primary technical highlight of my project. We do NOT rely on string matching because string matching can be fooled or cause false positives.*
>
> *Instead, Stage 1 uses abstract syntax tree tokenization through `sqlparse`. It guarantees exactly one query statement is present, blocking multi-statement injection like `SELECT; DROP TABLE;`. It also verifies the query type is strictly `SELECT` and scans tokens against a blocked keyword set while intelligently allowing keywords inside string literals.*
>
> *Stage 2 compiles the query using SQLite's `EXPLAIN QUERY PLAN`. This simulates query execution against the actual database catalog without reading or mutating rows. If Gemini hallucinates a column like `salary` that doesn't exist, SQLite catches it immediately, and the app rejects the query gracefully."*

---

## Slide 4: Live Demonstration Walkthrough (2:30 – 4:00)
**Action:** Switch window to the live Streamlit app running at `http://localhost:8501`.

### Demo Step 1: Aggregation & Dynamic Chart
- **Click or Type:** *"Which department has the highest average marks?"*
- **Explain to Examiner:**
  > *"Notice how the system generates a SQL query with `ROUND(AVG(marks), 2)` grouped by department with `ORDER BY avg_marks DESC LIMIT 1`. Because the result is a clean categorical-numeric pair, our chart engine automatically produces an interactive Plotly bar chart, alongside an easy-to-read explanation for a non-technical manager."*

### Demo Step 2: Multi-Table Join & Compound Filter
- **Click or Type:** *"Find students who scored above 80 and have attendance above 85%."*
- **Explain to Examiner:**
  > *"Here, the AI automatically identifies that student names are in `students`, scores are in `marks`, and attendance is in `attendance`. It joins all three tables across `student_id` and `subject_id`, returning the exact matching records."*

### Demo Step 3: Security & Injection Block Test
- **Click or Type:** *"DROP TABLE students;"* or *"SELECT * FROM students; DROP TABLE attendance;"*
- **Explain to Examiner:**
  > *"Now watch what happens if a malicious prompt or injection is attempted. The Safety Gate catches the `DROP` token and blocks execution before database access, outputting a clear safety alert without crashing."*

### Demo Step 4: Schema Hallucination Catch
- **Click or Type:** *"Show student salary and annual bonuses."*
- **Explain to Examiner:**
  > *"When a user asks for attributes not in our college schema, the Schema Gate catches `no such column: salary` during plan compilation, preventing invalid executions."*

---

## Slide 5: Results, Viva Defense & Conclusion (4:00 – 5:00)
**Slide Visuals:**
- Test Suite Summary: **75 Unit & Integration Tests Passing (100% test pass rate)**.
- 18 Benchmark queries verified across 8 distinct categories.
- Scalability roadmap: RAG for schemas, PostgreSQL connectors, Redis query caching.

**Speaker Script:**
> *"To ensure academic and engineering rigor, we implemented an automated test suite comprising 75 unit and integration tests across database constraints, AST safety, SQL parsing, Pandas extraction, and UI heuristics, all passing cleanly.*
>
> *In conclusion, NL2SQL AI transforms relational database access into an intuitive, safe, and transparent conversational experience. Thank you, and I am now ready to take your questions."*

---

## 🎯 Viva Voce Quick Defense Tips for the Student

| If the Examiner Asks... | Deliver this Key Insight: |
| :--- | :--- |
| **"Can users hack or drop your database through prompt injection?"** | *"No, because queries are never executed blindly. Our `sql/safety.py` AST scanner strips and inspects tokens using `sqlparse`, blocking any query that isn't strictly a single `SELECT` statement."* |
| **"How is this different from ChatGPT?"** | *"ChatGPT generates text in a vacuum without knowing the database schema or current data state. Our system dynamically inspects the SQLite catalog, injects schema context into Gemini, verifies syntax with `EXPLAIN QUERY PLAN`, and runs the query against real data."* |
| **"Why do you use Pandas?"** | *"Pandas (`pd.read_sql_query`) allows direct conversion of SQLite cursor results into structured DataFrames, which natively integrates with Streamlit tables and Plotly Express charting engines."* |
| **"What happens when Gemini hits a rate limit?"** | *"Our `ai/gemini.py` module implements exponential backoff retry logic. For the explanation engine, it returns a graceful fallback string so the user still sees their data table without the app crashing."* |

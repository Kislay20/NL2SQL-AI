# NL2SQL AI: Natural Language to SQL Generator with Explanation

> **Tagline:** Ask in Natural Language. Generate SQL. Understand the Query. Get the Result.

An AI-powered Generative SQL assistant built for college relational database querying. Powered by **Google Gemini API**, **Streamlit**, and **SQLite**.

---

## 🌟 Project Overview
NL2SQL AI allows users to interact with a relational database (College Management System) using natural everyday language. The application automatically generates valid SQLite queries, applies strict safety filters to prevent destructive operations, executes the query safely, provides clear natural language explanations of the query logic, and generates data visualizations using Plotly.

## 🏗️ Architecture
```
User
  ↓
Streamlit UI
  ↓
Natural Language Question
  ↓
Database Schema + Question Prompt
  ↓
Gemini LLM (SQL Generation)
  ↓
SQL Validation & Safety Layer (Blocks mutations, checks schema)
  ↓
SQLite Database (Read-only Execution)
  ↓
Query Results + AI Explanation + Dynamic Visualizations (Plotly)
```

## 📁 Recommended Project Structure
```
NL2SQL-AI/
├── app.py                  # Main Streamlit application entry point
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignored patterns
├── README.md               # Project documentation
│
├── ai/                     # Gemini integration & prompt engineering
│   ├── __init__.py
│   ├── gemini.py           # Gemini client configuration & initialization
│   ├── prompts.py          # Few-shot / system prompts for SQL & explanation
│   ├── sql_generator.py    # Natural language to SQL generation logic
│   ├── explainer.py        # SQL query explanation generator
│   └── parser.py           # Markdown/raw text response cleaner & parser
│
├── database/               # SQLite database layer
│   ├── __init__.py
│   ├── database.py         # SQLite connection manager & introspection
│   ├── schema.sql          # DDL schema (students, subjects, marks, attendance)
│   └── seed.py             # Realistic college sample data generator
│
├── sql/                    # SQL safety and execution
│   ├── __init__.py
│   ├── safety.py           # Mutation blocking (DROP, DELETE, INSERT, etc.)
│   ├── validator.py        # Syntax & schema validation (sqlparse)
│   └── executor.py         # Safe read-only execution & pandas conversion
│
├── ui/                     # Presentation layer
│   ├── __init__.py
│   ├── components.py       # Modular Streamlit UI cards, badges & sidebars
│   └── charts.py           # Plotly chart generators (bar, pie, histogram)
│
├── utils/                  # Utilities & state
│   ├── __init__.py
│   └── history.py          # Query history logger & session state manager
│
├── tests/                  # Automated unit test suite
│   ├── __init__.py
│   ├── test_ai.py          # AI prompt/generation tests
│   ├── test_database.py    # Database schema & query tests
│   └── test_sql.py         # SQL validation & safety tests
│
└── data/                   # Database storage
    ├── .gitkeep
    └── college.db          # Generated SQLite database file
```

---

## 🚀 Setup & Installation (Phase 1)
1. Clone the repository and navigate to the project directory:
   ```bash
   cd NL2SQL-AI
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment:
   ```bash
   cp .env.example .env
   ```
   Add your `GEMINI_API_KEY` in `.env`.

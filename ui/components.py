"""UI components and sidebar schema renderer for NL2SQL AI Streamlit application.

Provides modular sidebar controls, table schema explorer, and sample question prompts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import streamlit as st

from database.database import (
    get_table_names,
    get_table_info,
    get_table_counts,
    get_sample_data,
)
from utils.history import clear_history

SAMPLE_QUESTIONS = [
    "Show all students.",
    "Show students who scored more than 80 marks.",
    "Which department has the highest average marks?",
    "Show students whose attendance is below 75%.",
    "Show students and their marks in Data Structures.",
    "How many students are there in each department?",
    "Show the top 5 students based on highest marks.",
    "Find students who scored above 80 and have attendance above 85%.",
]


def render_sidebar(db_path: Optional[str | Path] = None) -> Optional[str]:
    """Render the sidebar with project metadata, schema explorer, and sample queries.

    Returns:
        Optional[str]: Question selected from sample buttons if clicked, else None.
    """
    selected_sample: Optional[str] = None

    with st.sidebar:
        st.title("🎓 NL2SQL AI")
        st.caption("College Database AI Assistant")
        st.markdown("---")

        # 1. System Status
        st.subheader("⚙️ System Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Engine", value="SQLite 3")
        with col2:
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            st.metric(label="LLM", value=model_name.split("-")[1].upper())

        st.markdown("---")

        # 2. Database Schema Explorer
        st.subheader("📁 Database Schema")
        try:
            tables = get_table_names(db_path)
            counts = get_table_counts(db_path)

            for tbl in tables:
                row_count = counts.get(tbl, 0)
                with st.expander(f"**{tbl.upper()}** ({row_count} rows)"):
                    cols = get_table_info(tbl, db_path)
                    col_data = []
                    for c in cols:
                        col_data.append({
                            "Column": c["name"],
                            "Type": c["type"],
                            "PK": "🔑" if c["pk"] else "",
                        })
                    st.dataframe(col_data, hide_index=True, width="stretch")

                    # Preview sample data
                    if st.checkbox(f"Preview {tbl}", key=f"prev_{tbl}"):
                        sample_df = get_sample_data(tbl, limit=3, db_path=db_path)
                        st.dataframe(sample_df, hide_index=True, width="stretch")

        except Exception as exc:
            st.error(f"Failed to inspect database schema: {exc}")

        st.markdown("---")

        # 3. Example Questions
        st.subheader("💡 Sample Questions")
        st.caption("Click to load a question:")
        for q in SAMPLE_QUESTIONS:
            if st.button(q, key=f"btn_{q}", use_container_width=True):
                selected_sample = q

        st.markdown("---")

        # 4. History Controls
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            clear_history()
            st.rerun()

    return selected_sample


def render_sidebar_schema(db_path: Optional[str | Path] = None) -> None:
    """Convenience alias to render sidebar schema explorer."""
    render_sidebar(db_path)

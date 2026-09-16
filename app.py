"""NL2SQL AI - Main Streamlit Application Entry Point.

Tagline: Ask in Natural Language. Generate SQL. Understand the Query. Get the Result.
Architecture: Natural Language Question -> Gemini LLM -> SQL Safety & Validation ->
              SQLite Execution -> Interactive Table & Plotly Chart -> AI Explanation.
"""

from __future__ import annotations

import streamlit as st

from ai.explainer import explain_sql
from ai.sql_generator import generate_sql
from sql.executor import execute_safe_query
from ui.charts import generate_auto_chart
from ui.components import render_sidebar
from utils.history import add_message, get_history, init_history


# ----------------------------------------------------------------------
# Helper: Efficient Data Export Caching
# ----------------------------------------------------------------------
@st.cache_data
def convert_df_to_csv(df):
    """Convert pandas DataFrame to UTF-8 encoded CSV bytes for download."""
    return df.to_csv(index=False).encode("utf-8")


# ----------------------------------------------------------------------
# Page Configuration & Aesthetics
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="NL2SQL AI - Natural Language to SQL Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
init_history()

# Database Connection Configuration
with st.sidebar.expander("⚙️ Database Connection", expanded=False):
    db_uri = st.text_input("Database URI", value="sqlite:///college.db")

# Render Sidebar (Schema explorer, system status, and sample buttons)
clicked_sample = render_sidebar(db_uri=db_uri)

# Main Header Banner
st.title("🎓 NL2SQL AI")
st.markdown(
    "**Natural Language to SQL Generator with Explanation**  \n"
    "*Ask in Natural Language. Generate SQL. Understand the Query. Get the Result.*"
)
st.markdown("---")

# Render Existing Chat History
history = get_history()
for idx, msg in enumerate(history):
    role = msg["role"]
    content = msg["content"]

    with st.chat_message(role):
        if role == "user":
            st.markdown(content["text"])
        elif role == "assistant":
            if content.get("error"):
                st.error(f"❌ **Error:** {content['error']}")
                if content.get("sql"):
                    with st.expander("🔍 View Attempted SQL"):
                        st.code(content["sql"], language="sql")
            else:
                # 1. Generated SQL Query
                st.markdown("##### ⚡ Generated SQL Query")
                st.code(content["sql"], language="sql")

                # 2. Database Execution Results
                df = content.get("dataframe")
                if df is not None:
                    st.markdown(f"##### 📋 Query Results ({len(df)} rows)")
                    if df.empty:
                        st.info("Query executed successfully, but returned 0 matching records.")
                    else:
                        st.dataframe(df, width="stretch", hide_index=True)
                        csv_data = convert_df_to_csv(df)
                        st.download_button(
                            label="📥 Download Results as CSV",
                            data=csv_data,
                            file_name="nl2sql_query_results.csv",
                            mime="text/csv",
                            key=f"dl_hist_{idx}",
                        )

                    # 3. Dynamic Visualization (Plotly)
                    chart_fig = content.get("chart")
                    if chart_fig:
                        st.plotly_chart(chart_fig, use_container_width=True)

                # 4. AI Explanation
                explanation = content.get("explanation")
                if explanation:
                    st.markdown("##### 💡 AI Explanation")
                    st.info(explanation)


# Capture User Input from chat input box or sample question button
user_query = st.chat_input("Ask a question about the college database (e.g. 'Show students scoring > 80')...")
active_prompt = clicked_sample if clicked_sample else user_query

if active_prompt:
    # 1. Display and record user question
    with st.chat_message("user"):
        st.markdown(active_prompt)
    add_message("user", {"text": active_prompt})

    # 2. Process query in Assistant flow
    with st.chat_message("assistant"):
        sql_query: str = ""
        try:
            # Step A: Natural Language -> SQL Generation
            with st.spinner("🤖 Gemini is generating SQLite query..."):
                sql_query = generate_sql(active_prompt)

            st.markdown("##### ⚡ Generated SQL Query")
            st.code(sql_query, language="sql")

            # Step B: SQL Safety Gate & SQLite Execution
            with st.spinner("🛡️ Validating safety guardrails and executing query..."):
                success, df, err_msg = execute_safe_query(sql_query, db_uri=db_uri)

            if not success:
                st.error(f"❌ **Execution Blocked / Failed:** {err_msg}")
                add_message(
                    "assistant",
                    {"sql": sql_query, "error": err_msg, "dataframe": None, "explanation": None},
                )
            else:
                # Step C: Display Results
                st.markdown(f"##### 📋 Query Results ({len(df)} rows)")
                if df.empty:
                    st.info("Query executed successfully, but returned 0 matching records.")
                else:
                    st.dataframe(df, width="stretch", hide_index=True)
                    csv_data = convert_df_to_csv(df)
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv_data,
                        file_name="nl2sql_query_results.csv",
                        mime="text/csv",
                        key="dl_active",
                    )

                # Step D: Dynamic Chart
                chart_fig = generate_auto_chart(df)
                if chart_fig:
                    st.plotly_chart(chart_fig, use_container_width=True)

                # Step E: AI Explanation
                with st.spinner("🧠 Generating natural language explanation..."):
                    explanation = explain_sql(active_prompt, sql_query)

                st.markdown("##### 💡 AI Explanation")
                st.info(explanation)

                # Step F: Save Complete Interaction to Session State
                add_message(
                    "assistant",
                    {
                        "sql": sql_query,
                        "dataframe": df,
                        "chart": chart_fig,
                        "explanation": explanation,
                        "error": None,
                    },
                )

        except Exception as exc:
            st.error(f"❌ **Application Error:** {exc}")
            add_message(
                "assistant",
                {"sql": sql_query, "error": str(exc), "dataframe": None, "explanation": None},
            )

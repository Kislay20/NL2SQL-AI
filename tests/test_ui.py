"""Unit tests for UI components, charts, and history management.

Verifies chart heuristic selection, session history records, and schema rendering helpers.
"""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from ui.charts import generate_auto_chart, render_dynamic_chart
from utils.history import init_history, add_message, clear_history, get_history


def test_auto_chart_none_for_empty():
    """Verify generate_auto_chart returns None for empty or single-row DataFrames."""
    assert generate_auto_chart(None) is None
    assert generate_auto_chart(pd.DataFrame()) is None
    assert generate_auto_chart(pd.DataFrame({"a": [1]})) is None


def test_auto_chart_for_two_columns():
    """Verify generate_auto_chart returns a valid Plotly Figure for 2-column aggregation."""
    df = pd.DataFrame({
        "department": ["Computer Science", "Mechanical", "Electronics"],
        "avg_marks": [85.5, 78.2, 81.0],
    })
    fig = generate_auto_chart(df)
    assert fig is not None
    assert "Figure" in type(fig).__name__


def test_auto_chart_none_for_general_table():
    """Verify general multi-column student table does not force a chart."""
    df = pd.DataFrame({
        "student_id": [1, 2, 3],
        "name": ["Aarav", "Priya", "Rohan"],
        "department": ["CS", "CS", "CS"],
        "year": [2, 3, 2],
        "email": ["a@edu", "p@edu", "r@edu"],
    })
    fig = generate_auto_chart(df)
    assert fig is None


def test_session_history_lifecycle():
    """Verify session history initialization, message appending, and clearing."""
    mock_session_state = {}

    with patch("utils.history.st.session_state", mock_session_state):
        init_history()
        assert "messages" in mock_session_state
        assert len(mock_session_state["messages"]) == 0

        add_message("user", {"text": "Show students"})
        assert len(mock_session_state["messages"]) == 1
        assert mock_session_state["messages"][0]["role"] == "user"

        add_message("assistant", {"sql": "SELECT * FROM students;"})
        assert len(mock_session_state["messages"]) == 2

        history = get_history()
        assert len(history) == 2

        clear_history()
        assert len(mock_session_state["messages"]) == 0


def test_render_dynamic_chart_heuristics():
    """Verify render_dynamic_chart follows empty, row count, and column heuristics."""
    # Empty & 1-row
    assert render_dynamic_chart(None) is None
    assert render_dynamic_chart(pd.DataFrame()) is None
    assert render_dynamic_chart(pd.DataFrame({"a": [1]})) is None

    # Cluttered (> 50 rows)
    cluttered_df = pd.DataFrame({"dept": ["CS"] * 55, "marks": list(range(55))})
    assert render_dynamic_chart(cluttered_df) is None

    # 2-column (categorical + numeric)
    bar_df = pd.DataFrame({"dept": ["CS", "ME", "EE"], "avg_marks": [80.5, 75.0, 82.0]})
    fig = render_dynamic_chart(bar_df)
    assert fig is not None
    assert "Figure" in type(fig).__name__

    # Multi-numeric grouped bar
    multi_df = pd.DataFrame({
        "dept": ["CS", "ME"],
        "min_marks": [60.0, 55.0],
        "max_marks": [95.0, 90.0],
    })
    grouped_fig = render_dynamic_chart(multi_df)
    assert grouped_fig is not None
    assert "Figure" in type(grouped_fig).__name__


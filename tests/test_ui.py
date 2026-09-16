"""Unit tests for UI components, charts, and history management.

Verifies chart heuristic selection, session history records, and schema rendering helpers.
"""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from ui.charts import generate_auto_chart
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

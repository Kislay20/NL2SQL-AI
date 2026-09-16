"""Query and conversation history management for NL2SQL AI Streamlit UI.

Maintains in-memory chat session history including user queries, generated SQL,
execution status, tabular outputs, and plain-English AI explanations.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List
import streamlit as st


def init_history() -> None:
    """Initialize session state history if not already present."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []


def add_message(role: str, content: Dict[str, Any]) -> None:
    """Append a message record to the session history.

    Args:
        role: Message author role ('user' or 'assistant').
        content: Dictionary containing query details, SQL, data, or error message.
    """
    init_history()
    record = {
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
    }
    st.session_state["messages"].append(record)


def clear_history() -> None:
    """Clear all chat messages from session state."""
    st.session_state["messages"] = []


def get_history() -> List[Dict[str, Any]]:
    """Retrieve the current list of history messages."""
    init_history()
    return st.session_state["messages"]

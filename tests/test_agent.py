"""Unit tests for LangGraph multi-agent orchestration module (ai/agent.py).

Verifies router intent classification, graph compilation, and state transitions.
"""

from unittest.mock import MagicMock, patch
import pytest

from ai.agent import (
    classify_intent,
    create_agent_graph,
    get_agent_graph,
    run_agent,
    router_node,
    conversational_node,
    validator_node,
)


def test_classify_intent_conversational():
    """Verify router identifies common greetings and chit-chat as conversational."""
    assert classify_intent("hello") == "conversational"
    assert classify_intent("Hi there!") == "conversational"
    assert classify_intent("Who are you?") == "conversational"
    assert classify_intent("namaste") == "conversational"
    assert classify_intent("Good morning!") == "conversational"
    assert classify_intent("thank you") == "conversational"
    assert classify_intent("") == "conversational"
    assert classify_intent("   ") == "conversational"


def test_classify_intent_query():
    """Verify router identifies database queries in English and Hinglish."""
    assert classify_intent("Show all students in CS") == "query"
    assert classify_intent("What is the average marks per department?") == "query"
    assert classify_intent("Wo students dikhao jinke marks 80 se zyada hain") == "query"
    assert classify_intent("Computer Science department mein kitne bacche hain?") == "query"
    assert classify_intent("List attendance percentages for all students") == "query"


def test_agent_graph_compilation():
    """Verify LangGraph StateGraph compiles successfully with expected nodes."""
    graph = create_agent_graph()
    assert graph is not None
    # Verify nodes exist in the compiled graph structure
    node_keys = graph.nodes.keys()
    for expected_node in ["router", "conversational", "coder", "validator"]:
        assert expected_node in node_keys


def test_conversational_node():
    """Verify conversational node returns a polite response without SQL."""
    state = {
        "question": "Hello!",
        "intent": "conversational",
        "sql": None,
        "is_valid": False,
        "error": None,
        "response": None,
        "validation_attempts": 0,
    }
    result = conversational_node(state)
    assert result["intent"] == "conversational"
    assert result["sql"] is None
    assert result["is_valid"] is True
    assert result["response"] is not None
    assert len(result["response"]) > 0


def test_validator_node_valid_sql():
    """Verify validator node passes valid SQLite SELECT queries."""
    state = {
        "question": "Show all students",
        "sql": "SELECT * FROM students;",
        "db_uri": "sqlite:///college.db",
        "is_valid": False,
        "error": None,
        "validation_attempts": 0,
    }
    result = validator_node(state)
    assert result["is_valid"] is True
    assert result["error"] is None


def test_validator_node_invalid_sql():
    """Verify validator node catches hallucinated tables or malformed syntax."""
    state = {
        "question": "Show non existent table",
        "sql": "SELECT * FROM imaginary_table_xyz;",
        "db_uri": "sqlite:///college.db",
        "is_valid": False,
        "error": None,
        "validation_attempts": 0,
    }
    result = validator_node(state)
    assert result["is_valid"] is False
    assert result["error"] is not None
    assert "imaginary_table_xyz" in result["error"] or "no such table" in result["error"].lower()


def test_run_agent_conversational_flow():
    """Verify run_agent correctly executes conversational flow end-to-end."""
    result = run_agent("hi")
    assert result["intent"] == "conversational"
    assert result["sql"] is None
    assert result["response"] is not None

"""Unit and integration tests for Flask REST API backend (api/server.py).

Verifies /api/health, /api/query, CORS headers, error handling, and JSON response formats.
"""

import json
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from api.server import create_app


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Verify /api/health returns 200 and status healthy."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "NL2SQL AI" in data["service"]


def test_cors_headers_present(client):
    """Verify CORS headers are present on API responses."""
    response = client.get("/api/health")
    assert "Access-Control-Allow-Origin" in response.headers


def test_query_endpoint_missing_json(client):
    """Verify 400 when request body is not JSON."""
    response = client.post("/api/query", data="not json", content_type="text/plain")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_query_endpoint_empty_query(client):
    """Verify 400 when 'query' field is missing or empty."""
    response = client.post("/api/query", json={})
    assert response.status_code == 400

    response = client.post("/api/query", json={"query": "   "})
    assert response.status_code == 400


def test_query_endpoint_conversational(client):
    """Verify conversational inputs return 200 with intent=conversational and data=None."""
    response = client.post("/api/query", json={"query": "hello"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["intent"] == "conversational"
    assert data["sql"] is None
    assert data["is_valid"] is True
    assert data["data"] is None
    assert data["response"] is not None


def test_query_endpoint_valid_query_mocked(client):
    """Verify valid SQL queries execute and return tabular rows as a list of dicts."""
    mock_state = {
        "question": "Show top students",
        "intent": "query",
        "sql": "SELECT student_id, name FROM students LIMIT 2;",
        "is_valid": True,
        "error": None,
        "response": None,
    }
    mock_df = pd.DataFrame({
        "student_id": [1, 2],
        "name": ["Aarav Sharma", "Priya Patel"],
    })

    with patch("api.server.run_agent", return_value=mock_state):
        with patch("api.server.execute_safe_query", return_value=(True, mock_df, "")):
            with patch("api.server.explain_sql", return_value="Retrieves the first two students."):
                response = client.post(
                    "/api/query",
                    json={"query": "Show top students", "db_uri": "sqlite:///college.db"},
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data["intent"] == "query"
                assert data["is_valid"] is True
                assert data["sql"] == "SELECT student_id, name FROM students LIMIT 2;"
                assert len(data["data"]) == 2
                assert data["data"][0]["name"] == "Aarav Sharma"
                assert "Retrieves the first two students." in data["response"]


def test_query_endpoint_invalid_sql(client):
    """Verify 400 status when query validation fails."""
    mock_state = {
        "question": "Show bad query",
        "intent": "query",
        "sql": "SELECT * FROM bad_table;",
        "is_valid": False,
        "error": "Table does not exist",
        "response": None,
    }

    with patch("api.server.run_agent", return_value=mock_state):
        response = client.post("/api/query", json={"query": "Show bad query"})
        assert response.status_code == 400
        data = response.get_json()
        assert data["intent"] == "query"
        assert data["is_valid"] is False
        assert "Table does not exist" in data["response"]


def test_query_endpoint_execution_failure(client):
    """Verify 400 status when database execution fails."""
    mock_state = {
        "question": "Show data",
        "intent": "query",
        "sql": "SELECT * FROM students;",
        "is_valid": True,
        "error": None,
        "response": None,
    }

    with patch("api.server.run_agent", return_value=mock_state):
        with patch("api.server.execute_safe_query", return_value=(False, None, "Database locked")):
            response = client.post("/api/query", json={"query": "Show data"})
            assert response.status_code == 400
            data = response.get_json()
            assert data["is_valid"] is False
            assert "Database execution error" in data["response"]


def test_query_endpoint_internal_server_error(client):
    """Verify 500 status when an unhandled exception occurs."""
    with patch("api.server.run_agent", side_effect=RuntimeError("Fatal agent crash")):
        response = client.post("/api/query", json={"query": "trigger crash"})
        assert response.status_code == 500
        data = response.get_json()
        assert "Internal Server Error" in data["error"]

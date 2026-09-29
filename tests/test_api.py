"""Unit and integration tests for Flask REST API backend (api/server.py).

Verifies /api/health, /api/query, /api/test-connection, Firebase JWT security,
CORS headers, tenant tracking, and JSON error response formats.
"""

import json
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from api.server import create_app

MOCK_HEADERS = {"Authorization": "Bearer mock_firebase_jwt_token"}


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_firebase_auth():
    """Mock Firebase Admin auth verification for authorized tests."""
    with patch(
        "firebase_admin.auth.verify_id_token",
        return_value={"uid": "tenant_123", "email": "test@college.edu"},
    ):
        yield


def test_health_endpoint(client):
    """Verify /api/health returns 200 and status healthy without auth."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "NL2SQL AI" in data["service"]


def test_cors_headers_present(client):
    """Verify CORS headers are present on API responses."""
    response = client.get("/api/health")
    assert "Access-Control-Allow-Origin" in response.headers


# ----------------------------------------------------------------------
# Security & Token Verification Tests
# ----------------------------------------------------------------------

def test_query_endpoint_missing_token(client):
    """Verify 401 status when Authorization header is completely omitted."""
    response = client.post("/api/query", json={"query": "hello"})
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "error"
    assert "Missing Authorization header" in data["error"]


def test_query_endpoint_malformed_token_header(client):
    """Verify 401 status when Authorization header is malformed."""
    response = client.post(
        "/api/query",
        json={"query": "hello"},
        headers={"Authorization": "TokenInvalid"},
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "error"
    assert "Invalid Authorization header format" in data["error"]


def test_query_endpoint_invalid_token(client):
    """Verify 401 status when token verification fails in Firebase."""
    with patch("firebase_admin.auth.verify_id_token", side_effect=ValueError("Token expired or forged")):
        response = client.post(
            "/api/query",
            json={"query": "hello"},
            headers={"Authorization": "Bearer bad_token"},
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["status"] == "error"
        assert "Token expired or forged" in data["error"]


def test_test_connection_missing_token(client):
    """Verify 401 status when Authorization header is missing on test-connection."""
    response = client.post("/api/test-connection", json={"db_uri": "sqlite:///college.db"})
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "error"
    assert "Missing Authorization header" in data["error"]


# ----------------------------------------------------------------------
# Authenticated Functional Tests
# ----------------------------------------------------------------------

def test_query_endpoint_missing_json(client, mock_firebase_auth):
    """Verify 400 when request body is not JSON."""
    response = client.post(
        "/api/query",
        data="not json",
        content_type="text/plain",
        headers=MOCK_HEADERS,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_query_endpoint_empty_query(client, mock_firebase_auth):
    """Verify 400 when 'query' field is missing or empty."""
    response = client.post("/api/query", json={}, headers=MOCK_HEADERS)
    assert response.status_code == 400

    response = client.post("/api/query", json={"query": "   "}, headers=MOCK_HEADERS)
    assert response.status_code == 400


def test_query_endpoint_conversational(client, mock_firebase_auth):
    """Verify conversational inputs return 200 with intent=conversational and data=None."""
    response = client.post("/api/query", json={"query": "hello"}, headers=MOCK_HEADERS)
    assert response.status_code == 200
    data = response.get_json()
    assert data["intent"] == "conversational"
    assert data["sql"] is None
    assert data["is_valid"] is True
    assert data["data"] is None
    assert data["response"] is not None


def test_query_endpoint_valid_query_mocked(client, mock_firebase_auth):
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
                    headers=MOCK_HEADERS,
                )
                assert response.status_code == 200
                data = response.get_json()
                assert data["intent"] == "query"
                assert data["is_valid"] is True
                assert data["sql"] == "SELECT student_id, name FROM students LIMIT 2;"
                assert len(data["data"]) == 2
                assert data["data"][0]["name"] == "Aarav Sharma"
                assert "Retrieves the first two students." in data["response"]


def test_query_endpoint_invalid_sql(client, mock_firebase_auth):
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
        response = client.post(
            "/api/query",
            json={"query": "Show bad query"},
            headers=MOCK_HEADERS,
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["intent"] == "query"
        assert data["is_valid"] is False
        assert "Table does not exist" in data["response"]


def test_query_endpoint_execution_failure(client, mock_firebase_auth):
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
            response = client.post(
                "/api/query",
                json={"query": "Show data"},
                headers=MOCK_HEADERS,
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data["is_valid"] is False
            assert "Database execution error" in data["response"]


def test_query_endpoint_internal_server_error(client, mock_firebase_auth):
    """Verify 500 status when an unhandled exception occurs."""
    with patch("api.server.run_agent", side_effect=RuntimeError("Fatal agent crash")):
        response = client.post(
            "/api/query",
            json={"query": "trigger crash"},
            headers=MOCK_HEADERS,
        )
        assert response.status_code == 500
        data = response.get_json()
        assert "Internal Server Error" in data["error"]


def test_test_connection_success(client, mock_firebase_auth):
    """Verify /api/test-connection returns 200 for valid local SQLite DB."""
    response = client.post(
        "/api/test-connection",
        json={"db_uri": "sqlite:///college.db"},
        headers=MOCK_HEADERS,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "verified" in data["message"].lower()


def test_test_connection_missing_payload(client, mock_firebase_auth):
    """Verify 400 status when db_uri is missing or invalid in /api/test-connection."""
    response = client.post("/api/test-connection", json={}, headers=MOCK_HEADERS)
    assert response.status_code == 400
    assert response.get_json()["status"] == "error"

    response = client.post(
        "/api/test-connection",
        data="not json",
        content_type="text/plain",
        headers=MOCK_HEADERS,
    )
    assert response.status_code == 400


def test_test_connection_invalid_uri(client, mock_firebase_auth):
    """Verify 400 status when db_uri fails connection."""
    response = client.post(
        "/api/test-connection",
        json={"db_uri": "postgresql://invalid_user:pass@127.0.0.1:9999/nonexistent"},
        headers=MOCK_HEADERS,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"
    assert "error" in data


# ----------------------------------------------------------------------
# Read-Only Security Filter (Forbidden Keywords) Tests
# ----------------------------------------------------------------------

@pytest.mark.parametrize("forbidden_kw", ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"])
def test_query_endpoint_forbidden_keywords_blocked(client, mock_firebase_auth, forbidden_kw):
    """Verify 403 Forbidden status when AI generates a query containing forbidden keywords."""
    mock_state = {
        "question": f"Perform {forbidden_kw} operation",
        "intent": "query",
        "sql": f"{forbidden_kw} TABLE students;",
        "is_valid": False,
        "error": f"Disallowed {forbidden_kw}",
        "response": None,
    }

    with patch("api.server.run_agent", return_value=mock_state):
        with patch("api.server.execute_safe_query") as mock_exec:
            response = client.post(
                "/api/query",
                json={"query": f"Perform {forbidden_kw} operation"},
                headers=MOCK_HEADERS,
            )
            assert response.status_code == 403
            data = response.get_json()
            assert data["is_valid"] is False
            assert data["error"] == "Security Alert: Only SELECT (read-only) queries are allowed!"
            assert data["response"] == "Security Alert: Only SELECT (read-only) queries are allowed!"
            assert data["data"] == []
            # Crucial: verify database execution was never called
            mock_exec.assert_not_called()


def test_query_endpoint_forbidden_keyword_validation_bypass_attempt(client, mock_firebase_auth):
    """Verify that even if an agent erroneously reports is_valid=True, execution is blocked with 403."""
    mock_state = {
        "question": "Sneaky update",
        "intent": "query",
        "sql": "UPDATE students SET marks = 100 WHERE student_id = 1;",
        "is_valid": True,  # simulated agent validation bypass
        "error": None,
        "response": None,
    }

    with patch("api.server.run_agent", return_value=mock_state):
        with patch("api.server.execute_safe_query") as mock_exec:
            response = client.post(
                "/api/query",
                json={"query": "Sneaky update"},
                headers=MOCK_HEADERS,
            )
            assert response.status_code == 403
            data = response.get_json()
            assert data["is_valid"] is False
            assert data["error"] == "Security Alert: Only SELECT (read-only) queries are allowed!"
            assert data["data"] == []
            mock_exec.assert_not_called()


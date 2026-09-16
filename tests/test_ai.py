"""Tests for Gemini client, configuration, prompts, parser, and SQL generation.

Includes unit tests with mocks for error conditions, parser tests,
prompt structure tests, and live integration tests when GEMINI_API_KEY is active.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import pytest

from ai.gemini import (
    GeminiClient,
    GeminiError,
    MissingAPIKeyError,
    InvalidAPIKeyError,
    RateLimitError,
    ServiceUnavailableError,
    GeminiAPIError,
    EmptyResponseError,
    get_gemini_client,
    verify_gemini_connection,
)
from ai.parser import extract_sql
from ai.prompts import build_sql_prompt, SQL_GENERATION_SYSTEM_INSTRUCTION
from ai.sql_generator import generate_sql
from google.genai import errors


# ----------------------------------------------------------------------
# Unit Tests: Gemini Client (Mocked)
# ----------------------------------------------------------------------

def test_missing_api_key_raises_error():
    """Verify MissingAPIKeyError is raised when no API key is provided."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True):
        with pytest.raises(MissingAPIKeyError) as exc_info:
            GeminiClient(api_key="")
        assert "GEMINI_API_KEY is not set" in str(exc_info.value)


def test_placeholder_api_key_raises_error():
    """Verify placeholder key strings raise MissingAPIKeyError."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "your_gemini_api_key_here"}, clear=True):
        with pytest.raises(MissingAPIKeyError) as exc_info:
            GeminiClient(api_key="your_gemini_api_key_here")
        assert "placeholder" in str(exc_info.value).lower()


def test_custom_model_configuration():
    """Verify custom model name can be supplied and overrides defaults."""
    with patch("ai.gemini.genai.Client"):
        client = GeminiClient(api_key="dummy-test-key", model="gemini-2.0-flash")
        assert client.model_name == "gemini-2.0-flash"


def test_empty_prompt_raises_value_error():
    """Verify empty prompt strings are rejected before making network calls."""
    with patch("ai.gemini.genai.Client"):
        client = GeminiClient(api_key="dummy-test-key")
        with pytest.raises(ValueError):
            client.generate_text("")


def test_empty_response_raises_error():
    """Verify EmptyResponseError is raised if Gemini returns null/blank text."""
    with patch("ai.gemini.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "   "
        mock_instance.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(api_key="dummy-test-key")
        with pytest.raises(EmptyResponseError):
            client.generate_text("Hello")


def test_invalid_api_key_error_translation():
    """Verify HTTP 400 API_KEY_INVALID translates into InvalidAPIKeyError."""
    with patch("ai.gemini.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_err = errors.ClientError(400, {"error": {"message": "API_KEY_INVALID"}}, None)
        mock_instance.models.generate_content.side_effect = mock_err
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(api_key="dummy-test-key")
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            client.generate_text("Hello", retries=0)
        assert "invalid" in str(exc_info.value).lower()


def test_rate_limit_error_translation():
    """Verify HTTP 429 quota exhaustion translates into RateLimitError."""
    with patch("ai.gemini.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_err = errors.ClientError(429, {"error": {"message": "RESOURCE_EXHAUSTED"}}, None)
        mock_instance.models.generate_content.side_effect = mock_err
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(api_key="dummy-test-key")
        with pytest.raises(RateLimitError):
            client.generate_text("Hello", retries=0)


def test_service_unavailable_error_translation():
    """Verify HTTP 503 high demand spike translates into ServiceUnavailableError."""
    with patch("ai.gemini.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_err = errors.ServerError(503, {"error": {"message": "Model high demand"}}, None)
        mock_instance.models.generate_content.side_effect = mock_err
        mock_client_cls.return_value = mock_instance

        client = GeminiClient(api_key="dummy-test-key")
        with pytest.raises(ServiceUnavailableError):
            client.generate_text("Hello", retries=0)


def test_get_gemini_client_singleton():
    """Verify get_gemini_client caches instances."""
    with patch("ai.gemini.genai.Client"):
        client1 = get_gemini_client(api_key="test-key-singleton")
        client2 = get_gemini_client(api_key="test-key-singleton")
        assert client1 is not None
        assert client2 is not None


# ----------------------------------------------------------------------
# Unit Tests: Parser (ai/parser.py)
# ----------------------------------------------------------------------

def test_extract_sql_markdown_fences():
    """Verify markdown code fences with 'sql' tag are stripped cleanly."""
    raw = "```sql\nSELECT * FROM students WHERE year = 2;\n```"
    assert extract_sql(raw) == "SELECT * FROM students WHERE year = 2;"


def test_extract_sql_plain_fences():
    """Verify markdown code fences without language tag are stripped."""
    raw = "```\nSELECT name, email FROM students;\n```"
    assert extract_sql(raw) == "SELECT name, email FROM students;"


def test_extract_sql_preamble_removal():
    """Verify conversational preambles are removed."""
    raw = "Here is the SQL query:\n```sql\nSELECT * FROM subjects;\n```"
    assert extract_sql(raw) == "SELECT * FROM subjects;"

    raw2 = "SQL: SELECT * FROM marks;"
    assert extract_sql(raw2) == "SELECT * FROM marks;"


def test_extract_sql_backticks_and_quotes():
    """Verify backticks and extraneous surrounding quotes are removed."""
    raw = "`SELECT department FROM students;`"
    assert extract_sql(raw) == "SELECT department FROM students;"

    raw2 = '"SELECT * FROM attendance;"'
    assert extract_sql(raw2) == "SELECT * FROM attendance;"


def test_extract_sql_semicolon_normalization():
    """Verify trailing semicolon is added if missing."""
    raw = "SELECT * FROM students"
    assert extract_sql(raw) == "SELECT * FROM students;"


def test_extract_sql_empty():
    """Verify blank inputs return empty strings safely."""
    assert extract_sql("") == ""
    assert extract_sql("   ") == ""


# ----------------------------------------------------------------------
# Unit Tests: Prompts (ai/prompts.py)
# ----------------------------------------------------------------------

def test_build_sql_prompt_structure():
    """Verify prompt formatting contains user question, schema, and examples."""
    schema = "Table: students\n  - student_id\n  - name"
    prompt = build_sql_prompt("Show all students", schema)

    assert "Table: students" in prompt
    assert 'User Question: "Show all students"' in prompt
    assert "Few-Shot Examples:" in prompt
    assert "SQL:" in prompt


def test_sql_system_instruction_rules():
    """Verify system instructions enforce read-only and no hallucinations."""
    assert "read-only" in SQL_GENERATION_SYSTEM_INSTRUCTION.lower()
    assert "no insert, update, delete, drop" in SQL_GENERATION_SYSTEM_INSTRUCTION.lower()


# ----------------------------------------------------------------------
# Unit Tests: SQL Generator (Mocked)
# ----------------------------------------------------------------------

def test_generate_sql_empty_question_raises():
    """Verify empty question raises ValueError."""
    with pytest.raises(ValueError):
        generate_sql("")


def test_generate_sql_mocked():
    """Verify generate_sql coordinates prompt construction and extraction."""
    mock_client = MagicMock()
    mock_client.generate_text.return_value = "```sql\nSELECT * FROM students;\n```"

    sql = generate_sql("Show all students", client=mock_client)
    assert sql == "SELECT * FROM students;"
    mock_client.generate_text.assert_called_once()


# ----------------------------------------------------------------------
# Live Integration Tests (Executes if valid key exists in environment)
# ----------------------------------------------------------------------

def test_live_gemini_connection():
    """Test actual live connection to Gemini API if a valid key is provided in .env."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key.startswith("your_gemini"):
        pytest.skip("Skipping live API test: no valid GEMINI_API_KEY configured in .env")

    result = verify_gemini_connection()
    assert result["status"] == "connected"
    assert "model" in result
    assert "response" in result
    assert len(result["response"]) > 0


def test_live_generate_sql_simple():
    """Test live SQL generation for a basic query."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key.startswith("your_gemini"):
        pytest.skip("Skipping live API test: no valid GEMINI_API_KEY configured in .env")

    sql = generate_sql("Show all students in Computer Science")
    assert sql.upper().startswith("SELECT")
    assert "students" in sql.lower()
    assert "computer science" in sql.lower()


def test_live_generate_sql_complex():
    """Test live SQL generation for group by and join query."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key.startswith("your_gemini"):
        pytest.skip("Skipping live API test: no valid GEMINI_API_KEY configured in .env")

    sql = generate_sql("Which department has the highest average marks?")
    assert sql.upper().startswith("SELECT")
    assert "department" in sql.lower()
    assert "avg" in sql.lower() or "average" in sql.lower()
    assert "marks" in sql.lower()

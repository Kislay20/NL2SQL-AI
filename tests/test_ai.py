"""Tests for Gemini client, configuration, and error handling.

Includes unit tests with mocks for error conditions and live integration tests
when a valid GEMINI_API_KEY is configured in the environment.
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
from google.genai import errors


# ----------------------------------------------------------------------
# Unit Tests (Mocked - No live API calls)
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
# Live Integration Test (Executes if valid key exists in environment)
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

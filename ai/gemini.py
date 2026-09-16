"""Gemini client configuration and API integration for NL2SQL AI.

Provides a robust, reusable interface to the official Google Gemini SDK (google-genai),
with structured error handling for missing keys, invalid keys, quota/rate limits,
transient server spikes, and malformed responses.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from google import genai
from google.genai import errors, types

load_dotenv()
logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash"]
PLACEHOLDER_KEYS = {
    "",
    "your_gemini_api_key_here",
    "your_api_key_here",
    "replace_with_your_key",
}


# ----------------------------------------------------------------------
# Custom Exceptions
# ----------------------------------------------------------------------

class GeminiError(Exception):
    """Base exception for all Gemini integration errors."""
    pass


class MissingAPIKeyError(GeminiError):
    """Raised when the GEMINI_API_KEY is missing or contains a placeholder value."""
    pass


class InvalidAPIKeyError(GeminiError):
    """Raised when the Google Gemini API rejects the provided API key (HTTP 400/403)."""
    pass


class RateLimitError(GeminiError):
    """Raised when the API rate limit or quota has been exceeded (HTTP 429)."""
    pass


class ServiceUnavailableError(GeminiError):
    """Raised when Gemini service is experiencing temporary high demand or outage (HTTP 503)."""
    pass


class GeminiAPIError(GeminiError):
    """Raised for unexpected Google API communication errors."""
    pass


class EmptyResponseError(GeminiError):
    """Raised when Gemini returns an empty or null text response."""
    pass


# ----------------------------------------------------------------------
# Gemini Client
# ----------------------------------------------------------------------

class GeminiClient:
    """Wrapper around Google GenAI client providing resilient prompt execution and error translation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Initialize the Gemini client.

        Args:
            api_key: Optional API key. If omitted, loaded from GEMINI_API_KEY env var.
            model: Optional model name. If omitted, loaded from GEMINI_MODEL or defaults to gemini-2.5-flash.
        """
        # Always reload environment variables in case .env was recently modified
        load_dotenv(override=False)

        resolved_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        if not resolved_key or resolved_key in PLACEHOLDER_KEYS:
            raise MissingAPIKeyError(
                "GEMINI_API_KEY is not set or contains a placeholder value. "
                "Please configure a valid Google Gemini API key in your .env file."
            )

        self._api_key = resolved_key
        self.model_name = (model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)).strip()

        try:
            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:
            raise GeminiAPIError(f"Failed to initialize Google GenAI client: {exc}") from exc

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: Optional[int] = None,
        retries: int = 2,
        backoff_factor: float = 1.5,
    ) -> str:
        """Generate text from a prompt using Google Gemini with error handling and retry support.

        Args:
            prompt: User or task prompt string.
            system_instruction: Optional system instruction / persona prompt.
            temperature: Sampling temperature (0.0 = deterministic).
            max_output_tokens: Optional limit on output token count.
            retries: Number of retry attempts on transient 503 or 429 errors.
            backoff_factor: Multiplier for exponential backoff between retries.

        Returns:
            The generated response string.

        Raises:
            MissingAPIKeyError: If API key is not configured.
            InvalidAPIKeyError: If the API key is rejected.
            RateLimitError: If rate limit / quota is exhausted.
            ServiceUnavailableError: If the service is overloaded.
            GeminiAPIError: If an API error occurs.
            EmptyResponseError: If the response is blank.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_instruction=system_instruction,
            # Disable automatic function calling to prevent CLI warning messages
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        last_exception: Optional[Exception] = None
        attempt = 0

        while attempt <= retries:
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                text = response.text
                if text is None or not text.strip():
                    raise EmptyResponseError("Gemini returned an empty response.")

                return text.strip()

            except errors.ClientError as exc:
                err_msg = str(exc).lower()
                status_code = getattr(exc, "code", None)

                # Check for invalid API key (HTTP 400 with API_KEY_INVALID or INVALID_ARGUMENT)
                if status_code == 400 and ("api_key" in err_msg or "invalid" in err_msg):
                    raise InvalidAPIKeyError(
                        "The configured GEMINI_API_KEY is invalid. Please check your API key in .env."
                    ) from exc

                # Check for rate limit / quota exhaustion (HTTP 429)
                if status_code == 429 or "resource_exhausted" in err_msg or "quota" in err_msg:
                    if attempt < retries:
                        attempt += 1
                        time.sleep(backoff_factor * attempt)
                        continue
                    raise RateLimitError(
                        "Gemini API rate limit or quota exceeded. Please wait a moment before trying again."
                    ) from exc

                raise GeminiAPIError(f"Gemini client error (HTTP {status_code}): {exc}") from exc

            except errors.ServerError as exc:
                err_msg = str(exc).lower()
                status_code = getattr(exc, "code", None)

                # Transient 503 High Demand Spikes
                if status_code == 503 or "high demand" in err_msg or "unavailable" in err_msg:
                    if attempt < retries:
                        attempt += 1
                        time.sleep(backoff_factor * attempt)
                        continue
                    raise ServiceUnavailableError(
                        f"The Gemini model '{self.model_name}' is temporarily experiencing high demand. "
                        "Please retry in a few seconds."
                    ) from exc

                if attempt < retries:
                    attempt += 1
                    time.sleep(backoff_factor * attempt)
                    continue
                raise GeminiAPIError(f"Gemini server error (HTTP {status_code}): {exc}") from exc

            except EmptyResponseError:
                raise

            except Exception as exc:
                last_exception = exc
                if attempt < retries:
                    attempt += 1
                    time.sleep(backoff_factor * attempt)
                    continue
                break

        raise GeminiAPIError(
            f"Failed to communicate with Gemini API after {retries + 1} attempts: {last_exception}"
        ) from last_exception

    def check_connection(self) -> Dict[str, Any]:
        """Perform a lightweight health check to confirm Gemini API connectivity.

        Returns:
            Dictionary with status, model name, and test response.
        """
        response_text = self.generate_text(
            prompt="Health check. Reply with the exact word: OK",
            temperature=0.0,
            max_output_tokens=10,
            retries=2,
        )
        return {
            "status": "connected",
            "model": self.model_name,
            "response": response_text,
            "message": "Successfully connected to Google Gemini API.",
        }


# ----------------------------------------------------------------------
# Singleton / Helper Functions
# ----------------------------------------------------------------------

_cached_client: Optional[GeminiClient] = None


def get_gemini_client(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    force_new: bool = False,
) -> GeminiClient:
    """Get a shared or new GeminiClient instance.

    Args:
        api_key: Optional API key override.
        model: Optional model override.
        force_new: If True, forces creation of a new instance.

    Returns:
        GeminiClient instance.
    """
    global _cached_client
    if force_new or _cached_client is None or api_key or model:
        client = GeminiClient(api_key=api_key, model=model)
        if not api_key and not model:
            _cached_client = client
        return client
    return _cached_client


def verify_gemini_connection() -> Dict[str, Any]:
    """Convenience helper to verify Gemini connectivity using the default client."""
    client = get_gemini_client()
    return client.check_connection()


if __name__ == "__main__":
    print("Testing Gemini API Connection...")
    try:
        result = verify_gemini_connection()
        print(f"[SUCCESS] Status: {result['status']}")
        print(f"Model: {result['model']}")
        print(f"Response: {result['response']}")
        print(f"Message: {result['message']}")
    except GeminiError as e:
        print(f"[ERROR] Gemini Error: {type(e).__name__} - {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected Error: {type(e).__name__} - {e}")

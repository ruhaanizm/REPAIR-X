import os

from openai import OpenAI

# Fail fast instead of hanging for the SDK default of 10 minutes.
REQUEST_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
MAX_RETRIES = 1


def create_provider(provider_name=None):
    """Return an API client and model for the selected provider."""

    provider = (
        provider_name or os.getenv("LLM_PROVIDER", "openai")
    ).strip().lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing.")

        client = OpenAI(
            api_key=api_key,
            timeout=REQUEST_TIMEOUT,
            max_retries=MAX_RETRIES,
        )
        return client, model

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing.")

        client = OpenAI(
            api_key=api_key,
            timeout=REQUEST_TIMEOUT,
            max_retries=MAX_RETRIES,
            base_url=(
                "https://generativelanguage.googleapis.com/"
                "v1beta/openai/"
            ),
        )
        return client, model

    raise ValueError(f"Unsupported LLM provider: {provider}")
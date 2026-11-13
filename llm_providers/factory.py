
import os

from openai import OpenAI


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

        return OpenAI(api_key=api_key), model

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing.")

        client = OpenAI(
            api_key=api_key,
            base_url=(
                "https://generativelanguage.googleapis.com/"
                "v1beta/openai/"
            ),
        )
        return client, model

    raise ValueError(f"Unsupported LLM provider: {provider}")

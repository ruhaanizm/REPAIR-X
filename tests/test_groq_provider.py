
from unittest.mock import patch

import pytest

from llm_providers.factory import create_provider


def test_groq_provider_configuration(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "dummy-test-key")
    monkeypatch.setenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    with patch("llm_providers.factory.OpenAI") as mock_client:
        client, model = create_provider("groq")

    assert client is mock_client.return_value
    assert model == "qwen/qwen3.8-27b"

    kwargs = mock_client.call_args.kwargs
    assert kwargs["api_key"] == "dummy-test-key"
    assert kwargs["base_url"] == "https://api.groq.com/openai/v1"


def test_groq_missing_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        create_provider("groq")

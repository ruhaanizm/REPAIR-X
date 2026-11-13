
from openai import APIConnectionError
from auto_repair import repair_incident


class FakeCompletions:
    def create(self, **kwargs):
        raise APIConnectionError(
            message="Simulated connection failure",
            request=None,
        )


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_api_connection_error_uses_validated_fallback():
    evidence = {
        "exception_type": "ZeroDivisionError",
        "message": "division by zero",
        "traceback": "Simulated traceback",
    }

    result = repair_incident(
        FakeClient(),
        "test-model",
        "divide",
        evidence,
    )

    assert result["patch_source"] == "fallback"
    assert result["fallback_reason"] == "api_error: APIConnectionError"
    assert result["repair_success"] is True
    assert "if b == 0:" in result["patch"]

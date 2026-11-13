
from openai import APIConnectionError

from auto_repair import repair_incident


class FakeResponses:
    def create(self, **kwargs):
        request = type(
            "Request",
            (),
            {"url": "https://api.openai.com/v1/responses"},
        )()
        raise APIConnectionError(
            message="Simulated connection failure",
            request=request,
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


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

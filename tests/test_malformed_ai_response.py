
from auto_repair import repair_incident


class FakeResponse:
    output_text = "definitely not valid python !!!"


class FakeResponses:
    def create(self, **kwargs):
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_malformed_ai_response_uses_fallback():
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
    assert result["fallback_reason"] == "invalid_ai_patch: SyntaxError"
    assert result["repair_success"] is True
    assert "if b == 0:" in result["patch"]

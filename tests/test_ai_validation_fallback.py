
import auto_repair


def test_valid_but_incorrect_ai_patch_uses_fallback(monkeypatch):
    # This is valid Python, but functionally incorrect.
    monkeypatch.setattr(
        auto_repair,
        "request_patch",
        lambda client, model, scenario, evidence: "return 0",
    )

    evidence = {
        "exception_type": "ZeroDivisionError",
        "message": "division by zero",
        "traceback": "Simulated traceback",
    }

    result = auto_repair.repair_incident(
        client=None,
        model="test-model",
        scenario_name="divide",
        evidence=evidence,
    )

    assert result["patch_source"] == "fallback"
    assert result["fallback_reason"] == "ai_patch_failed_validation"
    assert result["repair_success"] is True
    assert "if b == 0:" in result["patch"]

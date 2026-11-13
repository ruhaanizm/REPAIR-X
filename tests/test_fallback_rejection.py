
import auto_repair


def test_repair_rejected_when_ai_and_fallback_fail(monkeypatch):
    monkeypatch.setattr(
        auto_repair,
        "request_patch",
        lambda client, model, scenario, evidence: "return 0",
    )

    monkeypatch.setattr(
        auto_repair,
        "validate_candidate",
        lambda candidate, scenario: (
            False,
            "Simulated validation failure",
        ),
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

    assert result["repair_success"] is False
    assert result["patch_source"] == "ai"
    assert result["fallback_reason"] == (
        "ai_patch_failed_validation; fallback_patch_failed_validation"
    )

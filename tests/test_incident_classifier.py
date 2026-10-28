
from incident_classifier import classify_fault, create_incident


def test_classifies_zero_division():
    result = classify_fault("ZeroDivisionError", "division by zero")

    assert result["fault_category"] == "division_by_zero"
    assert result["repair_strategy"] == "guard_zero_denominator"


def test_classifies_key_error():
    result = classify_fault("KeyError", "'port'")

    assert result["fault_category"] == "missing_dictionary_key"
    assert result["repair_strategy"] == "check_key_or_use_default"


def test_unknown_fault_requires_review():
    result = classify_fault("RuntimeError", "unknown failure")

    assert result["fault_category"] == "unknown"
    assert result["repair_strategy"] == "manual_review"


def test_incident_contains_evidence_and_classification():
    incident = create_incident(
        "KeyError",
        "'port'",
        "get_config_value(config, 'port')",
    )

    assert incident["incident_id"].startswith("RX-")
    assert incident["exception_type"] == "KeyError"
    assert incident["fault_category"] == "missing_dictionary_key"
    assert incident["traceback"] == "get_config_value(config, 'port')"

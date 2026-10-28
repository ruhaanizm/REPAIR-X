
"""Evidence-based fault classification for REPAIR-X."""

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class Incident:
    incident_id: str
    timestamp: str
    exception_type: str
    message: str
    traceback: str
    fault_category: str
    confidence: float
    repair_strategy: str


def classify_fault(exception_type, message, traceback=""):
    """Classify an incident using explicit, inspectable rules."""
    text = f"{message}\n{traceback}"

    if exception_type == "ZeroDivisionError":
        return {
            "fault_category": "division_by_zero",
            "confidence": 0.99,
            "repair_strategy": "guard_zero_denominator",
        }

    if exception_type == "KeyError":
        return {
            "fault_category": "missing_dictionary_key",
            "confidence": 0.99,
            "repair_strategy": "check_key_or_use_default",
        }

    if exception_type == "TypeError":
        return {
            "fault_category": "type_mismatch",
            "confidence": 0.85,
            "repair_strategy": "inspect_argument_types",
        }

    if exception_type == "AttributeError":
        return {
            "fault_category": "missing_attribute",
            "confidence": 0.85,
            "repair_strategy": "inspect_object_and_attribute",
        }

    if re.search(r"timed out|connection refused|network", text, re.I):
        return {
            "fault_category": "possible_network_failure",
            "confidence": 0.65,
            "repair_strategy": "inspect_connectivity_and_retry_policy",
        }

    return {
        "fault_category": "unknown",
        "confidence": 0.0,
        "repair_strategy": "manual_review",
    }


def create_incident(exception_type, message, traceback=""):
    """Create a structured incident record from failure evidence."""
    classification = classify_fault(
        exception_type, message, traceback
    )

    incident = Incident(
        incident_id=datetime.now(timezone.utc).strftime(
            "RX-%Y%m%dT%H%M%S-%fZ"
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
        exception_type=exception_type,
        message=message,
        traceback=traceback,
        **classification,
    )

    return asdict(incident)

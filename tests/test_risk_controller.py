from risk_controller import assess_patch
from recovery_demo import run_demo

OLD = "def f(a, b):\n    return a / b\n"
SAFE = "def f(a, b):\n    if b == 0:\n        return None\n    return a / b\n"


def test_accepts_small_valid_patch():
    assert assess_patch(OLD, SAFE, visible_pass=True, hidden_pass=True).action == "ACCEPT"


def test_rejects_failed_hidden_validation():
    assert assess_patch(OLD, SAFE, visible_pass=True, hidden_pass=False).action == "REJECT"


def test_rejects_sensitive_call():
    bad = "def f(a, b):\n    return eval('1')\n"
    assert assess_patch(OLD, bad, visible_pass=True, hidden_pass=True).action == "REJECT"


def test_rejects_signature_change():
    bad = "def f(a):\n    return a\n"
    assert assess_patch(OLD, bad, visible_pass=True, hidden_pass=True).action == "REJECT"


def test_recover_after_rejection():
    report = run_demo(mode="recover")
    assert report["outcome"] == "ACCEPTED"
    assert len(report["attempts"]) == 2
    assert report["attempts"][0]["risk"]["action"] == "REJECT"
    assert report["attempts"][1]["risk"]["action"] == "ACCEPT"
    assert report["original_unchanged"]


def test_abstains_after_max_attempts():
    report = run_demo(mode="reject")
    assert report["outcome"] == "ABSTAINED"
    assert len(report["attempts"]) == 3


def test_high_risk_rejected():
    report = run_demo(mode="high-risk")
    assert report["outcome"] == "ABSTAINED"

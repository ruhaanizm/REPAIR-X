
from pathlib import Path

from repair_x import apply_validate_or_rollback


def test_failed_validation_restores_original_file(tmp_path):
    target = tmp_path / "demo_app.py"

    original = "def calculate():\n    return 10\n"
    invalid_candidate = "THIS IS THE WRONG CANDIDATE\n"

    target.write_text(original, encoding="utf-8")

    # Simulate a test suite rejecting the candidate patch.
    def reject_candidate():
        return False, "Simulated regression failure"

    passed, output = apply_validate_or_rollback(
        candidate_source=invalid_candidate,
        original_source=original,
        target_path=target,
        test_runner=reject_candidate,
    )

    assert passed is False
    assert "regression failure" in output
    assert target.read_text(encoding="utf-8") == original

    print("ROLLBACK VERIFIED: original source restored.")


def test_passing_validation_keeps_candidate(tmp_path):
    target = tmp_path / "demo_app.py"

    original = "def calculate():\n    return 10\n"
    candidate = "def calculate():\n    return 20\n"

    target.write_text(original, encoding="utf-8")

    def accept_candidate():
        return True, "All tests passed"

    passed, output = apply_validate_or_rollback(
        candidate_source=candidate,
        original_source=original,
        target_path=target,
        test_runner=accept_candidate,
    )

    assert passed is True
    assert target.read_text(encoding="utf-8") == candidate

"""Offline, reproducible REPAIR-X risk/recovery demonstration.

No model API required. Works with existing benchmark fixtures and test harness.
Candidate execution uses subprocesses and is NOT a secure sandbox.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from benchmark.cases import CASES
from auto_repair import replace_function_body
from benchmark_runner import check_tests
from risk_controller import assess_patch, MAX_ATTEMPTS

ROOT = Path(__file__).resolve().parent


def run_demo(case_id="divide_zero", mode="recover", output=None):
    case = next((x for x in CASES if x["id"] == case_id), None)
    if case is None:
        raise ValueError("Unknown benchmark case: " + case_id)
    # Known controlled fixture: scripted candidates demonstrate the controller,
    # NOT model-generated autonomous repair capability.
    if case_id != "divide_zero":
        raise ValueError("Offline scripted demo currently supports divide_zero only")
    scripts = {
        "recover": ["return a / b", "if b == 0:\n    return None\nreturn a / b"],
        "reject": ["return a / b", "return a / b", "return a / b"],
        "high-risk": ["return eval(\"1\")"],
    }
    attempts = []
    original = case["source"]
    original_snapshot = original
    accepted = None
    for number, body in enumerate(scripts[mode][:MAX_ATTEMPTS], start=1):
        try:
            candidate = replace_function_body(original_snapshot, case["function"], body)
            preliminary = assess_patch(original_snapshot, candidate, visible_pass=True, hidden_pass=True)
            if preliminary.score >= 50:
                visible, hidden = False, False
                visible_error, hidden_error = "blocked_by_pre_execution_risk", "blocked_by_pre_execution_risk"
                decision = preliminary
            else:
                visible, visible_error = check_tests(candidate, case["function"], case["visible"])
                hidden, hidden_error = check_tests(candidate, case["function"], case["hidden"])
                decision = assess_patch(original_snapshot, candidate, visible_pass=visible, hidden_pass=hidden)
            entry = {"attempt": number, "patch": body, "visible_pass": visible,
                     "hidden_pass": hidden, "risk": decision.to_dict(),
                     "validation_error": (visible_error if not visible else hidden_error if not hidden else "")[:250]}
            attempts.append(entry)
            if decision.action == "ACCEPT":
                accepted = candidate
                break
        except (SyntaxError, ValueError) as exc:
            attempts.append({"attempt": number, "patch": body, "decision": "REJECT",
                             "error": f"{type(exc).__name__}: {exc}"})
    # Rollback means discarding isolated candidates; the original remains unchanged.
    report = {"run_id": uuid4().hex, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "demo_type": "scripted_offline_controller", "case_id": case_id, "mode": mode,
              "max_attempts": MAX_ATTEMPTS, "attempts": attempts,
              "outcome": "ACCEPTED" if accepted is not None else "ABSTAINED",
              "original_unchanged": original == original_snapshot,
              "rollback_semantics": "rejected temporary candidates discarded; source never overwritten"}
    if output:
        Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["recover", "reject", "high-risk"], default="recover")
    parser.add_argument("--output", default="recovery_demo_report.json")
    args = parser.parse_args()
    report = run_demo(mode=args.mode, output=args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

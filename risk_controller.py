"""Risk-aware decision policy for REPAIR-X controlled demonstration.

This policy is a transparent heuristic, not a security guarantee.
"""
from dataclasses import dataclass, asdict
import ast
import difflib

MAX_ATTEMPTS = 3

@dataclass(frozen=True)
class RiskDecision:
    score: int
    level: str
    reasons: tuple[str, ...]
    action: str

    def to_dict(self):
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


def assess_patch(original: str, candidate: str, *, visible_pass: bool,
                 hidden_pass: bool, confidence: float = 1.0) -> RiskDecision:
    """Conservative risk scoring for single-file Python patches."""
    reasons = []
    score = 0
    try:
        old_tree = ast.parse(original)
        new_tree = ast.parse(candidate)
    except SyntaxError:
        return RiskDecision(100, "HIGH", ("invalid_python",), "REJECT")

    old_functions = {n.name: len(n.args.args) for n in ast.walk(old_tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new_functions = {n.name: len(n.args.args) for n in ast.walk(new_tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if old_functions != new_functions:
        score += 50
        reasons.append("function_signature_changed")

    diff = list(difflib.unified_diff(original.splitlines(), candidate.splitlines()))
    changed = sum(1 for line in diff if line.startswith(("+", "-"))
                  and not line.startswith(("+++", "---")))
    if changed > 20:
        score += 30
        reasons.append("large_patch_over_20_lines")
    elif changed > 8:
        score += 15
        reasons.append("moderate_patch_over_8_lines")

    risky_calls = {"eval", "exec", "compile", "__import__", "open"}
    for node in ast.walk(new_tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            score += 40
            reasons.append("new_or_existing_import_requires_review")
            break
    for node in ast.walk(new_tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in risky_calls:
            score += 60
            reasons.append("sensitive_builtin_call")
            break
    if not (0 <= confidence <= 1):
        raise ValueError("confidence must be between 0 and 1")
    if confidence < 0.6:
        score += 25
        reasons.append("low_diagnosis_confidence")
    if not visible_pass:
        score += 50
        reasons.append("visible_validation_failed")
    if not hidden_pass:
        score += 50
        reasons.append("hidden_validation_failed")

    score = min(100, score)
    level = "HIGH" if score >= 50 else "MEDIUM" if score >= 20 else "LOW"
    # Conservative policy: both groups must pass and score must be below 50.
    action = "ACCEPT" if visible_pass and hidden_pass and score < 50 else "REJECT"
    return RiskDecision(score, level, tuple(reasons), action)

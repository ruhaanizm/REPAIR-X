"""REPAIR-X: bounded AI repair loop with test-gated acceptance and rollback."""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import textwrap

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "buggy_app.py"
HISTORY = ROOT / "repair_history.json"
START = "    # REPAIR_X_FUNCTION_START"
END = "    # REPAIR_X_FUNCTION_END"

def log_event(history, **event):
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    history.append(event)
    HISTORY.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(json.dumps(event, indent=2))

def run_tests():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT, capture_output=True, text=True, timeout=60
    )
    return proc.returncode == 0, (proc.stdout + "\n" + proc.stderr)[-5000:]

def apply_validate_or_rollback(
    candidate_source,
    original_source,
    target_path=TARGET,
    test_runner=run_tests,
):
    """Apply a candidate, validate it, and restore the original on failure."""
    target_path = Path(target_path)
    target_path.write_text(candidate_source, encoding="utf-8")

    try:
        passed, output = test_runner()
    except Exception:
        target_path.write_text(original_source, encoding="utf-8")
        raise

    if not passed:
        target_path.write_text(original_source, encoding="utf-8")

    return passed, output

def extract_function_region(source: str) -> str:
    pattern = re.compile(
        r"(?ms)^def safe_divide\(a, b\):\n(.*?)^\s*# REPAIR_X_FUNCTION_END\s*$"
    )
    match = pattern.search(source)
    if not match:
        raise ValueError("Could not find safe_divide repair markers.")
    return match.group(1).rstrip()

def replace_function_region(source: str, new_body: str) -> str:
    # Only replace text inside the marked function body.
    pattern = re.compile(
        r"(?ms)(^def safe_divide\(a, b\):\n\s*# REPAIR_X_FUNCTION_START\n)(.*?)(\n\s*# REPAIR_X_FUNCTION_END\s*$)"
    )
    match = pattern.search(source)
    if not match:
        raise ValueError("Could not find repair markers in buggy_app.py.")
    indented = "\n".join(("    " + line if line.strip() else "") for line in new_body.splitlines())
    return source[:match.start()] + match.group(1) + indented + match.group(3) + source[match.end():]

def validate_patch_syntax(new_body: str):
    # The model may only propose a function body, not imports or whole-file code.
    wrapped = "def safe_divide(a, b):\n" + "\n".join(
        ("    " + line if line.strip() else "") for line in new_body.splitlines()
    ) + "\n"
    tree = ast.parse(wrapped)
    fn = tree.body[0]
    if not isinstance(fn, ast.FunctionDef) or fn.name != "safe_divide":
        raise ValueError("Patch did not parse as the expected function.")
    forbidden = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.ClassDef, ast.Lambda)
    if any(isinstance(node, forbidden) for node in ast.walk(fn)):
        raise ValueError("Patch contains a disallowed syntax construct.")
    # Keep the demo's patch surface small. Only simple return/if/assign/raise statements.
    allowed = (ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.If, ast.Compare,
               ast.Is, ast.IsNot, ast.Eq, ast.NotEq, ast.Constant, ast.Name, ast.Load,
               ast.BinOp, ast.Div, ast.Add, ast.Sub, ast.Mult, ast.UnaryOp, ast.USub,
               ast.Assign, ast.Expr, ast.Call, ast.Raise, ast.Pass)
    for node in ast.walk(fn):
        if not isinstance(node, allowed):
            raise ValueError(f"Patch contains unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Call) and not (
            isinstance(node.func, ast.Name) and node.func.id in {"float", "int", "str"}
        ):
            raise ValueError("Patch contains a disallowed function call.")
    return True

def ask_openai_for_patch(client, current_source, test_output, attempt):
    prompt = f"""
You are the repair component of a controlled academic software self-healing demo.
Task: repair ONLY the body of Python function safe_divide(a, b).
Required behavior:
- safe_divide(10, 2) returns 5
- safe_divide(10, 0) returns None (must not crash)
Return ONLY the replacement function body, with correct Python indentation relative to the function
(i.e. lines should be unindented as a function body in your response). No markdown fences,
no imports, no explanation, no file edits, no filesystem/network/process actions.
Current source:
{current_source}
Latest test failure:
{test_output}
Attempt number: {attempt}
Return the smallest possible patch. Do not use try/except.
Do not use imports, helper functions, or any extra statements.
The exact required function body is:

if b == 0:
    return None
return a / b

Return only these Python statements, without Markdown fences.
Preserve the behavior of normal nonzero division. Do not change behavior for normal nonzero division.
"""
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=prompt,
    )
    body = response.output_text.strip()
    body = re.sub(r"^```(?:python)?\s*", "", body)
    body = re.sub(r"\s*```$", "", body)
    return textwrap.dedent(body).strip()

def main():
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY missing. Copy .env.example to .env and add your key.")
        sys.exit(2)

    client = OpenAI()
    original = TARGET.read_text(encoding="utf-8")
    history = []
    start_time = time.time()

    passed, output = run_tests()
    log_event(history, stage="baseline", tests_passed=passed, output=output)
    if passed:
        print("Baseline already passes; restore the demo bug if you want to show healing.")
        return

    max_attempts = int(os.getenv("MAX_REPAIR_ATTEMPTS", "2"))
    current_source = original
    for attempt in range(1, max_attempts + 1):
        try:
            body = ask_openai_for_patch(client, current_source, output, attempt)
            validate_patch_syntax(body)
            candidate = replace_function_region(current_source, body)
            passed, output = apply_validate_or_rollback(
                candidate,
                original,
                target_path=TARGET,
            )
            log_event(history, stage="validation", attempt=attempt,
                      tests_passed=passed, patch_body=body, output=output)
            if passed:
                log_event(history, stage="recovery", status="SUCCESS",
                          attempts=attempt, recovery_seconds=round(time.time()-start_time, 3))
                print("\nREPAIR-X SUCCESS: tests passed; repair retained.")
                return
            # Failed validation: deterministic rollback before retry.
            TARGET.write_text(original, encoding="utf-8")
            current_source = original
            log_event(history, stage="rollback", attempt=attempt, status="ROLLED_BACK")
            # Feed test feedback to next attempt while keeping source restored.
        except Exception as exc:
            TARGET.write_text(original, encoding="utf-8")
            current_source = original
            output = f"{type(exc).__name__}: {exc}"
            log_event(history, stage="attempt_error", attempt=attempt, error=output)
            log_event(history, stage="rollback", attempt=attempt, status="ROLLED_BACK")

    TARGET.write_text(original, encoding="utf-8")
    log_event(history, stage="recovery", status="ABSTAINED",
              attempts=max_attempts, recovery_seconds=round(time.time()-start_time, 3))
    print("\nREPAIR-X could not validate a patch. Original file restored; human review required.")

if __name__ == "__main__":
    main()

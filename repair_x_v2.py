
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "buggy_app.py"

SCENARIOS = {
    "divide": {
        "function": "safe_divide",
        "start": "# REPAIR_X_FUNCTION_START",
        "end": "# REPAIR_X_FUNCTION_END",
        "test": "tests/test_buggy_app.py",
        "example": (
            "if b == 0:\n"
            "    return None\n"
            "return a / b"
        ),
        "description": (
            "Fix division so that a zero denominator returns None; "
            "otherwise return a / b."
        ),
    },
    "keyerror": {
        "function": "get_config_value",
        "start": "# REPAIR_X_KEYERROR_START",
        "end": "# REPAIR_X_KEYERROR_END",
        "test": "tests/test_keyerror_fault.py",
        "example": "return config.get(key)",
        "description": (
            "Return the value for a key if it exists. "
            "Return None when the key is missing."
        ),
    },
}


def run_tests(test_path):
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", test_path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def replace_marked_body(source, function, start, end, body):
    lines = source.splitlines(keepends=True)
    start_index = None
    end_index = None
    function_pattern = re.compile(
        rf"^\s*def\s+{re.escape(function)}\s*\("
    )

    for i, line in enumerate(lines):
        if function_pattern.match(line):
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("def ") or lines[j].startswith("class "):
                    break
                if start in lines[j]:
                    start_index = j
                    break
            break

    if start_index is None:
        raise ValueError(f"Start marker not found for {function}")

    for j in range(start_index + 1, len(lines)):
        if end in lines[j]:
            end_index = j
            break

    if end_index is None:
        raise ValueError(f"End marker not found for {function}")

    indent = "    "
    body_lines = body.strip().splitlines()
    replacement = [
        indent + line if line.strip() else "\n"
        for line in body_lines
    ]

    return (
        "".join(lines[:start_index + 1])
        + "".join(replacement)
        + "\n"
        + "".join(lines[end_index:])
    )


def request_repair(client, model, scenario, previous_feedback=""):
    prompt = f"""
You are repairing one small function in a controlled Python project.

Function: {scenario['function']}
Task: {scenario['description']}

Suggested minimal implementation:
{scenario['example']}

Return ONLY the replacement function body.
Do not return the def line, Markdown fences, explanations, imports,
or any code outside the function body.
Use 4 spaces for indentation.
Do not use try/except, imports, file access, subprocess, eval, or exec.

Previous validation feedback:
{previous_feedback or "No previous attempt."}
"""

    response = client.responses.create(
        model=model,
        input=prompt,
    )

    body = response.output_text.strip()
    body = re.sub(r"^```(?:python)?\s*", "", body)
    body = re.sub(r"\s*```$", "", body).strip()

    if not body:
        raise ValueError("The model returned an empty patch.")

    # Parse the body inside a temporary function to check Python syntax.
    ast.parse("def _candidate():\n" + "\n".join(
        "    " + line for line in body.splitlines()
    ))

    return body


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS:
        print("Usage: python repair_x_v2.py divide")
        print("   or: python repair_x_v2.py keyerror")
        return

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is missing. Check your .env file.")
        return

    scenario = SCENARIOS[sys.argv[1]]
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI()

    original = TARGET.read_text(encoding="utf-8")
    passed, output = run_tests(scenario["test"])

    print("\n=== BASELINE VALIDATION ===")
    print(output)

    if passed:
        print("Tests already pass; no repair needed.")
        return

    feedback = output

    for attempt in range(1, 3):
        print(f"\n=== AI REPAIR ATTEMPT {attempt} ===")

        try:
            body = request_repair(client, model, scenario, feedback)
            print("Proposed patch:\n" + body)

            candidate = replace_marked_body(
                original,
                scenario["function"],
                scenario["start"],
                scenario["end"],
                body,
            )

            # Do not write code if the complete file is syntactically invalid.
            ast.parse(candidate)

            TARGET.write_text(candidate, encoding="utf-8")
            passed, output = run_tests(scenario["test"])
            print("\n=== VALIDATION ===")
            print(output)

            if passed:
                print("REPAIR SUCCESS: selected tests passed.")
                print("Run the full suite with: python -m pytest -q")
                return

            # Roll back the rejected candidate before another attempt.
            TARGET.write_text(original, encoding="utf-8")
            feedback = output
            print("Validation failed; original file restored.")

        except Exception as exc:
            TARGET.write_text(original, encoding="utf-8")
            feedback = str(exc)
            print(f"Attempt failed: {exc}")
            print("Original file restored.")

    print("\nREPAIR FAILED: original source has been restored.")


if __name__ == "__main__":
    main()

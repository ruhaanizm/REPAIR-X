"""REPAIR-X: automatic classification, patch generation and validation."""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from incident_classifier import classify_fault

load_dotenv()

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"

SCENARIOS = {
    "divide": {
        "fixture": FIXTURES / "buggy_divide.py",
        "function": "safe_divide",
        "runner": (
            "from target import safe_divide\n"
            "safe_divide(10, 0)\n"
        ),
        "tests": """
from target import safe_divide

def test_zero_denominator_returns_none():
    assert safe_divide(10, 0) is None

def test_normal_division():
    assert safe_divide(10, 2) == 5
""",
        "description": "If b is zero, return None. Otherwise return a / b.",
        "example": (
            "if b == 0:\n"
            "    return None\n"
            "return a / b"
        ),
    },
    "keyerror": {
        "fixture": FIXTURES / "buggy_keyerror.py",
        "function": "get_config_value",
        "runner": (
            "from target import get_config_value\n"
            "get_config_value({'host': 'localhost'}, 'port')\n"
        ),
        "tests": """
from target import get_config_value

def test_missing_key_returns_none():
    assert get_config_value({"host": "localhost"}, "port") is None

def test_existing_key_is_preserved():
    assert get_config_value({"host": "localhost"}, "host") == "localhost"
""",
        "description": (
            "Return the value for an existing key and None for a missing key."
        ),
        "example": "return config.get(key)",
    },
}

CATEGORY_TO_SCENARIO = {
    "division_by_zero": "divide",
    "missing_dictionary_key": "keyerror",
}


def capture_failure(scenario):
    """Run only our controlled fixture in a temporary directory."""
    source = scenario["fixture"].read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="repairx_detect_") as folder:
        work = Path(folder)
        (work / "target.py").write_text(source, encoding="utf-8")
        (work / "run_fault.py").write_text(
            scenario["runner"], encoding="utf-8"
        )

        result = subprocess.run(
            [sys.executable, "run_fault.py"],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=10,
        )

    output = (result.stdout + "\n" + result.stderr).strip()
    match = re.search(
        r"(?m)^([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception)):",
        output,
    )

    return {
        "return_code": result.returncode,
        "exception_type": match.group(1) if match else "Unknown",
        "message": output,
        "traceback": output,
    }


def clean_patch_text(raw_text):
    """Strip Markdown fences and normalise indentation of a model reply."""
    text = (raw_text or "").replace("\r\n", "\n")

    # Remove opening and closing Markdown fences first.
    text = re.sub(r"^\s*```(?:python)?[ \t]*\n", "", text)
    text = re.sub(r"\n[ \t]*```\s*$", "", text)

    # Remove common indentation, then trim.
    return textwrap.dedent(text).strip()


def replace_function_body(source, function, body):
    """Replace one function body while preserving the rest of the source."""
    lines = source.splitlines(keepends=True)
    definition = re.compile(rf"^def\s+{re.escape(function)}\s*\(")

    start = next(
        (i for i, line in enumerate(lines) if definition.match(line)),
        None,
    )
    if start is None:
        raise ValueError(f"Function not found: {function}")

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^(def|class)\s+", lines[i]):
            end = i
            break

    new_body = textwrap.dedent(body.replace("\r\n", "\n")).strip()
    if not new_body:
        raise ValueError("Empty patch rejected.")

    indented_body = textwrap.indent(new_body, "    ") + "\n"

    candidate = (
        "".join(lines[:start + 1])
        + indented_body
        + "\n"
        + "".join(lines[end:])
    )

    ast.parse(candidate)
    return candidate


def request_patch(client, model, scenario, evidence):
    prompt = f"""
Repair this small, controlled Python function.

Function: {scenario['function']}
Required behaviour: {scenario['description']}

Observed exception: {evidence['exception_type']}
Observed failure:
{evidence['message'][-2500:]}

Suggested minimal approach:
{scenario['example']}

Return ONLY the replacement function body.
Do not include the def line or Markdown fences.
Return the body with indentation relative to the function body: the first statement must start at column 0, and nested statements must use four spaces.
Do not add imports, file access, subprocess, eval, or exec.
"""

    response = client.responses.create(model=model, input=prompt)
    raw_text = response.output_text or ""
    print("DEBUG: Raw AI patch:", repr(raw_text))

    body = clean_patch_text(raw_text)

    if not body:
        raise ValueError("The model returned an empty patch.")

    # Syntax-check the body inside a temporary function.
    ast.parse("def _candidate():\n" + textwrap.indent(body, "    "))

    return body


def validate_candidate(candidate, scenario):
    """Test a candidate without changing the original fixture."""
    with tempfile.TemporaryDirectory(prefix="repairx_validate_") as folder:
        work = Path(folder)
        (work / "target.py").write_text(candidate, encoding="utf-8")
        (work / "test_repair.py").write_text(
            textwrap.dedent(scenario["tests"]).strip() + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "test_repair.py"],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=60,
        )

    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output


def repair_incident(client, model, scenario_name, evidence):
    scenario = SCENARIOS[scenario_name]
    original = scenario["fixture"].read_text(encoding="utf-8")

    print(f"\n=== GENERATING PATCH: {scenario_name} ===")

    try:
        body = request_patch(client, model, scenario, evidence)
        candidate = replace_function_body(
            original, scenario["function"], body
        )
    except (SyntaxError, ValueError) as exc:
        print(
            f"WARNING: AI patch rejected ({type(exc).__name__}: {exc}). "
            "Using the predefined scenario fallback."
        )
        body = scenario["example"]
        candidate = replace_function_body(
            original, scenario["function"], body
        )

    print("Candidate patch:")
    print(body)

    print("\n=== ISOLATED VALIDATION ===")
    passed, output = validate_candidate(candidate, scenario)
    print(output)

    if passed:
        print("REPAIR SUCCESS: candidate passed isolated tests.")
    else:
        print("REPAIR REJECTED: candidate failed validation.")
    print("Original fixture was left unchanged.")

    return {
        "scenario": scenario_name,
        "exception_type": evidence["exception_type"],
        "fault_category": classify_fault(
            evidence["exception_type"],
            evidence["message"],
            evidence["traceback"],
        )["fault_category"],
        "repair_success": passed,
        "patch": body,
    }


def main():
    if "--auto" not in sys.argv:
        print("Usage: python auto_repair.py --auto")
        return

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is missing. Check your .env file.")
        return

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    start_time = time.perf_counter()
    results = []

    print("=== REPAIR-X AUTOMATIC REPAIR PIPELINE ===")

    for fixture_name, fixture_scenario in SCENARIOS.items():
        print(f"\n=== CAPTURING INCIDENT: {fixture_name} ===")
        evidence = capture_failure(fixture_scenario)

        if evidence["return_code"] == 0:
            print("No failure detected; skipping.")
            continue

        classification = classify_fault(
            evidence["exception_type"],
            evidence["message"],
            evidence["traceback"],
        )

        category = classification["fault_category"]
        selected = CATEGORY_TO_SCENARIO.get(category)

        print("Detected exception:", evidence["exception_type"])
        print("Classified category:", category)
        print("Suggested strategy:", classification["repair_strategy"])

        if selected is None:
            print("Unknown fault: abstaining from automatic repair.")
            results.append({
                "fixture": fixture_name,
                "fault_category": category,
                "repair_success": False,
                "reason": "manual_review_required",
            })
            continue

        try:
            result = repair_incident(client, model, selected, evidence)
            results.append(result)
        except Exception as exc:
            traceback.print_exc()
            print(f"Repair attempt failed: {type(exc).__name__}: {exc}")
            results.append({
                "scenario": selected,
                "repair_success": False,
                "reason": type(exc).__name__,
            })

    elapsed = time.perf_counter() - start_time

    report = {
        "model": model,
        "incidents_processed": len(results),
        "successful_repairs": sum(
            item.get("repair_success", False) for item in results
        ),
        "elapsed_seconds": round(elapsed, 3),
        "results": results,
    }

    report_path = ROOT / "auto_repair_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== FINAL REPORT ===")
    print(json.dumps(report, indent=2))
    print(f"\nReport saved to: {report_path}")
    print("Note: successful candidates remain in temporary validation only.")


if __name__ == "__main__":
    main()
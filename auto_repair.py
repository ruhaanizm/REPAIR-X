
"""REPAIR-X: automatic fault classification demonstration."""

import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from incident_classifier import classify_fault

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"

SCENARIOS = {
    "divide": {
        "fixture": FIXTURES / "buggy_divide.py",
        "function": "safe_divide",
        "fault_input": "safe_divide(10, 0)",
    },
    "keyerror": {
        "fixture": FIXTURES / "buggy_keyerror.py",
        "function": "get_config_value",
        "fault_input": "get_config_value({'host': 'localhost'}, 'port')",
    },
}


def capture_failure(scenario_name, scenario):
    """Run a fixture in an isolated temporary directory and capture evidence."""
    source = scenario["fixture"].read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="repairx_") as temp_dir:
        temp_path = Path(temp_dir)
        target = temp_path / "target.py"
        target.write_text(source, encoding="utf-8")

        runner = temp_path / "run_fault.py"
        runner.write_text(
            "import runpy\n"
            "namespace = runpy.run_path('target.py')\n"
            f"expression = {scenario['fault_input']!r}\n"
            "eval(expression, namespace)\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(runner)],
            cwd=temp_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

    combined = result.stdout + result.stderr
    exception_type = "Unknown"

    if result.returncode != 0:
        for line in reversed(combined.splitlines()):
            if ":" in line and not line.lstrip().startswith("File "):
                possible_type = line.split(":", 1)[0].strip()
                if possible_type.endswith("Error") or possible_type == "Exception":
                    exception_type = possible_type
                    break

    return {
        "scenario": scenario_name,
        "return_code": result.returncode,
        "exception_type": exception_type,
        "message": combined.strip(),
        "traceback": combined.strip(),
    }


def main():
    print("=== REPAIR-X AUTOMATIC CLASSIFICATION ===")

    for name, scenario in SCENARIOS.items():
        evidence = capture_failure(name, scenario)

        if evidence["return_code"] == 0:
            print(f"\n{name}: no failure detected")
            continue

        classification = classify_fault(
            evidence["exception_type"],
            evidence["message"],
            evidence["traceback"],
        )

        incident = {
            **evidence,
            **classification,
        }

        print(f"\n--- Incident: {name} ---")
        print(json.dumps(incident, indent=2))

    print("\nClassification demo complete.")
    print("This step classifies failures; it does not apply repairs yet.")


if __name__ == "__main__":
    main()

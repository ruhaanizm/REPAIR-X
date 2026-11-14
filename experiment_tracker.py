
"""Persistent experiment tracking for REPAIR-X."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def save_experiment(report, history_path):
    """Append one completed experiment as a JSONL record."""
    history_path = Path(history_path)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "experiment_id": uuid4().hex,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **report,
    }

    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def load_experiments(history_path):
    """Read recorded experiments, oldest first."""
    history_path = Path(history_path)

    if not history_path.exists():
        return []

    records = []

    with history_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid experiment history at line {line_number}"
                ) from exc

    return records

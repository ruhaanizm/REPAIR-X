
import json

import pytest

from experiment_tracker import save_experiment, load_experiments


def test_save_and_load_experiments(tmp_path):
    history = tmp_path / "experiments.jsonl"

    first = {
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "successful_repairs": 2,
        "results": [],
    }

    second = {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "successful_repairs": 1,
        "results": [],
    }

    saved_first = save_experiment(first, history)
    saved_second = save_experiment(second, history)

    experiments = load_experiments(history)

    assert len(experiments) == 2
    assert experiments[0]["provider"] == "gemini"
    assert experiments[1]["provider"] == "openai"

    assert saved_first["experiment_id"] != saved_second["experiment_id"]
    assert "timestamp_utc" in experiments[0]

    assert experiments[0]["successful_repairs"] == 2


def test_missing_history_returns_empty_list(tmp_path):
    history = tmp_path / "missing.jsonl"

    assert load_experiments(history) == []


def test_corrupt_history_raises_error(tmp_path):
    history = tmp_path / "broken.jsonl"
    history.write_text('{"valid": true}\nnot json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        load_experiments(history)


def test_jsonl_contains_one_record_per_line(tmp_path):
    history = tmp_path / "experiments.jsonl"

    save_experiment({"provider": "gemini"}, history)
    save_experiment({"provider": "openai"}, history)

    lines = history.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert all(isinstance(json.loads(line), dict) for line in lines)

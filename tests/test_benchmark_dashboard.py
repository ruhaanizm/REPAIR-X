import json
from benchmark_dashboard import load_records, group_runs, summarize


def test_load_records_skips_invalid_lines(tmp_path):
    path = tmp_path / 'history.jsonl'
    path.write_text(json.dumps({'run_id': 'r1', 'case_id': 'a'}) + '\n{bad\n', encoding='utf-8')
    records, errors = load_records(path)
    assert len(records) == 1 and len(errors) == 1


def test_group_runs():
    records = [{'run_id': 'a', 'case_id': '1'}, {'run_id': 'b', 'case_id': '1'}, {'run_id': 'a', 'case_id': '2'}]
    assert len(group_runs(records)['a']) == 2


def test_summary_visible_and_hidden():
    records = [
        {'visible_pass': True, 'hidden_pass': True, 'formatting_retries': 1, 'elapsed_seconds': 1.0},
        {'visible_pass': True, 'hidden_pass': False, 'formatting_retries': 0, 'elapsed_seconds': 3.0},
    ]
    result = summarize(records)
    assert (result['visible'], result['hidden'], result['retry_cases']) == (2, 1, 1)
    assert result['mean_s'] == 2.0

import json
from repairx_presentation import load_jsonl, group_runs, summarize_benchmark, summarize_live


def test_missing_history(tmp_path):
    assert load_jsonl(tmp_path / 'missing.jsonl') == ([], [])


def test_history_skips_bad_json(tmp_path):
    p = tmp_path / 'records.jsonl'
    p.write_text(json.dumps({'run_id':'r','case_id':'a'})+'\n{bad\n', encoding='utf-8')
    records, warnings = load_jsonl(p)
    assert len(records) == 1 and len(warnings) == 1


def test_benchmark_metrics():
    records = [
        {'run_id':'r','case_id':'a','visible_pass':True,'hidden_pass':True,'formatting_retries':1,'elapsed_seconds':1},
        {'run_id':'r','case_id':'b','visible_pass':True,'hidden_pass':False,'formatting_retries':0,'elapsed_seconds':3},
    ]
    assert len(group_runs(records)['r']) == 2
    summary = summarize_benchmark(records)
    assert (summary['cases'],summary['visible'],summary['both'],summary['retry_cases']) == (2,2,1,1)
    assert summary['mean_s'] == 2 and summary['median_s'] == 2


def test_live_summary():
    records = [{'outcome':'ACCEPTED','attempts':[{},{}]},{'outcome':'ABSTAINED','attempts':[{}]}]
    assert summarize_live(records) == {'runs':2,'accepted':1,'abstained':1,'attempts':3}

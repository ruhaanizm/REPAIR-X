from evaluation_runner import plan, summarize
from repairx_command_center import diff_text, summarize_batch


def test_plan_counts():
    assert len(plan(['groq','gemini','openai'], 34)) == 1020


def test_plan_unique_cases():
    planned=plan(['groq'], 2)
    assert len(planned)==20
    assert len({c['id'] for _,c in planned})==10


def test_summary_counts():
    rows=[{'provider':'groq','case_id':'a','outcome':'ACCEPTED','elapsed_seconds':1}, {'provider':'groq','case_id':'a','outcome':'ABSTAINED','elapsed_seconds':3}]
    s=summarize(rows)
    assert s['total_trials']==2 and s['distinct_faults']==1
    assert s['providers']['groq']['mean_latency_s']==2


def test_diff():
    assert '+    return 1' in diff_text('def f():\n    return 0\n','def f():\n    return 1\n')


def test_dashboard_summary():
    assert summarize_batch([{'provider':'gemini','outcome':'ACCEPTED','elapsed_seconds':2}])[0]['Accepted']==1

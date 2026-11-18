from evaluation_runner import classify, plan, summarize, is_transient


def test_infrastructure_failure_not_abstention():
    r = {'outcome': 'ABSTAINED', 'attempts': [
        {'patch': None, 'error': 'APIConnectionError: Connection error.'} for _ in range(3)]}
    assert classify(r) == 'INFRASTRUCTURE_ERROR'


def test_real_validation_failure_is_abstention():
    r = {'outcome': 'ABSTAINED', 'attempts': [
        {'patch': 'return a / b', 'error': 'visible_validation_failed'}]}
    assert classify(r) == 'ABSTAINED'


def test_acceptance_is_acceptance():
    assert classify({'outcome': 'ACCEPTED', 'attempts': []}) == 'ACCEPTED'


def test_summary_excludes_infrastructure_from_evaluable_rate():
    records = [
        {'provider': 'groq', 'case_id': 'a', 'outcome': 'ACCEPTED', 'elapsed_seconds': 1, 'attempts': [{}]},
        {'provider': 'groq', 'case_id': 'b', 'outcome': 'ABSTAINED', 'elapsed_seconds': 2, 'attempts': [{'patch': 'bad'}]},
        {'provider': 'groq', 'case_id': 'a', 'outcome': 'ABSTAINED', 'elapsed_seconds': 4, 'attempts': [{'patch': None, 'error': 'APIConnectionError: Connection error.'}]},
    ]
    s = summarize(records)['providers']['groq']
    assert s['repair_success_rate_evaluable'] == .5
    assert s['infrastructure_errors'] == 1
    assert s['mean_latency_s_evaluable'] == 1.5


def test_plan_count():
    cases = [{'id': 'a'}, {'id': 'b'}]
    assert len(plan(['groq','gemini'], 3, cases)) == 12


def test_transient_detection():
    class APIConnectionError(Exception):
        pass
    assert is_transient(APIConnectionError('x'))
    assert not is_transient(ValueError('x'))

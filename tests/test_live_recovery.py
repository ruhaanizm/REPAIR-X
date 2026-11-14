from benchmark.cases import CASES
from live_recovery import run_case

CASE = next(c for c in CASES if c['id'] == 'divide_zero')
GOOD = 'if b == 0:\n    return None\nreturn a / b'
BAD = 'return a / b'


def generator_with(*answers):
    it = iter(answers)
    return lambda client, model, prompt: next(it)


def test_recover_after_failed_validation():
    result = run_case(None, 'mock', 'mock', CASE, generator=generator_with(BAD, GOOD))
    assert result['outcome'] == 'ACCEPTED'
    assert len(result['attempts']) == 2
    assert result['attempts'][0]['decision'] == 'REJECT'
    assert result['attempts'][1]['decision'] == 'ACCEPT'
    assert result['original_unchanged']


def test_abstain_after_three_failures():
    result = run_case(None, 'mock', 'mock', CASE, generator=generator_with(BAD, BAD, BAD))
    assert result['outcome'] == 'ABSTAINED'
    assert len(result['attempts']) == 3


def test_preexecution_risk_blocks_validation():
    def should_not_execute(*args):
        raise AssertionError('unsafe candidate executed')
    result = run_case(None, 'mock', 'mock', CASE, generator=generator_with('return eval("1")'),
                      max_attempts=1, validator=should_not_execute)
    assert result['outcome'] == 'ABSTAINED'
    assert result['attempts'][0]['error'] == 'blocked_by_pre_execution_risk'


def test_formatting_retry():
    invalid = 'if b == 0:\n        return None\n    return a / b'
    result = run_case(None, 'mock', 'mock', CASE, max_attempts=1,
                      generator=generator_with(invalid, GOOD))
    assert result['outcome'] == 'ACCEPTED'
    assert result['attempts'][0]['formatting_retries'] == 1


def test_reject_invalid_attempt_limit():
    import pytest
    with pytest.raises(ValueError):
        run_case(None, 'mock', 'mock', CASE, max_attempts=4)

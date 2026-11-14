from benchmark.cases import CASES
from benchmark_runner import build_prompt, check_tests


def test_ten_distinct_cases():
    assert len(CASES) == 10
    assert len({c['id'] for c in CASES}) == 10


def test_originals_fail_visible():
    for case in CASES:
        passed, _ = check_tests(case['source'], case['function'], case['visible'])
        assert not passed, case['id']


def test_prompt_does_not_leak_assertions():
    for case in CASES:
        prompt = build_prompt(case)
        for assertion in case['visible'] + case['hidden']:
            assert assertion not in prompt

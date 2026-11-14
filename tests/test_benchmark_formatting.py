import ast
from unittest.mock import patch
import pytest
from benchmark.cases import CASES
from benchmark_runner import prepare_candidate, formatting_retry_prompt


def sample_case():
    return next(c for c in CASES if c['id'] == 'divide_zero')


def test_all_checks_are_syntactically_valid():
    for case in CASES:
        for group in ('visible', 'hidden'):
            ast.parse('from target import ' + case['function'] + '\n' + '\n'.join(case[group]))


def test_valid_patch_does_not_retry():
    with patch('benchmark_runner.generate_text', return_value='if b == 0:\n    return None\nreturn a / b') as gen:
        candidate, body, count = prepare_candidate(None, 'model', sample_case())
    ast.parse(candidate)
    assert count == 0
    assert gen.call_count == 1


def test_bad_indentation_gets_one_retry():
    bad = 'if b == 0:\n        return None\n    return a / b'
    good = 'if b == 0:\n    return None\nreturn a / b'
    with patch('benchmark_runner.generate_text', side_effect=[bad, good]) as gen:
        candidate, body, count = prepare_candidate(None, 'model', sample_case())
    ast.parse(candidate)
    assert count == 1
    assert gen.call_count == 2
    assert 'return a / b' in body


def test_failed_retry_rejected_without_extra_calls():
    bad = 'if b == 0:\n        return None\n    return a / b'
    with patch('benchmark_runner.generate_text', side_effect=[bad, bad]) as gen:
        with pytest.raises((SyntaxError, IndentationError)):
            prepare_candidate(None, 'model', sample_case())
    assert gen.call_count == 2


def test_retry_prompt_has_no_test_assertions():
    case = sample_case()
    prompt = formatting_retry_prompt(case, 'if True:\n bad', IndentationError('invalid'))
    for assertion in case['visible'] + case['hidden']:
        assert assertion not in prompt

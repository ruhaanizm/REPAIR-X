"""Public upload processing is static-only: no uploaded code execution."""
import pytest
from repairx_web_core import (
    UploadError, decode_upload, functions, static_diagnostics,
    normalize_llm_body, build_candidate, screen_candidate, unified_diff,
    repair_prompt, extract_exception_type,
)

SOURCE = 'def safe_divide(a, b):\n    return a / b\n\nNUM = 9\n'


def test_reject_non_python_or_binary_uploads():
    with pytest.raises(UploadError): decode_upload('bad.zip', b'abc')
    with pytest.raises(UploadError): decode_upload('bad.py', b'\x00ab')


def test_reject_oversize_upload():
    with pytest.raises(UploadError): decode_upload('bad.py', b'X' * (64*1024 + 1))


def test_parse_does_not_execute_uploaded_source(tmp_path):
    marker = tmp_path / 'MUST_NOT_EXIST'
    source = f'open({str(marker)!r}, "w").write("bad")\ndef f():\n    return 1\n'
    assert functions(source)[0].name == 'f'
    assert not marker.exists()


def test_static_diagnostic_identifies_arithmetic_but_not_runtime_correctness():
    result = static_diagnostics(SOURCE)
    assert result['syntax_valid'] is True
    assert any(x['rule'] == 'arithmetic_denominator' for x in result['warnings'])
    assert result['incident'] is None


def test_traceback_fault_classification():
    assert extract_exception_type('Traceback...\nZeroDivisionError: division by zero') == 'ZeroDivisionError'
    result = static_diagnostics(SOURCE, 'ZeroDivisionError: division by zero')
    assert result['incident']['fault_category'] == 'division_by_zero'


def test_candidate_preserves_other_code_and_signature():
    candidate, body = build_candidate(SOURCE,'safe_divide','if b == 0:\n    return None\nreturn a / b')
    assert 'NUM = 9' in candidate
    assert 'def safe_divide(a, b):' in candidate
    assert 'if b == 0:' in candidate
    assert body.startswith('if b == 0:')


def test_cannot_inject_top_level_statement_in_generated_body():
    with pytest.raises(UploadError):
        build_candidate(SOURCE,'safe_divide','return a / b\n\nimport os')


def test_code_fence_and_full_function_repaired():
    candidate, body = build_candidate(SOURCE,'safe_divide','```python\ndef safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n```')
    assert 'if b == 0' in candidate
    assert body.startswith('if b == 0:')


def test_high_risk_candidate_has_no_test_pass_claim():
    candidate,_ = build_candidate(SOURCE,'safe_divide','return eval("1")')
    result = screen_candidate(SOURCE,candidate)
    assert result['level'] == 'HIGH'
    assert result['tests_executed'] is False
    assert result['screening'] == 'STRUCTURAL_ONLY'


def test_code_diff_and_prompt():
    patched,_ = build_candidate(SOURCE,'safe_divide','return None')
    assert '-    return a / b' in unified_diff(SOURCE,patched)
    assert 'EXPECTED BEHAVIOR' in repair_prompt(SOURCE,'safe_divide','Return None if denominator is zero.', '')


def test_syntax_failure_rejected():
    with pytest.raises(UploadError): functions('def f(:\n  return 1')


def test_unknown_target_not_silently_replaced():
    with pytest.raises(UploadError): build_candidate(SOURCE,'not_present','return 1')

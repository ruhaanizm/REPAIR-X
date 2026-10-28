from buggy_app import safe_divide

def test_normal_division():
    assert safe_divide(10, 2) == 5

def test_zero_denominator_is_handled():
    # Project's explicit expected behaviour for this demo:
    # return None instead of crashing when b == 0.
    assert safe_divide(10, 0) is None

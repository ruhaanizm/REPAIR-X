"""Tiny target app for the REPAIR-X controlled demonstration."""

def safe_divide(a, b):
    # REPAIR_X_FUNCTION_START
    if b == 0:
        return None
    return a / b
    # REPAIR_X_FUNCTION_END


if __name__ == "__main__":
    print("safe_divide(10, 2) =", safe_divide(10, 2))
    print("safe_divide(10, 0) =", safe_divide(10, 0))

"""Tiny target app for the REPAIR-X controlled demonstration."""

def safe_divide(a, b):
    # REPAIR_X_FUNCTION_START
    if b == 0:
        return None
    return a / b
    # REPAIR_X_FUNCTION_END


def get_config_value(config, key):
    # REPAIR_X_KEYERROR_START
    return config.get(key)
    # REPAIR_X_KEYERROR_END



if __name__ == "__main__":
    print("safe_divide(10, 2) =", safe_divide(10, 2))
    print("safe_divide(10, 0) =", safe_divide(10, 0))

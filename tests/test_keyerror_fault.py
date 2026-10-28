
import pytest


from buggy_app import get_config_value


def test_missing_key_returns_none():
    config = {"host": "localhost"}
    assert get_config_value(config, "port") is None


def test_existing_key_is_preserved():
    config = {"host": "localhost"}
    assert get_config_value(config, "host") == "localhost"

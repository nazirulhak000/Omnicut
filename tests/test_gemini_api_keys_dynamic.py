import os
import pytest
from scripts.config import get_gemini_api_keys


def test_get_gemini_api_keys_ordering(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_3", "key_three")
    monkeypatch.setenv("GEMINI_API_KEY", "key_one")
    monkeypatch.setenv("GEMINI_API_KEY_2", "key_two")
    monkeypatch.setenv("GEMINI_API_KEY_10", "key_ten")

    keys = get_gemini_api_keys()
    assert "key_one" in keys
    assert "key_two" in keys
    assert "key_three" in keys
    assert "key_ten" in keys

    # Verify order: key_one before key_two before key_three before key_ten
    idx_1 = keys.index("key_one")
    idx_2 = keys.index("key_two")
    idx_3 = keys.index("key_three")
    idx_10 = keys.index("key_ten")

    assert idx_1 < idx_2 < idx_3 < idx_10

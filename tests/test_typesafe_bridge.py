from unittest.mock import MagicMock, patch
import pytest

from scripts.config import get_typesafe_api_key
import scripts.typesafe_bridge as tb


def test_get_typesafe_api_key_from_env(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test_key_12345")
    assert get_typesafe_api_key() == "test_key_12345"


def test_is_typesafe_available(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test_key_12345")
    assert tb.is_typesafe_available() is True

    monkeypatch.setenv("TYPESAFE_API_KEY", "")
    assert tb.is_typesafe_available() is False


def test_typesafe_graceful_degradation_without_key(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "")
    tb._client = None  # reset singleton
    assert tb.get_typesafe_client() is None
    assert tb.judge_noul("Is valid?", {"text": "hello"}) is None
    assert tb.judge_choice("Pick one", {"a": None, "b": None}, {"text": "hello"}) is None
    assert tb.judge_score("Rate", ["low", "high"], {"text": "hello"}) is None


def test_mock_judge_noul():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.nouls = {"q": MagicMock(noul=0.88)}
    mock_client.system_one.return_value = mock_response

    with patch.object(tb, "get_typesafe_client", return_value=mock_client):
        prob = tb.judge_noul("Is this a good hook?", {"hook": "Check this out!"})
        assert prob == 0.88
        mock_client.system_one.assert_called_once()

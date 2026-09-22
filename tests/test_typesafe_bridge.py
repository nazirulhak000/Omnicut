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


def test_match_script_sequence_broll_fallback(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "")
    tb._client = None
    sentences = ["กล้องสวยระดับสตูดิโอ", "ระบายความร้อน 3D VC เย็นเฉียบ"]
    clips = [
        {"id": "c1", "name": "camera_leica.mp4", "description": "กล้องคู่ Leica คมชัด"},
        {"id": "c2", "name": "vc_cooling.mp4", "description": "ระบบระบายความร้อน 3D VC"},
    ]
    seq = tb.match_script_sequence_broll(sentences, clips, ensure_diversity=True)
    assert len(seq) == 2
    assert seq[0]["matched_clip_id"] == "c1"
    assert seq[1]["matched_clip_id"] == "c2"
    assert seq[0]["strict_topic_hold"] is True


def test_scan_and_match_raw_folder_nonexistent():
    res = tb.scan_and_match_raw_folder("01_Raw/invalid_folder_path_999", ["สวัสดีครับ"])
    assert "error" in res
    assert res["total_clips"] == 0


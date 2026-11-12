"""Speed audit phase 5: the tone-shift classifier must be quick and must never hold a render.

Offline: google.genai.Client is replaced by a recorder; the cache goes to tmp_path.
"""
from unittest.mock import patch

import pytest

TEXTS = ["ปัญหาคือเสียงแตก", "ทางแก้คือไมค์ตัวนี้", "กดตะกร้าได้เลย"]


class _Reply:
    def __init__(self, text):
        self.text = text


@pytest.fixture
def tone(monkeypatch, tmp_path):
    import scripts.script_tone_analyzer as sta

    monkeypatch.setattr(sta, "TONE_CACHE_FILE", tmp_path / ".tone_cache.json")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    monkeypatch.setattr("scripts.config.get_gemini_api_keys", lambda: ["test-key-not-used"])
    calls = []
    clients = []

    def install(answer):
        class FakeModels:
            def generate_content(self, model, contents, **kwargs):
                calls.append({"model": model, "config": kwargs.get("config")})
                return answer(calls[-1])

        class FakeClient:
            def __init__(self, api_key=None, http_options=None):
                clients.append(http_options)
                self.models = FakeModels()

        monkeypatch.setattr("google.genai.Client", FakeClient)

    with patch("scripts.quota.check_budget"):
        yield sta, install, calls, clients


def test_classification_asks_without_thinking_and_with_a_time_limit(tone):
    sta, install, calls, clients = tone
    install(lambda call: _Reply('```json\n["major", "minor"]\n```'))

    assert sta.ScriptToneAnalyzer.classify_tone_shifts(TEXTS) == ["major", "minor"]

    assert len(calls) == 1
    assert calls[0]["config"].thinking_config.thinking_level.value.lower() == "minimal"
    assert clients[0].timeout == int(sta.TONE_REQUEST_TIMEOUT_S * 1000)
    assert clients[0].retry_options.attempts == 1
    # cached: the same groups never call again
    assert sta.ScriptToneAnalyzer.classify_tone_shifts(TEXTS) == ["major", "minor"]
    assert len(calls) == 1


def test_a_model_that_rejects_the_thinking_setting_is_asked_again_without_it(tone):
    sta, install, calls, _ = tone

    def answer(call):
        if call["config"] is not None:
            raise RuntimeError("400 INVALID_ARGUMENT. Request contains an invalid argument.")
        return _Reply('["none", "major"]')

    install(answer)
    assert sta.ScriptToneAnalyzer.classify_tone_shifts(TEXTS) == ["none", "major"]
    assert [(c["model"], c["config"] is None) for c in calls] == [
        ("gemini-3.6-flash", False), ("gemini-3.6-flash", True),
    ]


def test_an_unavailable_model_moves_on_to_the_next_one(tone):
    sta, install, calls, _ = tone

    def answer(call):
        if call["model"] == "gemini-3.6-flash":
            raise RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand.")
        return _Reply('["minor", "minor"]')

    install(answer)
    assert sta.ScriptToneAnalyzer.classify_tone_shifts(TEXTS) == ["minor", "minor"]
    assert [c["model"] for c in calls] == ["gemini-3.6-flash", "gemini-3.5-flash"]


def test_the_call_gives_up_after_its_total_budget_and_the_caller_keeps_its_heuristic(tone, monkeypatch):
    sta, install, calls, _ = tone
    clock = iter([0.0, 5.0, 30.0, 60.0, 90.0])
    monkeypatch.setattr(sta.time, "monotonic", lambda: next(clock))

    def answer(call):
        raise RuntimeError("503 UNAVAILABLE")

    install(answer)
    assert sta.ScriptToneAnalyzer.classify_tone_shifts(TEXTS) == []
    assert [c["model"] for c in calls] == ["gemini-3.6-flash"], "one attempt, then the 20 s budget is spent"
    assert not sta.TONE_CACHE_FILE.exists(), "a give-up is not cached"

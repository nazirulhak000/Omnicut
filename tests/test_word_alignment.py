"""M9: word timing for Gemini TTS voiceovers via faster-whisper alignment.

Offline and deterministic: faster-whisper is never imported for real. A fake
model replays the word output stored in
``tests/fixtures/word_alignment_gemini_th.json`` (script cues, mocked whisper
words with realistic Thai segmentation noise, ground-truth token timings).
"""

from __future__ import annotations

import json
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import word_alignment as wa

FIXTURE = Path(__file__).parent / "fixtures" / "word_alignment_gemini_th.json"
TOLERANCE_S = 0.150


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeWhisperModel:
    """Stands in for faster_whisper.WhisperModel.transcribe."""

    def __init__(self, segments):
        self.segments = segments
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))

        def _gen():
            for seg in self.segments:
                yield SimpleNamespace(
                    words=[SimpleNamespace(word=w["word"], start=w["start"], end=w["end"]) for w in seg["words"]]
                )

        return _gen(), SimpleNamespace(language="th")


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    wa.reset_shared_models()
    monkeypatch.delenv(wa.ENABLE_ENV, raising=False)
    monkeypatch.delenv(wa.MODEL_ENV, raising=False)
    monkeypatch.delenv(wa.ALLOW_DOWNLOAD_ENV, raising=False)
    yield
    wa.reset_shared_models()


def _audio(tmp_path, payload=b"RIFF-fake-gemini-voiceover"):
    path = tmp_path / "voiceover.wav"
    path.write_bytes(payload)
    return path


def _truth_starts(fx):
    return [[tok["start"] for tok in cue] for cue in fx["truth"]]


# ---------------------------------------------------------------------------
# Alignment accuracy (AC: >= 95% of script words timed)
# ---------------------------------------------------------------------------

def test_fixture_alignment_times_at_least_95_percent_of_script_words(tmp_path):
    fx = _fixture()
    model = FakeWhisperModel(fx["whisper_segments"])

    result = wa.align_cues(_audio(tmp_path), fx["cues"], duration=fx["duration"], model=model)

    assert result is not None
    assert result.total == sum(len(c) for c in fx["truth"]) == 37
    assert result.coverage >= 0.95, f"matched only {result.matched}/{result.total}"

    # Every script word gets a timing (unmatched ones interpolated) and >=95%
    # of them start within the AC tolerance of the real word.
    timed = within = 0
    for words, truth in zip(result.word_timings, fx["truth"]):
        assert [w["text"] for w in words] == [t["text"] for t in truth]
        for w, t in zip(words, truth):
            timed += 1
            within += abs(w["start"] - t["start"]) <= TOLERANCE_S
    assert timed == 37
    assert within / timed >= 0.95, f"{within}/{timed} within ±150ms"


def test_word_timings_use_the_edge_tts_schema_and_are_monotonic(tmp_path):
    fx = _fixture()
    result = wa.align_cues(_audio(tmp_path), fx["cues"], duration=fx["duration"],
                           model=FakeWhisperModel(fx["whisper_segments"]))

    previous_start = -1.0
    for words in result.word_timings:
        for w in words:
            assert set(w) == {"text", "start", "end"}
            assert isinstance(w["start"], float) and isinstance(w["end"], float)
            assert w["end"] >= w["start"] >= previous_start
            assert w["start"] == round(w["start"], 3)
            previous_start = w["start"]
    assert previous_start <= fx["duration"]


def test_whisper_is_prompted_with_the_script_in_thai_with_word_timestamps(tmp_path):
    fx = _fixture()
    model = FakeWhisperModel(fx["whisper_segments"])
    wa.align_cues(_audio(tmp_path), fx["cues"], model=model)

    (_, kwargs), = model.calls
    assert kwargs["word_timestamps"] is True
    assert kwargs["language"] == "th"
    assert fx["cues"][0]["text"] in kwargs["initial_prompt"]


def test_tokens_follow_translation_service_newmm_tokenizer():
    assert wa.tokenize_script("แบตเตอรี่ 5000mAh ใช้ได้ทั้งวัน") == ["แบตเตอรี่", "5000", "mAh", "ใช้ได้", "ทั้งวัน"]


def test_punctuation_tokens_get_no_timing_and_do_not_count():
    words = [wa.RecognizedWord("สวัสดี", 0.0, 0.5), wa.RecognizedWord("ครับ", 0.5, 0.8)]
    result = wa.align_tokens(["สวัสดี", "!", "ครับ"], words)
    assert result.total == 2 and result.matched == 2
    assert result.timings[1] is None


def test_unrecognized_tokens_are_interpolated_between_neighbours():
    words = [wa.RecognizedWord("หนึ่ง", 0.0, 0.4), wa.RecognizedWord("สาม", 1.0, 1.4)]
    result = wa.align_tokens(["หนึ่ง", "สอง", "สาม"], words)
    assert result.matched == 2
    middle = result.timings[1]
    assert middle["start"] == pytest.approx(0.4) and middle["end"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Spec onset (AC: SpecBar within ±150ms of the number word)
# ---------------------------------------------------------------------------

def test_spec_onset_lands_within_150ms_of_the_spoken_number(tmp_path):
    fx = _fixture()
    result = wa.align_cues(_audio(tmp_path), fx["cues"], duration=fx["duration"],
                           model=FakeWhisperModel(fx["whisper_segments"]))
    checked = 0
    for cue, words, truth in zip(fx["cues"], result.word_timings, fx["truth"]):
        if not cue["on_screen"]:
            continue
        onset = wa.spec_onset_time(words, cue["on_screen"], start=cue["start"], end=cue["end"])
        number = next(t for t in truth if any(ch.isdigit() for ch in t["text"]))
        assert onset is not None, cue
        assert abs(onset - number["start"]) <= TOLERANCE_S, (cue["on_screen"], onset, number)
        assert onset > cue["start"]
        checked += 1
    assert checked == 4


def test_spec_onset_survives_number_read_back_as_thai_words(tmp_path):
    """Whisper may write 5000 as 'ห้าพัน'; the number is then interpolated
    between its aligned neighbours and still lands on time."""
    fx = _fixture()
    segments = json.loads(json.dumps(fx["whisper_segments"]))
    segments[0]["words"][2]["word"] = "ห้าพัน"
    result = wa.align_cues(_audio(tmp_path), fx["cues"], duration=fx["duration"],
                           model=FakeWhisperModel(segments))
    cue = fx["cues"][0]
    onset = wa.spec_onset_time(result.word_timings[0], cue["on_screen"], start=cue["start"], end=cue["end"])
    assert abs(onset - fx["truth"][0][1]["start"]) <= TOLERANCE_S


def test_spec_onset_prefers_the_number_shown_on_screen():
    words = [
        {"text": "แบต", "start": 0.0, "end": 0.3},
        {"text": "5000", "start": 0.3, "end": 0.6},
        {"text": "mAh", "start": 0.6, "end": 0.8},
        {"text": "ชาร์จ", "start": 0.9, "end": 1.1},
        {"text": "65", "start": 1.2, "end": 1.4},
        {"text": "W", "start": 1.4, "end": 1.5},
    ]
    assert wa.spec_onset_time(words, "65W", start=0.0, end=3.0) == 1.2
    assert wa.spec_onset_time(words, "", start=0.0, end=3.0) == 0.3
    assert wa.spec_onset_time(words, "IP68", start=0.0, end=3.0) == 0.3  # unspoken -> first spec


def test_spec_onset_is_none_without_timings_or_too_late():
    words = [{"text": "65", "start": 1.9, "end": 2.0}, {"text": "W", "start": 2.0, "end": 2.1}]
    assert wa.spec_onset_time([], "65W", start=0.0, end=2.2) is None
    assert wa.spec_onset_time(None, "65W") is None
    assert wa.spec_onset_time(words, "65W", start=0.0, end=2.2) is None  # < 0.4s visible
    assert wa.spec_onset_time([{"text": "สวย", "start": 0.1, "end": 0.3}], "สวยมาก", start=0.0, end=2.0) is None


# ---------------------------------------------------------------------------
# Failure paths never raise and attach nothing
# ---------------------------------------------------------------------------

def test_missing_faster_whisper_returns_none_with_thai_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)  # import -> ImportError
    fx = _fixture()
    assert wa.align_cues(_audio(tmp_path), fx["cues"]) is None
    assert "faster-whisper" in capsys.readouterr().out


def test_low_coverage_transcript_is_rejected(tmp_path, capsys):
    fx = _fixture()
    junk = [{"words": [{"word": "ลาลาลา", "start": 0.0, "end": 1.0}, {"word": "zzz", "start": 1.0, "end": 2.0}]}]
    assert wa.align_cues(_audio(tmp_path), fx["cues"], model=FakeWhisperModel(junk)) is None
    assert "จับคู่คำกับสคริปต์ได้แค่" in capsys.readouterr().out


def test_transcribe_error_returns_none(tmp_path, capsys):
    class Broken:
        def transcribe(self, *_a, **_k):
            raise RuntimeError("CUDA out of memory")

    fx = _fixture()
    assert wa.align_cues(_audio(tmp_path), fx["cues"], model=Broken()) is None
    assert "จัดเวลาคำไม่สำเร็จ" in capsys.readouterr().out


def test_alignment_can_be_disabled_by_env(tmp_path, monkeypatch):
    monkeypatch.setenv(wa.ENABLE_ENV, "0")
    fx = _fixture()
    model = FakeWhisperModel(fx["whisper_segments"])
    assert wa.align_cues(_audio(tmp_path), fx["cues"], model=model) is None
    assert model.calls == []


# ---------------------------------------------------------------------------
# Cache by audio hash
# ---------------------------------------------------------------------------

def test_cache_by_audio_hash_skips_retranscription(tmp_path):
    fx = _fixture()
    audio = _audio(tmp_path)
    cache = tmp_path / "voiceover.word_timings.json"
    model = FakeWhisperModel(fx["whisper_segments"])

    first = wa.align_cues(audio, fx["cues"], model=model, cache_path=cache)
    assert cache.exists() and not first.cached

    wa.reset_shared_models()  # drop the memory cache: the sidecar must serve it
    second = wa.align_cues(audio, fx["cues"], model=model, cache_path=cache)
    assert second.cached and second.word_timings == first.word_timings
    assert len(model.calls) == 1

    audio.write_bytes(b"RIFF-a-different-take")
    third = wa.align_cues(audio, fx["cues"], model=model, cache_path=cache)
    assert not third.cached and len(model.calls) == 2


def test_attach_keeps_existing_edge_timings():
    alignment = wa.CueAlignment(word_timings=[[{"text": "ก", "start": 0.0, "end": 0.1}], [{"text": "ข", "start": 0.2, "end": 0.3}]],
                                matched=2, total=2, model="m")
    edge = [{"text": "x", "start": 9.0, "end": 9.1}]
    cues = [{"text": "ก", "word_timings": edge}, {"text": "ข"}]
    out = wa.attach_word_timings(cues, alignment)
    assert out[0]["word_timings"] == edge
    assert out[1]["word_timings"] == [{"text": "ข", "start": 0.2, "end": 0.3}]
    assert "word_timings" not in cues[1]  # input untouched


# ---------------------------------------------------------------------------
# Device + shared model (AGENTS rule 21, concurrent renders)
# ---------------------------------------------------------------------------

def _fake_ctranslate2(monkeypatch, count):
    monkeypatch.setitem(sys.modules, "ctranslate2", types.SimpleNamespace(get_cuda_device_count=lambda: count))


def test_gpu_present_loads_cuda_float16(monkeypatch):
    _fake_ctranslate2(monkeypatch, 1)
    calls = []
    wa.get_shared_model(factory=lambda *a, **k: calls.append((a, k)) or object())
    (args, kwargs), = calls
    assert args == (wa.DEFAULT_MODEL_SIZE,)
    assert kwargs["device"] == "cuda" and kwargs["compute_type"] == "float16"
    assert kwargs["local_files_only"] is True


def test_no_gpu_falls_back_to_cpu_int8_with_thai_warning(monkeypatch, capsys):
    _fake_ctranslate2(monkeypatch, 0)
    calls = []
    wa.get_shared_model("base", factory=lambda *a, **k: calls.append(k) or object())
    assert calls[0]["device"] == "cpu" and calls[0]["compute_type"] == "int8"
    assert "ไม่พบการ์ดจอ CUDA" in capsys.readouterr().out


def test_cuda_load_failure_retries_on_cpu(monkeypatch):
    _fake_ctranslate2(monkeypatch, 1)
    calls = []

    def factory(*_a, **k):
        calls.append(k["device"])
        if k["device"] == "cuda":
            raise RuntimeError("cuDNN missing")
        return "cpu-model"

    assert wa.get_shared_model(factory=factory) == "cpu-model"
    assert calls == ["cuda", "cpu"]


def test_concurrent_callers_share_one_model(monkeypatch):
    _fake_ctranslate2(monkeypatch, 1)
    created = []
    gate = threading.Event()

    def factory(*_a, **_k):
        gate.wait(0.05)
        created.append(object())
        return created[-1]

    results = []
    threads = [threading.Thread(target=lambda: results.append(wa.get_shared_model(factory=factory))) for _ in range(8)]
    for t in threads:
        t.start()
    gate.set()
    for t in threads:
        t.join()
    assert len(created) == 1
    assert all(r is created[0] for r in results)


def test_model_size_is_configurable_by_env(monkeypatch):
    _fake_ctranslate2(monkeypatch, 1)
    monkeypatch.setenv(wa.MODEL_ENV, "small")
    seen = []
    wa.get_shared_model(factory=lambda size, **k: seen.append(size) or object())
    assert seen == ["small"]

"""M9 integration: Gemini TTS voice stage -> aligned word timings -> SpecBar
onset, spec callout onset and editorial pacing.

Offline: Gemini TTS writes a synthetic wav, ffprobe is stubbed and the shared
faster-whisper model is replaced by a fake that replays
``tests/fixtures/word_alignment_gemini_th.json``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from scripts import word_alignment as wa
from scripts.editorial_pacing import build_pacing_plan_from_cues, resolve_pacing_boundaries
from scripts.gemini_tts_engine import GeminiFlashTTSEngine
from scripts.pipeline_context import PipelineContext
from scripts.product_callout_builder import build_product_callouts
from scripts.stages import voice_stage
from scripts.stages.voice_stage import VoiceStage
from scripts.subtitle_engine import SubtitleEngine

FIXTURE = Path(__file__).parent / "fixtures" / "word_alignment_gemini_th.json"
TOLERANCE_S = 0.150
SR = 16000


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FakeWhisperModel:
    def __init__(self, segments):
        self.segments = segments
        self.calls = 0

    def transcribe(self, audio, **kwargs):
        self.calls += 1
        segs = [
            SimpleNamespace(words=[SimpleNamespace(word=w["word"], start=w["start"], end=w["end"]) for w in s["words"]])
            for s in self.segments
        ]
        return iter(segs), SimpleNamespace(language="th")


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    # generate_ass batch-translates captions through Google; keep tests offline.
    from scripts.translator import SubtitleTranslator

    monkeypatch.setattr(SubtitleTranslator, "translate_batch", staticmethod(lambda texts: [""] * len(texts)))
    wa.reset_shared_models()
    monkeypatch.delenv(wa.ENABLE_ENV, raising=False)
    yield
    wa.reset_shared_models()


def _write_voice(path: Path, fx) -> None:
    """Tone bursts where the fixture's cues are spoken, silence between."""
    audio = np.zeros(int(fx["duration"] * SR), dtype=np.float32)
    for cue in fx["truth"]:
        a, b = int(cue[0]["start"] * SR), int(cue[-1]["end"] * SR)
        t = np.arange(b - a) / SR
        audio[a:b] = 0.4 * np.sin(2 * np.pi * 220 * t)
    sf.write(str(path), audio, SR)


def _run_gemini_voice_stage(tmp_path, monkeypatch, fx, model_getter):
    def fake_generate_speech(text, output_path, **_kwargs):
        _write_voice(Path(output_path), fx)
        return output_path

    monkeypatch.setattr(GeminiFlashTTSEngine, "generate_speech", staticmethod(fake_generate_speech))
    monkeypatch.setattr(voice_stage, "_probe_audio_duration", lambda _p: fx["duration"])
    monkeypatch.setattr(wa, "get_shared_model", model_getter)

    ctx = PipelineContext(
        product_name="test",
        raw_video_path="input.mp4",
        project_name="m9_word_alignment_test",
        voice_engine_type="gemini_tts",
    )
    ctx.project_dir = tmp_path
    ctx.script_data = {"lines": [{"text": c["text"], "on_screen": c["on_screen"]} for c in fx["cues"]]}
    ctx.should_run = lambda _stage: True
    VoiceStage.run(ctx)
    return ctx


def _spec_events(ass_path):
    content = Path(ass_path).read_text(encoding="utf-8")
    return [l for l in content.splitlines() if l.startswith("Dialogue:") and ",SpecBar," in l]


def _ass_seconds(stamp: str) -> float:
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _number_truth(fx, on_screen):
    for cue, truth in zip(fx["cues"], fx["truth"]):
        if cue["on_screen"] == on_screen:
            return next(t["start"] for t in truth if any(ch.isdigit() for ch in t["text"]))
    raise KeyError(on_screen)


# ---------------------------------------------------------------------------
# Voice stage
# ---------------------------------------------------------------------------

def test_gemini_voice_stage_attaches_word_timings(tmp_path, monkeypatch):
    fx = _fixture()
    model = FakeWhisperModel(fx["whisper_segments"])
    ctx = _run_gemini_voice_stage(tmp_path, monkeypatch, fx, lambda *_a, **_k: model)

    assert ctx.voice_engine_used == "gemini_tts"
    assert ctx.cues and all(c.get("word_timings") for c in ctx.cues)
    timed_words = [w for c in ctx.cues for w in c["word_timings"]]
    assert len(timed_words) == 37
    assert all(set(w) == {"text", "start", "end"} for w in timed_words)
    # Line-level beat cues carry their clauses' timings too.
    assert all(c.get("word_timings") for c in ctx.beat_cues)
    # Cached by audio hash next to the voiceover.
    assert (tmp_path / "voiceover.word_timings.json").exists()
    assert model.calls == 1


def test_alignment_failure_leaves_voice_stage_output_unchanged(tmp_path, monkeypatch, capsys):
    fx = _fixture()
    # Baseline: alignment switched off -> the pre-M9 Gemini path.
    monkeypatch.setenv(wa.ENABLE_ENV, "0")
    (tmp_path / "a").mkdir()
    baseline = _run_gemini_voice_stage(tmp_path / "a", monkeypatch, fx, lambda *_a, **_k: None)
    monkeypatch.delenv(wa.ENABLE_ENV)

    def broken_getter(*_a, **_k):
        raise RuntimeError("CUDA driver crashed")

    (tmp_path / "b").mkdir()
    failed = _run_gemini_voice_stage(tmp_path / "b", monkeypatch, fx, broken_getter)

    assert failed.cues == baseline.cues
    assert failed.beat_cues == baseline.beat_cues
    assert failed.total_duration == baseline.total_duration
    assert not any("word_timings" in c for c in failed.cues)
    out = capsys.readouterr().out
    assert "จัดเวลาคำไม่สำเร็จ" in out and "ใช้จังหวะซับ/ช็อตแบบเดิม" in out


def test_missing_faster_whisper_does_not_fail_the_render(tmp_path, monkeypatch):
    fx = _fixture()

    def no_whisper(*_a, **_k):
        raise ImportError("No module named 'faster_whisper'")

    ctx = _run_gemini_voice_stage(tmp_path, monkeypatch, fx, no_whisper)
    assert ctx.cues and not any("word_timings" in c for c in ctx.cues)


# ---------------------------------------------------------------------------
# SpecBar (subtitle_engine) and spec callout (product_callout_builder)
# ---------------------------------------------------------------------------

def test_specbar_starts_within_150ms_of_the_spoken_number(tmp_path, monkeypatch):
    fx = _fixture()
    ctx = _run_gemini_voice_stage(tmp_path, monkeypatch, fx, lambda *_a, **_k: FakeWhisperModel(fx["whisper_segments"]))
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=ctx.cues, output_ass_path=str(tmp_path / "out.ass"), bilingual=False
    )
    events = _spec_events(ass_path)
    assert len(events) == 4
    cues_by_text = {c["on_screen"]: c for c in ctx.cues if c.get("on_screen")}
    for line in events:
        fields = line.split(",", 9)
        start, end, text = _ass_seconds(fields[1]), _ass_seconds(fields[2]), fields[9]
        on_screen = re.sub(r"\{[^}]*\}", "", text)
        cue = cues_by_text[on_screen]
        assert abs(start - _number_truth(fx, on_screen)) <= TOLERANCE_S, (on_screen, start)
        assert start > cue["start"]
        # End unchanged: still the cue end (ASS stamps are centiseconds).
        assert abs(end - cue["end"]) < 0.011


def test_specbar_without_word_timings_keeps_sentence_start(tmp_path):
    cues = [{"id": 1, "start": 1.0, "end": 3.0, "text": "ชาร์จไว 65W เต็มใน 30 นาที", "sfx": None, "on_screen": "65W"}]
    ass_path, _ = SubtitleEngine.generate_ass(cues=cues, output_ass_path=str(tmp_path / "out.ass"), bilingual=False)
    (event,) = _spec_events(ass_path)
    assert "0:00:01.00,0:00:03.00" in event


def test_specbar_style_and_markup_unchanged_by_word_timings(tmp_path):
    base = {"id": 1, "start": 1.0, "end": 3.0, "text": "ชาร์จไว 65W", "sfx": None, "on_screen": "65W"}
    timed = dict(base, word_timings=[
        {"text": "ชาร์จ", "start": 1.0, "end": 1.3}, {"text": "ไว", "start": 1.3, "end": 1.5},
        {"text": "65", "start": 1.6, "end": 1.8}, {"text": "W", "start": 1.8, "end": 1.9},
    ])
    (plain,) = _spec_events(SubtitleEngine.generate_ass(cues=[base], output_ass_path=str(tmp_path / "a.ass"), bilingual=False)[0])
    (shifted,) = _spec_events(SubtitleEngine.generate_ass(cues=[timed], output_ass_path=str(tmp_path / "b.ass"), bilingual=False)[0])
    assert "0:00:01.60,0:00:03.00" in shifted
    # Only the start stamp differs: layer, style, margins, animation and text are identical.
    assert plain.replace("0:00:01.00", "T") == shifted.replace("0:00:01.60", "T")
    style = lambda p: [l for l in Path(p).read_text(encoding="utf-8").splitlines() if l.startswith("Style: SpecBar")]
    assert style(tmp_path / "a.ass") == style(tmp_path / "b.ass")


def test_spec_callout_starts_on_the_number_when_beat_cue_is_timed():
    words = [
        {"text": "ชาร์จ", "start": 2.0, "end": 2.3}, {"text": "ไว", "start": 2.3, "end": 2.5},
        {"text": "65", "start": 2.62, "end": 2.8}, {"text": "W", "start": 2.8, "end": 2.9},
    ]
    timed = [{"id": 1, "start": 2.0, "end": 4.0, "text": "ชาร์จไว 65W", "on_screen": "65W", "word_timings": words}]
    untimed = [{"id": 1, "start": 2.0, "end": 4.0, "text": "ชาร์จไว 65W", "on_screen": "65W"}]
    feature = [{"id": 1, "start": 2.0, "end": 4.0, "text": "สวยมาก", "on_screen": "ดีไซน์พรีเมียม",
                "word_timings": [{"text": "สวย", "start": 2.4, "end": 2.6}]}]

    (spec,) = build_product_callouts(timed)
    assert spec["callout_type"] == "spec" and spec["start"] == 2.62 and spec["end"] == 4.0
    (legacy,) = build_product_callouts(untimed)
    assert legacy["start"] == 2.0 and legacy["end"] == 4.0
    (feat,) = build_product_callouts(feature)
    assert feat["start"] == 2.0
    assert {k: v for k, v in spec.items() if k != "start"} == {k: v for k, v in legacy.items() if k != "start"}


# ---------------------------------------------------------------------------
# Editorial pacing now activates for Gemini TTS
# ---------------------------------------------------------------------------

def test_editorial_pacing_activates_for_aligned_gemini_cues(tmp_path, monkeypatch):
    fx = _fixture()
    ctx = _run_gemini_voice_stage(tmp_path, monkeypatch, fx, lambda *_a, **_k: FakeWhisperModel(fx["whisper_segments"]))

    plan = build_pacing_plan_from_cues(ctx.cues, duration=ctx.total_duration)
    assert plan is not None
    assert len(plan["words"]) >= 36  # zero-length interpolations may drop out
    assert plan["beats"], "aligned words must yield beat candidates"
    # The fixture's pauses between lines are ~0.35s: short pauses, below the
    # 0.55s cut-candidate threshold.
    assert plan["silence_gaps"], "the pauses between lines must be detected as silence gaps"

    # Every silence gap sits in real silence between spoken words.
    words = sorted(plan["words"], key=lambda w: w["start"])
    for gap in plan["silence_gaps"]:
        assert not any(w["start"] < gap["end"] - 1e-6 and w["end"] > gap["start"] + 1e-6 for w in words)

    # Beat boundaries resolve for shot matching exactly as designed: within
    # the timeline and no segment shorter than the minimum.
    boundaries = resolve_pacing_boundaries(plan, ctx.total_duration, min_segment_duration=0.2)
    assert boundaries is not None
    assert boundaries[0] == 0.0 and boundaries[-1] == pytest.approx(ctx.total_duration)
    assert all(b - a >= 0.2 for a, b in zip(boundaries, boundaries[1:]))
    # The resolver stays conservative (unchanged by M9): this 16s fixture has
    # beats paired ~0.3s apart around each pause, so at the production minimum
    # shot (1.5s) it refuses and shot matching keeps its legacy grouping.
    assert resolve_pacing_boundaries(plan, ctx.total_duration, min_segment_duration=1.5) is None


def test_editorial_pacing_stays_off_without_alignment(tmp_path, monkeypatch):
    fx = _fixture()

    def broken(*_a, **_k):
        raise RuntimeError("no model")

    ctx = _run_gemini_voice_stage(tmp_path, monkeypatch, fx, broken)
    assert build_pacing_plan_from_cues(ctx.cues, duration=ctx.total_duration) is None

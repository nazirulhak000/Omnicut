"""Behavioral tests for scripts/silence_detect.py.

The dangerous outputs here are the ones that drive a ripple delete: a cut span
that overlaps speech removes words, and a keep-range list that does not tile
the timeline loses or duplicates footage. Those get direct assertions.

Audio is synthesized with ffmpeg into tmp_path -- tone and silence
concatenated at known offsets, so an assertion can name where a gap should be
rather than trusting whatever a real asset happens to contain.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import scripts.silence_detect as sd
from scripts.silence_detect import (
    SilenceDetectError,
    build_keep_ranges,
    detect_silences,
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not available on PATH"
)


def _audio(path: Path, segments: list[tuple[str, float]]) -> Path:
    """
    Build a WAV from a list of (kind, seconds) where kind is 'tone' or
    'silence'. Concatenating known-length pieces is what lets a test assert
    'there is a gap at 2.0s' instead of only 'some gap exists'.
    """
    parts, filters = [], []
    for i, (kind, dur) in enumerate(segments):
        if kind == "tone":
            parts += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}"]
        else:
            parts += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono:duration={dur}"]
        filters.append(f"[{i}:a]")
    graph = "".join(filters) + f"concat=n={len(segments)}:v=0:a=1[out]"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *parts,
         "-filter_complex", graph, "-map", "[out]", str(path)],
        capture_output=True, check=True, timeout=120,
    )
    return path


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def test_finds_a_gap_between_two_phrases(tmp_path):
    """tone 1.5s | silence 1.0s | tone 1.5s -- the gap starts near 1.5s."""
    wav = _audio(tmp_path / "gap.wav", [("tone", 1.5), ("silence", 1.0), ("tone", 1.5)])
    result = detect_silences(wav)

    assert len(result["silences"]) == 1
    gap = result["silences"][0]
    assert gap["start"] == pytest.approx(1.5, abs=0.15)
    assert gap["end"] == pytest.approx(2.5, abs=0.15)
    assert result["duration"] == pytest.approx(4.0, abs=0.15)


def test_continuous_speech_has_no_dead_air(tmp_path):
    wav = _audio(tmp_path / "solid.wav", [("tone", 3.0)])
    result = detect_silences(wav)
    assert result["silences"] == []
    assert result["removable_s"] == 0


def test_gap_shorter_than_threshold_is_ignored(tmp_path):
    """A 0.2s breath is under the 0.35s minimum -- cutting it would make the
    read sound clipped for almost no time saved."""
    wav = _audio(tmp_path / "breath.wav", [("tone", 1.0), ("silence", 0.2), ("tone", 1.0)])
    assert detect_silences(wav)["silences"] == []


def test_finds_multiple_gaps_in_order(tmp_path):
    wav = _audio(
        tmp_path / "multi.wav",
        [("tone", 1.0), ("silence", 0.8), ("tone", 1.0), ("silence", 0.9), ("tone", 1.0)],
    )
    silences = detect_silences(wav)["silences"]
    assert len(silences) == 2
    starts = [s["start"] for s in silences]
    assert starts == sorted(starts)
    assert silences[0]["end"] <= silences[1]["start"]


def test_trailing_silence_is_reported(tmp_path):
    """A file ending mid-silence gives silencedetect a start with no end.
    Dead air at the tail is exactly what this feature removes, so it must not
    be dropped."""
    wav = _audio(tmp_path / "tail.wav", [("tone", 1.5), ("silence", 1.2)])
    silences = detect_silences(wav)["silences"]
    assert silences, "trailing dead air must be reported"
    assert silences[-1]["end"] == pytest.approx(2.7, abs=0.2)


def test_leading_silence_is_reported(tmp_path):
    wav = _audio(tmp_path / "lead.wav", [("silence", 1.0), ("tone", 1.5)])
    silences = detect_silences(wav)["silences"]
    assert silences
    assert silences[0]["start"] == pytest.approx(0.0, abs=0.1)


# ---------------------------------------------------------------------------
# Padding -- the guard against clipped speech
# ---------------------------------------------------------------------------

def test_cut_span_sits_strictly_inside_the_detected_gap(tmp_path):
    """The proposed cut must never reach past the silence into speech. This
    is the assertion that stops the feature from eating words."""
    wav = _audio(tmp_path / "gap.wav", [("tone", 1.5), ("silence", 1.0), ("tone", 1.5)])
    for gap in detect_silences(wav)["silences"]:
        assert gap["cut_start"] >= gap["start"]
        assert gap["cut_end"] <= gap["end"]
        assert gap["cut_duration"] <= gap["duration"]


def test_padding_leaves_natural_pause_at_both_ends(tmp_path):
    wav = _audio(tmp_path / "gap.wav", [("tone", 1.5), ("silence", 1.0), ("tone", 1.5)])
    gap = detect_silences(wav, padding_s=0.10)["silences"][0]
    assert gap["cut_start"] - gap["start"] == pytest.approx(0.10, abs=0.01)
    assert gap["end"] - gap["cut_end"] == pytest.approx(0.10, abs=0.01)


def test_zero_padding_cuts_the_whole_gap(tmp_path):
    wav = _audio(tmp_path / "gap.wav", [("tone", 1.5), ("silence", 1.0), ("tone", 1.5)])
    gap = detect_silences(wav, padding_s=0.0)["silences"][0]
    assert gap["cut_duration"] == pytest.approx(gap["duration"], abs=0.01)


def test_padding_larger_than_the_gap_yields_no_cut(tmp_path):
    """Padding wider than the silence would invert the span. It must drop the
    entry rather than emit a negative-length cut."""
    wav = _audio(tmp_path / "gap.wav", [("tone", 1.0), ("silence", 0.5), ("tone", 1.0)])
    result = detect_silences(wav, padding_s=1.0)
    assert all(s["cut_duration"] >= sd.MIN_USEFUL_CUT_S for s in result["silences"])


def test_all_reported_values_are_non_negative(tmp_path):
    wav = _audio(
        tmp_path / "multi.wav",
        [("tone", 1.0), ("silence", 0.8), ("tone", 1.0), ("silence", 0.9)],
    )
    result = detect_silences(wav)
    for gap in result["silences"]:
        assert all(gap[k] >= 0 for k in ("start", "end", "duration", "cut_start", "cut_duration"))
        assert gap["end"] > gap["start"]
    assert result["removable_s"] >= 0


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_missing_file_raises(tmp_path):
    with pytest.raises(SilenceDetectError):
        detect_silences(tmp_path / "nope.wav")


def test_undecodable_file_raises_rather_than_reporting_no_silence(tmp_path):
    """Reporting 'no dead air' for a file that never decoded would tell the
    user their clip is already tight when nothing was examined."""
    junk = tmp_path / "junk.wav"
    junk.write_bytes(b"RIFF definitely not audio")
    with pytest.raises(SilenceDetectError):
        detect_silences(junk)


# ---------------------------------------------------------------------------
# Log parsing (no ffmpeg needed)
# ---------------------------------------------------------------------------

def test_parse_pairs_starts_with_ends():
    log = (
        "[silencedetect @ 0x1] silence_start: 1.5\n"
        "[silencedetect @ 0x1] silence_end: 2.5 | silence_duration: 1.0\n"
    )
    assert sd._parse_silence_log(log, 4.0) == [{"start": 1.5, "end": 2.5}]


def test_parse_closes_unterminated_span_at_duration():
    log = "[silencedetect @ 0x1] silence_start: 2.0\n"
    assert sd._parse_silence_log(log, 3.5) == [{"start": 2.0, "end": 3.5}]


def test_parse_drops_unterminated_span_past_duration():
    """A start beyond the known duration cannot be closed into a real span."""
    assert sd._parse_silence_log("silence_start: 9.0\n", 3.0) == []


def test_parse_ignores_zero_length_and_inverted_spans():
    log = "silence_start: 2.0\nsilence_end: 2.0\n"
    assert sd._parse_silence_log(log, 5.0) == []


def test_parse_empty_log_is_empty():
    assert sd._parse_silence_log("", 5.0) == []
    assert sd._parse_silence_log(None, 5.0) == []


# ---------------------------------------------------------------------------
# build_keep_ranges -- what a ripple delete would keep
# ---------------------------------------------------------------------------

def test_keep_ranges_tile_the_timeline_without_overlap():
    """Keeps must be ordered, non-overlapping and inside the duration --
    an overlap would duplicate footage, a gap would drop it."""
    silences = [
        {"cut_start": 1.5, "cut_end": 2.5},
        {"cut_start": 4.0, "cut_end": 5.0},
    ]
    keeps = build_keep_ranges(7.0, silences)
    assert keeps == [
        {"start": 0.0, "end": 1.5},
        {"start": 2.5, "end": 4.0},
        {"start": 5.0, "end": 7.0},
    ]
    for a, b in zip(keeps, keeps[1:]):
        assert a["end"] <= b["start"]


def test_keep_ranges_length_equals_duration_minus_cuts():
    silences = [{"cut_start": 1.0, "cut_end": 2.0}, {"cut_start": 3.0, "cut_end": 3.5}]
    keeps = build_keep_ranges(6.0, silences)
    kept = sum(k["end"] - k["start"] for k in keeps)
    assert kept == pytest.approx(6.0 - 1.5)


def test_keep_ranges_handle_unsorted_input():
    unsorted_spans = [{"cut_start": 4.0, "cut_end": 5.0}, {"cut_start": 1.0, "cut_end": 2.0}]
    keeps = build_keep_ranges(6.0, unsorted_spans)
    assert [k["start"] for k in keeps] == sorted(k["start"] for k in keeps)


def test_keep_ranges_merge_overlapping_cuts():
    """Overlapping cut spans must not produce a negative-length keep."""
    keeps = build_keep_ranges(6.0, [{"cut_start": 1.0, "cut_end": 3.0},
                                    {"cut_start": 2.0, "cut_end": 4.0}])
    assert all(k["end"] > k["start"] for k in keeps)
    assert keeps == [{"start": 0.0, "end": 1.0}, {"start": 4.0, "end": 6.0}]


def test_keep_ranges_with_no_silences_is_the_whole_clip():
    assert build_keep_ranges(5.0, []) == [{"start": 0.0, "end": 5.0}]


def test_fully_silent_track_keeps_nothing():
    """The caller must refuse this rather than build an empty timeline --
    surfacing it as [] makes that check possible."""
    assert build_keep_ranges(3.0, [{"cut_start": 0.0, "cut_end": 3.0}]) == []


def test_keep_ranges_clamp_to_zero_duration():
    assert build_keep_ranges(0.0, []) == []

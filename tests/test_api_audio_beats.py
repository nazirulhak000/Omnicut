"""Behavioral tests for scripts/api_audio_beats.py.

Both endpoints take a caller-supplied filename and turn it into a filesystem
read, so much of this file is about what they refuse: traversal, nested
paths, non-audio suffixes, and symlinks resolving outside the allowed roots.
The rest pins the response shapes the timeline depends on.

MUSIC_DIR is monkeypatched on the api module (the name is bound at import
time, so patching scripts.config alone would not take effect) and every audio
file is synthesized into tmp_path -- no real asset is ever read.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

soundfile = pytest.importorskip("soundfile")
pytest.importorskip("librosa")

import scripts.api_audio_beats as api
from scripts import beat_sync as beat_sync_mod


def _click_track(dur_s: float, interval_s: float = 0.5, sr: int = 22050, seed: int = 0):
    """Percussive bursts at a fixed interval, so librosa's beat tracker has
    something real to lock onto (a pure tone yields no onsets)."""
    rng = np.random.default_rng(seed)
    n = int(sr * dur_s)
    y = np.zeros(n, dtype=np.float64)
    burst_len = int(sr * 0.02)
    t = 0.0
    while t < dur_s:
        idx = int(t * sr)
        end = min(n, idx + burst_len)
        length = end - idx
        if length > 0:
            y[idx:end] += rng.standard_normal(length) * np.exp(-np.linspace(0, 10, length))
        t += interval_s
    peak = np.max(np.abs(y)) or 1.0
    return (y / peak * 0.8).astype(np.float64)


@pytest.fixture
def music_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated stand-in for 02_Assets/Music, plus an isolated beat cache
    so a test run never writes into the real asset tree."""
    d = tmp_path / "Music"
    d.mkdir()
    monkeypatch.setattr(api, "MUSIC_DIR", d)
    monkeypatch.setattr(beat_sync_mod, "BEAT_CACHE_FILE", tmp_path / ".beat_cache.json")
    return d


@pytest.fixture
def client(music_dir: Path) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _write_bgm(music_dir: Path, name: str, dur_s: float = 6.0) -> Path:
    path = music_dir / name
    soundfile.write(str(path), _click_track(dur_s), 22050)
    return path


def _get(client: TestClient, bgm_name: str):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return client.get("/api/audio/beats", params={"bgm_name": bgm_name})


# ---------------------------------------------------------------------------
# Happy path / response contract
# ---------------------------------------------------------------------------

def test_returns_grid_for_existing_track(client, music_dir):
    _write_bgm(music_dir, "tiktok_upbeat_bgm.wav")
    res = _get(client, "tiktok_upbeat_bgm.wav")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["bgm_name"] == "tiktok_upbeat_bgm.wav"
    assert body["available"] is True
    assert body["major_beats"] and body["minor_beats"]
    assert body["bpm"] is not None
    # Every timestamp must be finite, non-negative and inside the track --
    # a marker past the end of the music would be an unreachable snap target.
    for t in body["major_beats"] + body["minor_beats"]:
        assert isinstance(t, float) and 0.0 <= t <= 6.0


def test_bare_stem_resolves_to_the_audio_file(client, music_dir):
    """The plan specifies ?bgm_name=tiktok_upbeat_bgm without a suffix."""
    _write_bgm(music_dir, "tiktok_upbeat_bgm.wav")
    res = _get(client, "tiktok_upbeat_bgm")
    assert res.status_code == 200
    assert res.json()["bgm_name"] == "tiktok_upbeat_bgm.wav"


def test_beats_are_sorted_and_disjoint(client, music_dir):
    _write_bgm(music_dir, "bgm.wav")
    body = _get(client, "bgm.wav").json()
    major, minor = body["major_beats"], body["minor_beats"]
    assert major == sorted(major)
    assert minor == sorted(minor)
    assert not set(major) & set(minor)


def test_silent_track_reports_unavailable_rather_than_failing(client, music_dir):
    """Silence has no onsets. The timeline needs to tell 'no beats in this
    track' apart from 'the request failed', so this is a 200 with
    available=False, not an error."""
    soundfile.write(str(music_dir / "silent.wav"), np.zeros(22050 * 2), 22050)
    res = _get(client, "silent.wav")
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is False
    assert body["major_beats"] == [] and body["minor_beats"] == []


def test_undecodable_file_reports_unavailable(client, music_dir):
    (music_dir / "corrupt.wav").write_bytes(b"RIFF fake wav not real audio data")
    res = _get(client, "corrupt.wav")
    assert res.status_code == 200
    assert res.json()["available"] is False


# ---------------------------------------------------------------------------
# Path safety -- bgm_name is attacker-controlled
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hostile",
    [
        "../config.py",
        "../../scripts/config.py",
        "..\\..\\scripts\\config.py",
        "subdir/track.wav",
        "subdir\\track.wav",
        ".beat_cache.json",
        "....//config.py",
    ],
)
def test_rejects_traversal_and_nested_paths(client, hostile):
    res = _get(client, hostile)
    assert res.status_code == 400, f"{hostile!r} should be rejected outright"


def test_rejects_absolute_path(client, tmp_path):
    res = _get(client, str(tmp_path / "anything.wav"))
    assert res.status_code == 400


def test_rejects_url_encoded_traversal(client):
    """The handler unquotes before validating, so %2F must not smuggle a
    separator past the check."""
    res = _get(client, "..%2Fconfig.py")
    assert res.status_code == 400


def test_rejects_non_audio_suffix(client, music_dir):
    (music_dir / "notes.txt").write_text("not audio", encoding="utf-8")
    res = _get(client, "notes.txt")
    assert res.status_code == 400


def test_missing_track_is_404_not_500(client):
    res = _get(client, "no_such_track.wav")
    assert res.status_code == 404


def test_blank_name_is_400(client):
    res = _get(client, "   ")
    assert res.status_code == 400


def test_symlink_escaping_music_dir_is_not_served(client, music_dir, tmp_path):
    """A symlink living inside MUSIC_DIR but resolving outside it must not
    become a readable path -- this is why containment is re-checked after
    resolve(), matching api_videos.py's _allowed_media_path."""
    outside = tmp_path / "outside.wav"
    soundfile.write(str(outside), _click_track(2.0), 22050)
    link = music_dir / "sneaky.wav"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform/account")
    res = _get(client, "sneaky.wav")
    assert res.status_code == 404


def test_response_does_not_leak_absolute_paths(client, music_dir):
    """Error text is shown in the UI; it must name the track, not the
    machine's directory layout."""
    res = _get(client, "missing_track.wav")
    assert str(music_dir) not in res.text


# ---------------------------------------------------------------------------
# /api/audio/silences
# ---------------------------------------------------------------------------

@pytest.fixture
def media_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A stand-in project tree whose 01_Raw is an allowed media root."""
    base = tmp_path / "repo"
    raw = base / "01_Raw"
    raw.mkdir(parents=True)
    monkeypatch.setattr(api, "BASE_DIR", base)
    monkeypatch.setattr(api, "CAPCUT_DRAFT_DIR", tmp_path / "drafts")
    import scripts.api_videos as videos
    monkeypatch.setattr(videos, "BASE_DIR", base, raising=False)
    return raw


def _speech_gap_wav(path: Path) -> Path:
    """tone 1.5s | silence 1.0s | tone 1.5s."""
    parts, filters = [], []
    for i, (kind, dur) in enumerate([("t", 1.5), ("s", 1.0), ("t", 1.5)]):
        src = f"sine=frequency=440:duration={dur}" if kind == "t" else f"anullsrc=r=44100:cl=mono:duration={dur}"
        parts += ["-f", "lavfi", "-i", src]
        filters.append(f"[{i}:a]")
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *parts,
         "-filter_complex", "".join(filters) + "concat=n=3:v=0:a=1[out]",
         "-map", "[out]", str(path)],
        capture_output=True, check=True, timeout=120,
    )
    return path


def _silences(client: TestClient, media_path: str, **params):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return client.get("/api/audio/silences", params={"media_path": media_path, **params})


def test_silences_reports_gap_and_keep_ranges(client, media_root):
    _speech_gap_wav(media_root / "voice.wav")
    res = _silences(client, "01_Raw/voice.wav")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert len(body["silences"]) == 1
    # Keeps must tile the timeline in order without overlapping.
    keeps = body["keep_ranges"]
    assert len(keeps) == 2
    for a, b in zip(keeps, keeps[1:]):
        assert a["end"] <= b["start"]
    assert body["fully_silent"] is False


def test_silences_cut_span_never_exceeds_detected_gap(client, media_root):
    """The cut the UI would apply must stay inside the silence, or the
    ripple delete eats speech."""
    _speech_gap_wav(media_root / "voice.wav")
    for gap in _silences(client, "01_Raw/voice.wav").json()["silences"]:
        assert gap["cut_start"] >= gap["start"]
        assert gap["cut_end"] <= gap["end"]


def test_silences_rejects_traversal(client, media_root):
    for hostile in ["../../../etc/passwd", "01_Raw/../../secrets.wav", r"..\..\config.py"]:
        assert _silences(client, hostile).status_code in (400, 403, 404)


def test_silences_rejects_path_outside_media_roots(client, media_root, tmp_path):
    """A real, readable file outside the allowed roots must still be refused."""
    outside = tmp_path / "elsewhere.wav"
    _speech_gap_wav(outside)
    assert _silences(client, str(outside)).status_code == 403


def test_silences_rejects_non_media_suffix(client, media_root):
    (media_root / "notes.txt").write_text("x", encoding="utf-8")
    assert _silences(client, "01_Raw/notes.txt").status_code == 403


def test_silences_missing_file_is_404(client, media_root):
    assert _silences(client, "01_Raw/nope.wav").status_code == 404


def test_silences_blank_path_is_400(client, media_root):
    assert _silences(client, "  ").status_code == 400


def test_silences_rejects_nonpositive_min_silence(client, media_root):
    _speech_gap_wav(media_root / "voice.wav")
    assert _silences(client, "01_Raw/voice.wav", min_silence_s=0).status_code == 400
    assert _silences(client, "01_Raw/voice.wav", padding_s=-1).status_code == 400


def test_silences_undecodable_file_is_422_not_empty_result(client, media_root):
    """Returning 'no dead air' for a file that never decoded would tell the
    user their clip is already tight when nothing was examined."""
    (media_root / "junk.wav").write_bytes(b"RIFF definitely not audio")
    assert _silences(client, "01_Raw/junk.wav").status_code == 422

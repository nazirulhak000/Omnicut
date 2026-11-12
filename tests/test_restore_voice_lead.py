"""tools/restore_voice_lead.py: put back the lead-in an in-place cleanup trimmed off a voiceover.

Offline, synthetic audio, storage under tmp_path."""
import os
import wave

import numpy as np
import pytest

from scripts.project_manifest import ProjectManifest
from tests.test_incremental_render_reuse import _context_for, _strict_project, isolated_manifest  # noqa: F401
from tools import restore_voice_lead as tool

RATE = 24000


def _speech(seconds=12.0, seed=7):
    """Noise bursts at a syllable rate: unrelated between seeds, like two takes."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * RATE)) / RATE
    syllables = np.sin(2 * np.pi * (2.6 + 0.2 * seed % 1) * t) > 0.2
    noise = np.convolve(rng.normal(0, 1, len(t)), np.ones(6) / 6, mode="same")   # keep it below 4 kHz
    return (0.45 * syllables * noise / np.abs(noise).max()).astype(np.float32)


def _write(path, samples, rate=RATE, channels=1):
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    if channels == 2:
        pcm = np.repeat(pcm, 2)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def _frames(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes(), w.readframes(w.getnframes())


@pytest.fixture
def trimmed_project(isolated_manifest, monkeypatch, tmp_path):  # noqa: F811
    """A rendered project whose voice lost 0.17 s of lead-in after the mix was made."""
    monkeypatch.setattr(tool, "ARCHIVE_DIR", tmp_path / "06_Archive")
    project_name, project_dir, raw_video, _ = _strict_project(isolated_manifest)
    speech = _speech()
    lead = np.zeros(int(0.17 * RATE), np.float32)
    bed = 0.03 * np.sin(2 * np.pi * 90 * np.arange(len(lead) + len(speech)) / RATE).astype(np.float32)
    voice, mix = project_dir / "voiceover.wav", project_dir / "mixed_audio.wav"
    _write(mix, np.concatenate([lead, speech]) + bed, channels=2)
    _write(voice, speech)                              # the cleanup's result: no lead-in
    os.utime(mix, (1_700_000_000, 1_700_000_000))
    os.utime(voice, (1_700_100_000, 1_700_100_000))
    from scripts import render_jobs
    render_jobs.finalize_incremental_render(project_name)   # fingerprints accepted, as in phase 4
    return project_name, project_dir, raw_video, voice, mix


def test_measures_the_missing_lead_without_touching_anything(trimmed_project):
    project_name, _, _, voice, mix = trimmed_project
    before = voice.read_bytes()
    status, offset = tool.measure(ProjectManifest.load(project_name))
    assert status == "restore" and offset == pytest.approx(0.17, abs=0.002)
    assert tool.main([]) == 0
    assert voice.read_bytes() == before and not (tool.ARCHIVE_DIR / tool.BACKUP_FOLDER).exists()


def test_apply_restores_the_lead_keeps_a_backup_and_the_voice_stays_reusable(trimmed_project):
    project_name, project_dir, raw_video, voice, mix = trimmed_project
    original_frames, original_audio = _frames(voice)
    original_bytes = voice.read_bytes()

    assert tool.main(["--apply"]) == 0

    frames, audio = _frames(voice)
    added = frames - original_frames
    assert added == pytest.approx(0.17 * RATE, abs=0.002 * RATE)
    assert audio[: added * 2] == b"\x00" * (added * 2), "the lead-in is digital silence"
    assert audio[added * 2:] == original_audio, "the speech itself is untouched"
    backup = tool.ARCHIVE_DIR / tool.BACKUP_FOLDER / project_name / "voiceover.wav"
    assert backup.read_bytes() == original_bytes
    assert abs(tool.voice_offset_in_mix(voice, mix)) <= tool.ALIGNED_S

    ctx = _context_for(project_name, project_dir, raw_video, ProjectManifest.load(project_name))
    assert ctx.should_run("voice") is False, "the padded file is the accepted voice; no new TTS take"

    padded = voice.read_bytes()
    assert tool.measure(ProjectManifest.load(project_name))[0] == "aligned"
    assert tool.main(["--apply"]) == 0 and voice.read_bytes() == padded, "a second run changes nothing"


def test_projects_that_were_never_trimmed_or_cannot_be_measured_are_left_alone(trimmed_project, monkeypatch):
    project_name, project_dir, _, voice, mix = trimmed_project
    # mix newer than the voice: it was made from this very file
    os.utime(mix, (1_700_200_000, 1_700_200_000))
    assert tool.measure(ProjectManifest.load(project_name)) == ("not_affected", None)
    os.utime(mix, (1_700_000_000, 1_700_000_000))

    # a different take in the mix: no clear match -> skipped, file untouched
    _write(mix, _speech(seed=99), channels=2)
    os.utime(mix, (1_700_000_000, 1_700_000_000))
    before = voice.read_bytes()
    assert tool.match_voice_in_mix(voice, mix)[1] < tool.MIN_MATCH
    assert tool.measure(ProjectManifest.load(project_name)) == ("unclear", None)
    assert tool.main(["--apply"]) == 0 and voice.read_bytes() == before


def test_a_failed_check_after_padding_puts_the_original_file_back(trimmed_project, monkeypatch):
    project_name, _, _, voice, _ = trimmed_project
    before = voice.read_bytes()
    real = tool.voice_offset_in_mix
    answers = iter([real, lambda *_: 0.05])            # measure normally, then "still off"
    monkeypatch.setattr(tool, "voice_offset_in_mix", lambda v, m: next(answers)(v, m))
    ok, note = tool.restore(project_name)
    assert ok is False and "คืนไฟล์เดิม" in note
    assert voice.read_bytes() == before

"""Speed round phase 3: analysis that only feeds the automatic shot plan is skipped when the
clip list is already fixed. Offline and deterministic."""
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.pipeline_context import PipelineContext
from scripts.stages.shot_matching_stage import ShotMatchingStage

STAGE = "scripts.stages.shot_matching_stage"


def _ctx(tmp_path):
    mixed = tmp_path / "mixed.wav"
    mixed.write_bytes(b"RIFF")
    ctx = PipelineContext(product_name="speed phase 3", raw_video_path="raw.mp4", total_duration=6.0, export_mp4=False)
    ctx.raw_video = Path("raw.mp4")
    ctx.cues = [
        {"id": 1, "start": 0.0, "end": 3.0, "text": "ท่อนแรก"},
        {"id": 2, "start": 3.0, "end": 6.0, "text": "ท่อนสอง"},
    ]
    ctx.micro_cues = list(ctx.cues)
    ctx.use_ai_vision = False
    ctx.mixed_audio_path = mixed
    return ctx


@pytest.fixture()
def analyzers():
    """Record which analyzers the stage calls; none of them touch a real file."""
    calls = []

    def record(name, value):
        def fake(*_a, **_kw):
            calls.append(name)
            return value
        return fake

    with patch(f"{STAGE}.VideoEditor.get_media_info", return_value={"duration": 30.0, "width": 1080, "height": 1920}), \
            patch(f"{STAGE}.SFXManager.resolve_bgm_path", side_effect=record("bgm", Path("bgm.wav"))), \
            patch(f"{STAGE}.BeatSync.get_beat_times", side_effect=record("beats", [])), \
            patch(f"{STAGE}.BeatSync.get_rms_energy", side_effect=record("energy", ([], []))), \
            patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", side_effect=record("motion", ([], []))), \
            patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]):
        yield calls


def test_fixed_clip_list_skips_shot_plan_analysis(tmp_path, analyzers):
    ctx = _ctx(tmp_path)
    clip = {"id": "c0", "source_path": "a.mp4", "trim_start": 0.0, "trim_end": 6.0, "duration": 6.0}
    ctx.clip_list = [dict(clip)]

    ShotMatchingStage.run(ctx)

    assert analyzers == []
    assert ctx.actual_clip_list == [clip]
    assert ctx.is_newly_generated_clips is False


def _scrim_md5(source_chain):
    """md5 of every yuva420p frame the scrim chain produces (real ffmpeg, lavfi source only)."""
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-filter_complex", f"{source_chain}[out]",
         "-map", "[out]", "-c:v", "rawvideo", "-pix_fmt", "yuva420p", "-f", "md5", "-"],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-400:]
    return proc.stdout.strip()


def test_hook_scrim_strip_matches_the_full_width_scrim():
    # Same alpha expression the renderer writes: hold from 0.2s to 0.6s, then a 0.3s fade.
    alpha = "140.25*(1-Y/H)*(if(lt(T\\,0.2)\\,0\\,if(lt(T\\,0.6)\\,1\\,max(0\\,1-(T-0.6)/0.3))))"
    geq = f"format=yuva420p,geq=lum='0':cb='128':cr='128':a='{alpha}'"
    full = _scrim_md5(f"color=c=black:s=1080x480:d=1.4,{geq}")
    strip = _scrim_md5(f"color=c=black:s=2x480:d=1.4,{geq},scale=1080:480:flags=neighbor")
    assert strip == full

    # Whole composite: the scrim blended over moving 30 fps footage for its full length (before)
    # against the strip blended only inside its window (after). The scrim source runs at 25 fps.
    footage = "testsrc2=s=1080x600:r=30:d=1.6,format=yuv420p[bg]"
    before = _scrim_md5(f"{footage};color=c=black:s=1080x480:d=1.4,{geq}[a];[bg][a]overlay=x=0:y=0:format=auto")
    after = _scrim_md5(f"{footage};color=c=black:s=2x480:d=1.4,{geq},scale=1080:480:flags=neighbor[a];"
                       "[bg][a]overlay=x=0:y=0:format=auto:enable='between(t\\,0.2\\,1)'")
    assert after == before

    source = (Path(__file__).resolve().parents[1] / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert 'f"color=c=black:s=2x{grad_h}:d={scrim_source_dur:.6f}[{src}];"' in source
    assert 'f"scale={VIDEO_WIDTH}:{grad_h}:flags=neighbor[{alpha}];"' in source
    assert "between(t\\\\,{span_start:g}\\\\,{span_end + fade_tail + 0.1:g})" in source


def test_automatic_shot_plan_still_runs_every_analyzer(tmp_path, analyzers):
    ctx = _ctx(tmp_path)

    ShotMatchingStage.run(ctx)

    assert sorted(analyzers) == ["beats", "bgm", "energy", "motion"]
    assert ctx.is_newly_generated_clips is True
    assert ctx.actual_clip_list

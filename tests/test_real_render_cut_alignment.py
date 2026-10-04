"""Real-render measurements of cut timing (round EDITOR-CUT-QUALITY-R2, lane R0).

Every check renders tiny synthetic media with the real FFmpeg path and measures
the OUTPUT file -- decoded frames and decoded audio -- instead of trusting the
clip list:

* A6  -- picture cut vs voice onset (J-cut) for first_cue_start 0.0/0.1/0.3,
         shot plan from the real ShotMatchingStage, render via VideoEditor.
* B(a) -- splitClipAt (real JS module via node) on a zoom-ramp clip renders
         frame-identical to the unsplit clip, with no jump at the seam.
* B(b) -- ImageMotionEngine: exact ceil(dur*30) frames, 1080x1920, no stretch.
* B(c) -- rendered picture changes sit on the 1/30 s grid.

Offline and deterministic: analysers that would read music/motion are patched,
no Gemini, everything lives under pytest's tmp_path (deleted by pytest).
"""

import json
import math
import shutil
import subprocess
import wave
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
STAGE = "scripts.stages.shot_matching_stage"
FPS = 30
FRAME = 1.0 / FPS
SR = 48000

pytestmark = [
    pytest.mark.render_regression,
    pytest.mark.skipif(
        not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
        reason="FFmpeg and FFprobe are required for real-render measurements",
    ),
]


# ── synthetic media helpers ────────────────────────────────────────────────

def _run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, capture_output=True, **kwargs)


def _code_rgb(i):
    """Solid colour that encodes a raw frame index (8 levels per channel)."""
    return (32 * (i % 8) + 16, 32 * ((i // 8) % 8) + 16, 32 * ((i // 64) % 8) + 16)


def _decode_rgb(rgb):
    q = [int(min(7, max(0, round((float(c) - 16) / 32)))) for c in rgb]
    return q[0] + 8 * q[1] + 64 * q[2]


def _write_index_coded_source(path, n_frames=512, w=96, h=160):
    """Each frame is one flat colour = its own frame index, so any output frame
    tells which raw frame it came from (zoom/crop cannot change a flat colour)."""
    frames = np.zeros((n_frames, h, w, 3), np.uint8)
    for i in range(n_frames):
        frames[i, :, :] = _code_rgb(i)
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
          "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-qp", "0",
          "-pix_fmt", "yuv444p", str(path)], input=frames.tobytes())


def _write_voice(path, cue_starts, total, burst=0.4):
    """Synthetic voice: silence, then a 1 kHz burst at every cue start."""
    x = np.zeros(int(round(total * SR)), np.float32)
    for s in cue_starts:
        a = int(round(s * SR))
        t = np.arange(int(burst * SR)) / SR
        x[a:a + len(t)] = 0.5 * np.sin(2 * np.pi * 1000 * t)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def _write_empty_ass(path):
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
    )


def _decoded_indices(path):
    out = _run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=18:32",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]).stdout
    frames = np.frombuffer(out, np.uint8).reshape(-1, 32, 18, 3)
    return [_decode_rgb(f[12:20, 6:12].reshape(-1, 3).mean(0)) for f in frames]


def _frame_pts(path):
    out = _run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time",
                "-of", "csv=p=0", str(path)], text=True).stdout
    return [float(line.strip().strip(",")) for line in out.split() if line.strip()]


def _decoded_audio(path):
    out = _run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                "-f", "s16le", "-"]).stdout
    return np.frombuffer(out, "<i2").astype(np.float32) / 32768.0


def _onsets(x, threshold=0.05, min_gap=0.2):
    hits = np.flatnonzero(np.abs(x) > threshold)
    onsets, last = [], -10 * SR
    for k in hits:
        if k - last > int(min_gap * SR):
            onsets.append(k / SR)
        last = k
    return onsets


def _gray_frames(path, w=90, h=160):
    out = _run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h}",
                "-f", "rawvideo", "-pix_fmt", "gray", "-"]).stdout
    return np.frombuffer(out, np.uint8).reshape(-1, h, w).astype(float)


# ── A6: picture cut vs voice onset on a real render ────────────────────────

CUE_LEN = 2.0
N_CUES = 4
FIRST_CUE_STARTS = (0.0, 0.1, 0.3)


def _plan_shots(raw, cues, total):
    """Run the real ShotMatchingStage (legacy rhythmic path, no AI/BGM/motion)."""
    from scripts.pipeline_context import PipelineContext
    from scripts.stages.shot_matching_stage import ShotMatchingStage

    ctx = PipelineContext(product_name="R0 real render", raw_video_path=str(raw), clip_list=None,
                          total_duration=total, export_mp4=False)
    ctx.raw_video = Path(raw)
    ctx.cues = cues
    ctx.micro_cues = cues
    ctx.editorial_pacing = None
    ctx.use_ai_vision = False
    ctx.effective_bgm_name = None
    ctx.mixed_audio_path = None
    ctx.transitions = None
    with ExitStack() as stack:
        stack.enter_context(patch(f"{STAGE}.SFXManager.resolve_bgm_path", return_value=None))
        stack.enter_context(patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", return_value=([], [])))
        stack.enter_context(patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]))
        ShotMatchingStage.run(ctx)
    return ctx.actual_clip_list


@pytest.fixture(scope="module")
def a6_renders(tmp_path_factory):
    """Render the stage's shot plan once per first_cue_start; return measurements."""
    from scripts.video_editor import VideoEditor

    mp = pytest.MonkeyPatch()
    mp.setenv("OMNICUT_ENCODER", "cpu")
    tmp = tmp_path_factory.mktemp("r0_a6")
    raw = tmp / "raw_index_coded.mp4"
    _write_index_coded_source(raw)
    ass = tmp / "empty.ass"
    _write_empty_ass(ass)
    results = {}
    try:
        for fcs in FIRST_CUE_STARTS:
            cue_starts = [round(fcs + CUE_LEN * i, 3) for i in range(N_CUES)]
            cues = [{"start": s, "end": round(s + CUE_LEN, 3), "text": f"cue {i}"} for i, s in enumerate(cue_starts)]
            total = round(fcs + CUE_LEN * N_CUES, 3)
            voice = tmp / f"voice_{fcs}.wav"
            _write_voice(voice, cue_starts, total)
            clips = _plan_shots(raw, cues, total)
            # Straight cuts isolate the timing question. VideoAssemblyStage would
            # swap an all-cut plan for xfades (audit A7) -- measured separately
            # in the R0 report, not asserted here.
            render_clips = [{**c, "transition_in": "cut"} for c in clips]
            for c in render_clips:
                c.pop("transition_duration", None)
            out = tmp / f"render_{fcs}.mp4"
            VideoEditor.assemble_tiktok_video(
                raw_video_paths=[str(raw)], total_duration=total, mixed_audio_path=str(voice),
                ass_subtitle_path=str(ass), output_mp4_path=str(out), clip_list=render_clips,
                transitions=["cut"] * (len(render_clips) - 1), export_preset="draft",
            )
            idx = _decoded_indices(out)
            pts = _frame_pts(out)
            # A picture change = the raw frame index stops advancing by one.
            # Frozen tail frames (same index repeated) are not shot changes.
            changes = [k for k in range(1, len(idx)) if idx[k] not in (idx[k - 1] + 1, idx[k - 1])]
            audio = _decoded_audio(out)
            results[fcs] = {
                "clips": clips,
                "cue_starts": cue_starts,
                "total": total,
                "indices": idx,
                "pts": pts,
                "change_frames": changes,
                "change_times": [pts[k] for k in changes],
                "onsets": _onsets(audio),
                "audio_duration": len(audio) / SR,
                "video_duration": pts[-1] + FRAME if pts else 0.0,
            }
        yield results
    finally:
        mp.undo()


@pytest.mark.parametrize("fcs", FIRST_CUE_STARTS, ids=lambda f: f"first_cue_start={f}")
def test_a6_voice_leads_every_picture_cut_by_j_cut_window(a6_renders, fcs):
    """At every internal boundary the next cue's voice starts 150-250 ms (J_CUT
    standard, +-1 frame of render quantisation) before the picture cuts --
    whatever the TTS lead-in silence (R2/A6: the plan now starts at 0.0)."""
    r = a6_renders[fcs]
    assert len(r["change_times"]) == N_CUES - 1, r["change_frames"]
    assert len(r["onsets"]) == N_CUES, r["onsets"]
    for boundary, (cut_t, onset) in enumerate(zip(r["change_times"], r["onsets"][1:]), start=1):
        lead = cut_t - onset
        assert 0.150 - FRAME - 1e-3 <= lead <= 0.250 + FRAME + 1e-3, (
            f"boundary {boundary}: picture {cut_t:.4f}s, voice {onset:.4f}s, lead {lead * 1000:+.0f} ms"
        )


@pytest.mark.parametrize("fcs", FIRST_CUE_STARTS)
def test_a6_render_starts_with_picture_and_matches_audio_length(a6_renders, fcs):
    """No black/empty head: frame 0 is already shot 0's first source frame, even
    while the voice is still in its leading silence; and the file's video and
    audio streams end within one frame (+ AAC padding) of each other."""
    r = a6_renders[fcs]
    first_raw_frame = round(float(r["clips"][0]["trim_start"]) * FPS)
    assert r["indices"][0] == first_raw_frame
    assert r["onsets"][0] == pytest.approx(fcs, abs=0.005)
    assert abs(r["video_duration"] - r["total"]) <= FRAME + 1e-3
    assert abs(r["audio_duration"] - r["total"]) <= 0.03


@pytest.mark.parametrize("fcs", FIRST_CUE_STARTS)
def test_a6_clips_fill_the_voice_so_no_last_frame_is_held(a6_renders, fcs):
    """R0 measured 0/3/9 frozen tail frames (fcs 0/0.1/0.3): the clips ended
    fcs early and the renderer cloned the last frame. The plan now covers the
    whole voice, so the tail keeps playing footage (allow 1 frame of B5)."""
    r = a6_renders[fcs]
    assert sum(float(c["duration"]) for c in r["clips"]) == pytest.approx(r["total"], abs=2e-3)
    idx = r["indices"]
    held = 0
    while held + 1 < len(idx) and idx[-1 - held] == idx[-2 - held]:
        held += 1
    assert held <= 1, f"{held} frozen tail frames"


# ── A7d: a transition's midpoint lands where the J-lead wants the cut ──────

def _new_shot_fraction(path, lo, hi):
    """Per output frame: share of an 18x32 grid whose decoded raw index lies in
    the incoming shot's source range [lo, hi] (a wipe is a hard edge)."""
    out = _run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=18:32:flags=neighbor",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]).stdout
    frames = np.frombuffer(out, np.uint8).reshape(-1, 32 * 18, 3)
    fractions = []
    for f in frames:
        decoded = [_decode_rgb(px) for px in f]
        fractions.append(sum(lo <= d <= hi for d in decoded) / len(decoded))
    return fractions


@pytest.mark.parametrize("fcs", (0.0, 0.3))
def test_a7d_transition_midpoint_sits_in_the_j_cut_window(tmp_path, monkeypatch, fcs):
    from scripts.stages.video_assembly_stage import _centre_transition_overlaps
    from scripts.video_editor import VideoEditor

    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    raw = tmp_path / "raw_index_coded.mp4"
    _write_index_coded_source(raw)
    ass = tmp_path / "empty.ass"
    _write_empty_ass(ass)
    cue_starts = [round(fcs + CUE_LEN * i, 3) for i in range(N_CUES)]
    cues = [{"start": s, "end": round(s + CUE_LEN, 3), "text": f"cue {i}"} for i, s in enumerate(cue_starts)]
    total = round(fcs + CUE_LEN * N_CUES, 3)
    voice = tmp_path / "voice.wav"
    _write_voice(voice, cue_starts, total)
    clips = [dict(c) for c in _plan_shots(raw, cues, total)]
    wipe = {"type": "wipeleft", "duration": 0.35}
    transitions = [dict(wipe) for _ in clips[1:]]
    for c in clips[1:]:
        c["transition_in"], c["transition_duration"] = wipe["type"], wipe["duration"]
    _centre_transition_overlaps(clips, transitions)
    out = tmp_path / "wipes.mp4"
    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(raw)], total_duration=total, mixed_audio_path=str(voice),
        ass_subtitle_path=str(ass), output_mp4_path=str(out), clip_list=clips,
        transitions=transitions, export_preset="draft",
    )
    pts = _frame_pts(out)
    onsets = _onsets(_decoded_audio(out))
    assert len(onsets) == N_CUES, onsets
    for b, clip in enumerate(clips[1:], start=1):
        lo = round(float(clip["trim_start"]) * FPS) - 2
        hi = round(float(clip["trim_end"]) * FPS) + 2
        frac = _new_shot_fraction(out, lo, hi)
        k = next(i for i in range(1, len(frac)) if frac[i] >= 0.5 and pts[i] > onsets[b] - 0.5)
        # linear interpolation of the 50 % crossing between frames k-1 and k
        a, c = frac[k - 1], frac[k]
        mid = pts[k - 1] + (0.5 - a) / max(1e-6, c - a) * (pts[k] - pts[k - 1])
        lead = mid - onsets[b]
        assert 0.150 - FRAME - 1e-3 <= lead <= 0.250 + FRAME + 1e-3, (
            f"boundary {b}: wipe midpoint {mid:.4f}s, voice {onsets[b]:.4f}s, lead {lead * 1000:+.0f} ms"
        )


# ── B(c): rendered cuts sit on the 1/30 s grid ─────────────────────────────

def _off_grid(t):
    return abs(t * FPS - round(t * FPS)) / FPS


def test_rendered_cuts_land_on_the_frame_grid(a6_renders):
    for fcs, r in a6_renders.items():
        assert r["change_times"], fcs
        for t in r["change_times"]:
            assert _off_grid(t) <= 0.001, (fcs, t)
        # The planned cuts (clips back to back) are on the grid too ...
        acc, planned = 0.0, []
        for clip in r["clips"][:-1]:
            acc += float(clip["duration"])
            planned.append(acc)
        for t in planned:
            assert _off_grid(t) <= 0.001, (fcs, planned)
        # ... and the render honours them exactly. (R0 measured +1 frame at
        # every cut: the per-clip frame count rounded up -- audit B5. Lane TM
        # lays the clips on cumulative whole-frame boundaries, so it is 0 now.)
        for want, got in zip(planned, r["change_times"]):
            assert abs(got - want) <= 1e-3, (fcs, planned, r["change_times"])


# ── B(a): split of a zoom-ramp clip renders without a seam ─────────────────

def test_split_zoom_ramp_clip_renders_seamlessly(tmp_path, monkeypatch):
    if not shutil.which("node"):
        pytest.skip("node is required to run frontend/src/lib/timelineMath.js")
    from scripts.video_editor import VideoEditor

    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    src = tmp_path / "grid.mp4"
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=white:s=270x480:r=30:d=2.5",
          "-vf", "drawgrid=w=18:h=18:t=2:c=black,drawbox=x=100:y=200:w=70:h=80:c=red:t=fill",
          "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(src)])
    wav = tmp_path / "silence.wav"
    _write_voice(wav, [], 2.0)
    ass = tmp_path / "empty.ass"
    _write_empty_ass(ass)

    clip = {"id": "orig", "source_path": str(src), "trim_start": 0.0, "trim_end": 2.0, "duration": 2.0,
            "speed": 1.0, "zoom": 1.0, "keyframes": [{"time": 0.0, "zoom": 1.0}, {"time": 2.0, "zoom": 2.0}]}
    seg = {"clip": clip, "srcDur": 2.5, "segStart": 0.0, "segEnd": 2.0}
    runner = tmp_path / "split.mjs"
    runner.write_text(
        "const lib = await import(new URL('file:///' + process.argv[2].replace(/\\\\/g, '/')).href);\n"
        "const seg = JSON.parse(process.argv[3]);\nlet n = 0;\n"
        "console.log(JSON.stringify(lib.splitClipAt(seg, Number(process.argv[4]), () => `p${++n}`)));\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["node", str(runner), str(ROOT / "frontend" / "src" / "lib" / "timelineMath.js"), json.dumps(seg), "1.0"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    left, right = json.loads(proc.stdout)
    # splitClipAt keeps the parent's `duration`; the render plays trim spans.
    for half in (left, right):
        half["duration"] = round(half["trim_end"] - half["trim_start"], 3)

    def render(name, clips):
        out = tmp_path / f"{name}.mp4"
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[str(src)], total_duration=2.0, mixed_audio_path=str(wav),
            ass_subtitle_path=str(ass), output_mp4_path=str(out), clip_list=clips,
            transitions=["cut"] * (len(clips) - 1), export_preset="draft",
        )
        return _gray_frames(out)

    mad = lambda a, b: float(np.abs(a - b).mean())  # noqa: E731 -- mean abs diff, 0-255 scale
    unsplit = render("unsplit", [clip])
    split = render("split", [left, right])
    # Pre-R1 behaviour (keyframes copied unchanged to both halves), built as
    # test data only -- proves the measurement can see a seam at all.
    naive = render("naive", [{**left, "keyframes": clip["keyframes"]}, {**right, "keyframes": clip["keyframes"]}])
    assert len(unsplit) == len(split) == len(naive) == 60

    seam = 30  # first frame of the right half
    # Tolerances (mean abs diff, 0-255): two x264 encodes of the same picture
    # differ by <= ~1 on most frames, with isolated rate-control outliers
    # measured at 5.5-6.1 (frames 35/50, both well inside the right half,
    # not at the seam). One frame of this zoom ramp moves the grid by ~25-28,
    # and the naive seam is ~80, so 8.0 per frame / 1.0 median still
    # separates "same picture" from "different zoom" cleanly.
    diffs = [mad(split[k], unsplit[k]) for k in range(len(unsplit))]
    assert max(diffs) <= 8.0, diffs
    assert float(np.median(diffs)) <= 1.0, diffs
    assert diffs[seam - 1] <= 2.0 and diffs[seam] <= 2.0, diffs[seam - 2:seam + 2]
    natural = mad(unsplit[seam - 1], unsplit[seam])
    assert abs(mad(split[seam - 1], split[seam]) - natural) <= 2.0
    # Without the R1 fix the right half restarts the ramp at zoom 1.0.
    assert mad(naive[seam], unsplit[seam]) > 10.0
    assert mad(naive[seam - 1], naive[seam]) > 2 * natural


# ── B(b): Ken Burns still images ───────────────────────────────────────────

def _circle_png(path, w, h, r=250):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(image).ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], fill="black")
    image.save(path)


def _probe_stream(path):
    out = _run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,nb_read_frames", "-of", "json", str(path)], text=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"]), int(s["nb_read_frames"])


def test_ken_burns_exact_frames_portrait_canvas_and_no_stretch(tmp_path):
    from scripts.image_motion_engine import ImageMotionEngine

    land = tmp_path / "landscape.png"
    port = tmp_path / "portrait.png"
    _circle_png(land, 1600, 900)
    _circle_png(port, 900, 1600)
    cues = [{"start": 0.0, "end": 1.6}, {"start": 1.6, "end": 3.1}]
    expected = [math.ceil((c["end"] - c["start"]) * FPS) for c in cues]  # 48, 45
    out = tmp_path / "kb" / "motion.mp4"
    ImageMotionEngine.generate_motion_video_from_images(
        [str(land), str(port)], cues, 3.1, str(out), project_dir=tmp_path / "kb",
    )
    segments = sorted((tmp_path / "kb").glob("motion_seg_*.mp4"))
    assert [_probe_stream(s) for s in segments] == [(1080, 1920, n) for n in expected]
    assert _probe_stream(out) == (1080, 1920, sum(expected))

    frames = _gray_frames(out, 1080, 1920)
    # A circle stays a circle: the dark blob's bbox in a 500x500 window at the
    # canvas centre (inside the sharp foreground for both orientations) is
    # square within 2%. The pre-R1 3:4 stretch made the landscape one ~0.42:1.
    for k in (0, expected[0] - 1, expected[0], sum(expected) - 1):
        ys, xs = np.nonzero(frames[k, 960 - 250:960 + 250, 540 - 250:540 + 250] < 80)
        w = xs.max() - xs.min() + 1
        h = ys.max() - ys.min() + 1
        assert abs(w / h - 1.0) <= 0.02, (k, w, h)

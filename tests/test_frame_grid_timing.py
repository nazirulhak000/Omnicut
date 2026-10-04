"""Whole-frame clip timing, preview == render (EDITOR-CUT-QUALITY-R2 lane TM, audit B5).

Every clip chain used to come out as ~round(duration*30) frames, so the
per-clip rounding error added up along the sequence (measured +0.04..+1.52
frames over 12-24 clips) while the preview kept the exact float. The render
now quantises CUMULATIVE boundaries (boundary_k = floor(cumsum_k*30 + 0.5),
every length a difference of two boundaries, transition offset/duration on the
same grid). frontend/src/lib/timelineMath.js planSequenceFrames() is the same
function; tests/test_preview_render_parity.py feeds both one clip list.

Offline and deterministic: lavfi/rawvideo synthetic media, outputs only under
pytest's tmp_path.
"""
import math
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.video_editor import (  # noqa: E402
    VideoEditor,
    frames_to_seconds,
    plan_sequence_frames,
    sequence_frame_index,
)

FPS = 30
CUT = {"type": "cut"}

needs_ffmpeg = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and FFprobe are required for real-render measurements",
)


# ---------------------------------------------------------------- pure math
def _half_up(x):
    return int(math.floor(x + 0.5))


def test_cumulative_boundaries_never_accumulate_rounding_error():
    # 24 clips of 1.0167 s: rounding each clip alone gives 31 frames apiece
    # (744) while the true total is 732.0 frames -- the pre-B5 render drift.
    durs = [1.0167] * 24
    plan = plan_sequence_frames(durs, [CUT] * 23)
    assert sum(_half_up(d * FPS) for d in durs) == 744
    assert plan["end"][-1] == _half_up(sum(durs) * FPS) == 732
    acc = 0.0
    for i, d in enumerate(durs):
        acc += d
        assert plan["end"][i] == _half_up(acc * FPS)
        assert abs(plan["end"][i] - acc * FPS) <= 0.5 + 1e-9
        assert plan["start"][i] == (plan["end"][i - 1] if i else 0)
        assert plan["overlap"][i] == 0


def test_every_clip_keeps_at_least_one_frame_and_the_chain_stays_in_order():
    # (the editor never goes below MIN_CLIP_DURATION 0.2 s; 0.01 s is the
    # degenerate case that proves the floor)
    plan = plan_sequence_frames([0.01, 0.01, 0.2, 0.2], [CUT, CUT, {"type": "fade", "duration": 0.4}])
    for s, e in zip(plan["start"], plan["end"]):
        assert e - s >= 1
    assert plan["end"] == sorted(plan["end"])
    assert plan["start"][3] <= plan["end"][2] - 1 and plan["overlap"][3] >= 1


def test_transition_offset_is_boundary_minus_overlap_on_whole_frames():
    durs = [1.03, 0.987, 1.2111, 0.95]
    bounds = [{"type": "fade", "duration": 0.4}, CUT, {"type": "slideleft", "duration": 0.3333}]
    plan = plan_sequence_frames(durs, bounds)
    assert plan["overlap"][1] == 12 and plan["overlap"][2] == 0 and plan["overlap"][3] == 10
    for i in (1, 3):
        assert plan["start"][i] == plan["end"][i - 1] - plan["overlap"][i]
    assert frames_to_seconds(plan["start"][1]) == pytest.approx(plan["start"][1] / FPS, abs=1e-6)


def test_transition_clamp_matches_the_old_float_rule_and_never_empties_a_clip():
    plan = plan_sequence_frames([1.0, 1.0], [{"type": "circleopen", "duration": 2.0}])
    # min(clip) - 0.05 = 0.95 s -> offset 0.05 s -> frame round(1.5) = 2
    assert plan["start"][1] == 2 and plan["overlap"][1] == 28
    assert plan["end"][1] - plan["start"][1] > plan["overlap"][1]


def test_sequence_frame_index_rounds_halves_up():
    assert sequence_frame_index(0.05) == 2
    assert sequence_frame_index(1 / 60 - 1e-9) == 0


def test_saved_project_total_moves_at_most_one_frame_against_the_old_render():
    """The old render summed per-clip round(); the new one rounds the sum. For
    any plausible clip list the two differ by well under one frame per ~half
    the clips, and the new total is always within half a frame of the float
    model the preview used (the 'saved project total moves <= 1 frame' gate:
    the float model is the one a saved project's length was measured with)."""
    rng = np.random.default_rng(20261004)
    for _ in range(200):
        n = int(rng.integers(3, 25))
        durs = [round(float(x), 3) for x in rng.uniform(0.4, 2.6, n)]
        plan = plan_sequence_frames(durs, [CUT] * (n - 1))
        assert abs(plan["end"][-1] - sum(durs) * FPS) <= 0.5 + 1e-9


# ------------------------------------------------------------ graph capture
class _Done:
    returncode = 0
    stdout = ""
    stderr = ""


def capture_graph(tmp_path, monkeypatch, clip_list, transitions, total_duration):
    """Assemble the ffmpeg command without running it; return the filtergraph."""
    monkeypatch.setattr(
        VideoEditor, "get_media_info",
        classmethod(lambda cls, path: {"duration": 30.0, "width": 1080, "height": 1920, "fps": 30.0}),
    )
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    captured = {}

    def fake_run(cmd, *args, **kwargs):
        if cmd and "ffmpeg" in str(cmd[0]).lower():
            captured["cmd"] = list(cmd)
        return _Done()

    monkeypatch.setattr("scripts.video_editor.subprocess.run", fake_run)
    audio = tmp_path / "mixed.wav"
    audio.write_bytes(b"fake")
    subs = tmp_path / "subs.ass"
    subs.write_text("[Script Info]\n", encoding="utf-8")
    try:
        VideoEditor.assemble_tiktok_video(
            raw_video_paths=[c["source_path"] for c in clip_list],
            total_duration=total_duration, mixed_audio_path=str(audio),
            ass_subtitle_path=str(subs), output_mp4_path=str(tmp_path / "out.mp4"),
            clip_list=clip_list, transitions=transitions,
        )
    except Exception:
        pass  # the stub writes no output; the argv is what is read
    cmd = captured.get("cmd")
    assert cmd, "ffmpeg was never invoked"
    return cmd[cmd.index("-filter_complex") + 1]


def _fake_clips(tmp_path, specs):
    clips = []
    for i, (start, end, extra) in enumerate(specs):
        src = tmp_path / f"c{i}.mp4"
        src.write_bytes(b"fake")
        clips.append({"source_path": str(src), "trim_start": start, "trim_end": end, **extra})
    return clips


def graph_frames(graph):
    """Per-clip start/end/overlap frames as the filtergraph spells them."""
    lengths = [int(n) for n in re.findall(r"trim=end_frame=(\d+)\[", graph)]
    steps = []
    for part in graph.split(";"):
        if "xfade=" in part:
            m = re.search(r":duration=([\d.]+):offset=([\d.]+),setsar=1,fps=30\[", part)
            assert m, part[:200]
            steps.append((float(m.group(1)), float(m.group(2))))
        elif "concat=n=2" in part:
            steps.append(None)
    assert len(steps) == len(lengths) - 1
    start, end, overlap = [0], [lengths[0]], [0]
    for i, step in enumerate(steps, start=1):
        if step:
            dur, off = step
            s = _half_up(off * FPS)
            assert abs(off * FPS - s) < 1e-4, f"offset {off} is off the frame grid"
            assert abs(dur * FPS - _half_up(dur * FPS)) < 1e-4
            start.append(s)
            overlap.append(end[i - 1] - s)
            assert _half_up(dur * FPS) == overlap[i]
        else:
            start.append(end[i - 1])
            overlap.append(0)
        end.append(start[i] + lengths[i])
    return {"start": start, "end": end, "overlap": overlap}


def test_clip_chain_graph_carries_the_frame_plan(tmp_path, monkeypatch):
    durs = [1.017, 0.983, 1.05, 0.967, 1.0, 1.013, 1.021, 0.989]
    clips = _fake_clips(tmp_path, [(0.2 * i, 0.2 * i + d, {}) for i, d in enumerate(durs)])
    transitions = [
        {"type": "wipeleft", "duration": 0.4}, "cut", {"type": "fade", "duration": 0.35},
        "cut", {"type": "slideup", "duration": 0.3, "easing": "ease_in_out"},
        "cut", {"type": "fadeblack", "duration": 0.4},
    ]
    graph = capture_graph(tmp_path, monkeypatch, clips, transitions, sum(durs))
    from scripts.video_editor import normalize_transitions
    plan = plan_sequence_frames(durs, normalize_transitions(transitions))
    assert graph_frames(graph) == plan
    # An eased boundary renders as a custom expression; the others stay built-in.
    assert graph.count("xfade=transition=custom:expr=") == 1
    assert "xfade=transition=wipeleft:duration=0.4:offset=" in graph


def test_linear_and_unsupported_easing_leave_the_graph_text_unchanged(tmp_path, monkeypatch):
    durs = [1.2, 1.2, 1.2]
    clips = _fake_clips(tmp_path, [(0.0, d, {}) for d in durs])
    base = [{"type": "slideleft", "duration": 0.4}, {"type": "circleopen", "duration": 0.4}]
    reference = capture_graph(tmp_path, monkeypatch, clips, base, sum(durs))
    for variant in (
        [{**base[0], "easing": "linear"}, base[1]],
        [{**base[0], "easing": "nonsense"}, base[1]],
        [base[0], {**base[1], "easing": "ease_in_out"}],   # circleopen ignores easing
    ):
        assert capture_graph(tmp_path, monkeypatch, clips, variant, sum(durs)) == reference


# ------------------------------------------------------------- real render
def _code_rgb(i):
    return (32 * (i % 8) + 16, 32 * ((i // 8) % 8) + 16, 32 * ((i // 64) % 8) + 16)


def _decode_rgb(rgb):
    q = [int(min(7, max(0, round((float(c) - 16) / 32)))) for c in rgb]
    return q[0] + 8 * q[1] + 64 * q[2]


def _run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, capture_output=True, **kwargs)


def write_index_coded_source(path, fps, n_frames=510, w=96, h=160):
    """Every frame is one flat colour naming its own index (8x8x8 = 512)."""
    frames = np.zeros((n_frames, h, w, 3), np.uint8)
    for i in range(n_frames):
        frames[i, :, :] = _code_rgb(i)
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
          "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-qp", "0",
          "-pix_fmt", "yuv444p", str(path)], input=frames.tobytes())


def _write_silence(path, seconds, sr=48000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x00\x00" * int(round(seconds * sr)))


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


# 12 ~1 s clips, none a whole number of frames (30.51, 29.49, 31.41, 29.01 ...)
# and none landing a cumulative boundary on an exact half frame, alternating a
# 30 fps and a 25 fps source.
DURATIONS = [1.017, 0.983, 1.047, 0.967, 1.004, 1.013, 1.021, 0.989, 1.034, 0.975, 1.008, 1.041]
SOURCE_FPS = [30, 25] * 6
BASE = [40 * i + 5 for i in range(12)]  # disjoint raw-index range per clip


def chain_clips(sources):
    clips = []
    for i, d in enumerate(DURATIONS):
        fps = SOURCE_FPS[i]
        # 0.3 of a frame early: the input seek lands on frame BASE[i] exactly,
        # whatever 3-decimal rounding does to the -ss argument.
        start = (BASE[i] - 0.3) / fps
        clips.append({"source_path": str(sources[fps]), "trim_start": start, "trim_end": start + d})
    return clips


def played_durations(clips):
    """What the builder (and the preview) read off each clip: the float
    difference of its own trim points, exactly as stored."""
    return [max(0.2, float(c["trim_end"]) - float(c["trim_start"])) for c in clips]


def _grid_indices(path):
    """Per output frame, the raw index every cell of a 72x128 grid decodes to
    (a flat colour names its raw frame; each clip's index range is disjoint)."""
    out = _run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=72:128:flags=neighbor",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]).stdout
    frames = np.frombuffer(out, np.uint8).reshape(-1, 72 * 128, 3).astype(np.float32)
    q = np.clip(np.rint((frames - 16.0) / 32.0), 0, 7).astype(np.int32)
    return q[..., 0] + 8 * q[..., 1] + 64 * q[..., 2]


def _share(idx_frame, clip):
    return float(((idx_frame >= BASE[clip]) & (idx_frame < BASE[clip] + 40)).mean())


def _grid_owners(grid, min_share=0.03):
    """Per output frame: the clips that own at least `min_share` of the frame.
    A wipe/slide edge column straddles two flat colours and can decode to
    anything, but it is ~1 % of the frame, well under `min_share`."""
    return [{i for i in range(len(BASE)) if _share(row, i) >= min_share} for row in grid]


def _nb_frames(path):
    out = _run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)], text=True).stdout
    return int(out.strip().strip(","))


def _float_model_total(durs, boundaries):
    """The preview's exact-float timeline length (no frame grid)."""
    acc = 0.0
    for i, d in enumerate(durs):
        b = boundaries[i - 1] if i else None
        if b and b["type"] != "cut":
            fade = min(b["duration"], max(0.05, min(acc, d) - 0.05))
            acc = acc - fade + d
        else:
            acc += d
    return acc


@pytest.fixture(scope="module")
def chain_sources(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("grid_src")
    sources = {}
    for fps in (30, 25):
        sources[fps] = tmp / f"src{fps}.mp4"
        write_index_coded_source(sources[fps], fps)
    silence = tmp / "silence.wav"
    _write_silence(silence, 20.0)
    ass = tmp / "empty.ass"
    _write_empty_ass(ass)
    return {"sources": sources, "silence": silence, "ass": ass}


def render_chain(editor, tmp_path, media, transitions, name="chain.mp4"):
    """Render the 12 synthetic clips through `editor` (VideoEditor or the HEAD
    copy) and return the measurements."""
    from scripts.video_editor import normalize_transitions

    clips = chain_clips(media["sources"])
    boundaries = normalize_transitions(transitions)
    durs = played_durations(clips)
    total = _float_model_total(durs, boundaries)
    out = tmp_path / name
    editor.assemble_tiktok_video(
        raw_video_paths=[str(media["sources"][30])], total_duration=total,
        mixed_audio_path=str(media["silence"]), ass_subtitle_path=str(media["ass"]),
        output_mp4_path=str(out), clip_list=clips, transitions=transitions, export_preset="draft",
    )
    grid = _grid_indices(out)
    return {
        "out": out, "total": total, "frames": _nb_frames(out), "durs": durs,
        "grid": grid, "owners": _grid_owners(grid), "boundaries": boundaries,
    }


def _first_frame_of(owners, clip, only=False):
    for k, seen in enumerate(owners):
        if clip in seen and (not only or seen == {clip}):
            return k
    return None


@pytest.fixture(autouse=True)
def _cpu_encoder(monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")


@pytest.mark.render_regression
@needs_ffmpeg
def test_twelve_clip_cut_chain_lands_every_boundary_on_the_frame_model(tmp_path, chain_sources):
    r = render_chain(VideoEditor, tmp_path, chain_sources, ["cut"] * 11)
    expected_starts, acc = [0], 0.0
    for d in r["durs"][:-1]:
        acc += d
        expected_starts.append(_half_up(acc * FPS))
    assert r["frames"] == _half_up(r["total"] * FPS)
    for i, want in enumerate(expected_starts):
        assert _first_frame_of(r["owners"], i, only=True) == want, (i, want)
    # nothing else on screen: every frame is exactly one clip
    assert all(len(s) == 1 for s in r["owners"])


@pytest.mark.render_regression
@needs_ffmpeg
def test_twelve_clip_transition_chain_keeps_total_and_transition_start(tmp_path, chain_sources):
    transitions = [
        {"type": "wipeleft", "duration": 0.4}, "cut",
        {"type": "slideup", "duration": 0.3}, {"type": "fade", "duration": 0.35},
        "cut", {"type": "wiperight", "duration": 0.4},
        {"type": "circleopen", "duration": 0.3}, "cut",
        {"type": "wipedown", "duration": 0.4, "easing": "ease_in_out"},
        {"type": "fadeblack", "duration": 0.4},
        {"type": "slideleft", "duration": 0.35, "easing": "ease_out"},
    ]
    r = render_chain(VideoEditor, tmp_path, chain_sources, transitions)
    from scripts.video_editor import plan_sequence_frames as plan_fn
    plan = plan_fn(r["durs"], r["boundaries"])
    assert r["frames"] == plan["end"][-1] == _half_up(r["total"] * FPS)
    for i, b in enumerate(r["boundaries"], start=1):
        if b["type"] == "cut":
            # hard cut: from this frame on the picture is clip i alone
            assert _first_frame_of(r["owners"], i) == plan["start"][i], i
        elif b["type"].startswith(("wipe", "slide")) and "easing" not in b:
            # xfade shows nothing of B at progress 0 and the first sliver one
            # frame later: the transition starts exactly at the planned offset
            assert _first_frame_of(r["owners"], i) == plan["start"][i] + 1, (i, b)
        if b["type"].startswith(("wipe", "slide")):
            # B covers a share of the frame equal to the (eased) transition
            # progress -- inside the full 12-clip chain, at every frame of it.
            from scripts.video_editor import ease_camera_ratio
            n = plan["overlap"][i]
            for k in range(1, n):
                want = ease_camera_ratio(b.get("easing", "linear"), k / n)
                got = _share(r["grid"][plan["start"][i] + k], i)
                assert abs(got - want) <= 0.04, (i, b, k, got, want)

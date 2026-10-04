"""Eased transition progress (EDITOR-CUT-QUALITY-R2 lane TM spike).

Real-render proof, not a source read:
1. For every type in EASED_TRANSITIONS the custom xfade expression evaluated
   at LINEAR progress reproduces ffmpeg's built-in transition (that is what
   makes "the same geometry at an eased progress" a true statement).
2. An eased render, measured at 25/50/75 % of the transition, lands where the
   preview math (timelineMath.js easing + SequencePlayer geometry) puts it.
3. Linear/absent easing leaves the filter text byte-identical to the
   built-in form old projects always rendered.
Offline: lavfi sources only, outputs in tmp_path.
"""
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from scripts.video_editor import (
    EASED_TRANSITIONS,
    XFADE_TRANSITIONS,
    ease_camera_ratio,
    eased_xfade_custom_expr,
    normalize_transitions,
    transition_easing_name,
    xfade_custom_body,
    xfade_filter_args,
)

ROOT = Path(__file__).resolve().parent.parent
JS_SRC = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
TM_SRC = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")

W, H = 216, 384
FPS = 30
OFFSET_FRAMES = 30
FRAMES = 12            # 0.4 s transition -> 25/50/75 % are whole frames 3/6/9
SAMPLES = (3, 6, 9)

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


# ------------------------------------------------------------ source contracts
def test_eased_types_match_on_both_sides():
    js = re.search(r"EASED_TRANSITIONS = \[(.*?)\];", TM_SRC, re.S).group(1)
    assert tuple(re.findall(r"'(\w+)'", js)) == EASED_TRANSITIONS
    assert set(EASED_TRANSITIONS) <= set(XFADE_TRANSITIONS)
    for kind in ("dissolve", "circleopen", "circleclose"):
        assert kind not in EASED_TRANSITIONS


def test_linear_keeps_the_exact_builtin_filter_text():
    for kind in XFADE_TRANSITIONS:
        old = f"xfade=transition={kind}:duration=0.4:offset=1.6"
        assert xfade_filter_args(kind, 0.4, 1.6) == old
        assert xfade_filter_args(kind, 0.4, 1.6, "linear") == old
        assert xfade_filter_args(kind, 0.4, 1.6, "nonsense") == old
    # Types that do not honour easing ignore it entirely.
    assert xfade_filter_args("dissolve", 0.4, 1.6, "ease_in_out") == "xfade=transition=dissolve:duration=0.4:offset=1.6"
    assert normalize_transitions([{"type": "fade", "duration": 0.4}]) == [{"type": "fade", "duration": 0.4}]
    assert normalize_transitions([{"type": "fade", "duration": 0.4, "easing": "linear"}]) == [{"type": "fade", "duration": 0.4}]
    assert normalize_transitions([{"type": "circleopen", "easing": "ease_out"}]) == [{"type": "circleopen", "duration": 0.4}]
    assert normalize_transitions([{"type": "wipeup", "easing": "ease_out"}])[0]["easing"] == "ease_out"


def test_progress_expression_is_the_camera_curve_reversed():
    """xfade's P runs 1 -> 0; E must equal 1 - ease(1 - P) for every curve."""
    exprs = {
        "ease_in": ("(P*(2-P))", lambda P: P * (2 - P)),
        "ease_out": ("(P*P)", lambda P: P * P),
        "ease_in_out": ("(if(gt(P,0.5),1-2*(1-P)*(1-P),2*P*P))",
                        lambda P: 1 - 2 * (1 - P) * (1 - P) if P > 0.5 else 2 * P * P),
    }
    for name, (text, fn) in exprs.items():
        assert eased_xfade_custom_expr("fade", name) == f"A*{text}+B*(1-{text})"
        for P in [i / 24 for i in range(25)]:
            assert math.isclose(fn(P), 1 - ease_camera_ratio(name, 1 - P), abs_tol=1e-12)
    assert transition_easing_name("slideup", "ease_in") == "ease_in"
    assert transition_easing_name("dissolve", "ease_in") == "linear"


# ------------------------------------------------------------ real renders
def _render(tmp_path, a_src, b_src, transition_arg):
    out = tmp_path / "out.yuv"
    graph = (
        f"[0:v]format=yuv420p,setsar=1[a];[1:v]format=yuv420p,setsar=1[b];"
        f"[a][b]{transition_arg}:duration={FRAMES / FPS}:offset={OFFSET_FRAMES / FPS},"
        f"format=yuv444p[o]"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", a_src, "-f", "lavfi", "-i", b_src,
         "-filter_complex", graph, "-map", "[o]", "-f", "rawvideo", str(out)],
        check=True,
    )
    data = np.fromfile(out, dtype=np.uint8).reshape(-1, 3, H, W)
    out.unlink()
    return data


def _src(expr_or_color):
    if expr_or_color.startswith("geq"):
        return f"color=c=gray:s={W}x{H}:r={FPS}:d=2,format=yuv444p,{expr_or_color}"
    return f"color=c={expr_or_color}:s={W}x{H}:r={FPS}:d=2"


TEXTURE_A = "testsrc2=s=216x384:r=30:d=2"
TEXTURE_B = "mandelbrot=s=216x384:r=30,trim=duration=2"


def _best_shift_mismatch(ref, cus, axis):
    """Fraction of pixels off by >1 after the best of -1/0/+1 px shifts --
    the custom expression truncates W*P in double, xfade in float, which can
    move one edge by a single pixel on frames where W*P lands on an integer."""
    best = 1.0
    for s in (-1, 0, 1):
        diff = np.abs(np.roll(cus.astype(int), s, axis=axis) - ref.astype(int)) > 1
        best = min(best, diff.mean())
    return best


@needs_ffmpeg
@pytest.mark.parametrize("kind", EASED_TRANSITIONS)
def test_custom_expression_at_linear_progress_is_the_builtin(tmp_path, kind):
    ref = _render(tmp_path, TEXTURE_A, TEXTURE_B, f"xfade=transition={kind}")
    cus = _render(tmp_path, TEXTURE_A, TEXTURE_B,
                  f"xfade=transition=custom:expr='{xfade_custom_body(kind, '(P)')}'")
    assert ref.shape == cus.shape
    worst = 0.0
    for f in range(OFFSET_FRAMES, OFFSET_FRAMES + FRAMES):
        if kind.startswith(("fade",)):
            assert np.abs(ref[f].astype(int) - cus[f].astype(int)).max() <= 1, f"{kind} frame {f}"
        else:
            axis = 2 if kind.endswith(("left", "right")) else 1
            worst = max(worst, _best_shift_mismatch(ref[f], cus[f], axis))
    # A single wrapped column/row at P=1 is the only other difference.
    assert worst <= 1.5 / min(W, H), f"{kind}: {worst:.4%} pixels differ beyond a 1 px edge shift"


def _ease(name, p):
    return ease_camera_ratio(name, p)


def _smoothstep(x):
    c = min(1.0, max(0.0, x))
    return c * c * (3 - 2 * c)


def _preview_bridge(q):
    """SequencePlayer.jsx bridgeWeights(), same arithmetic, phase read from it."""
    phase = float(re.search(r"FADE_BRIDGE_PHASE = ([\d.]+);", JS_SRC).group(1))
    P = 1 - min(1.0, max(0.0, q))
    s_out = _smoothstep((P - (1 - phase)) / phase)
    s_in = _smoothstep((P - phase) / (1 - phase))
    w_a = P * s_out
    w_b = (1 - P) * (1 - s_in)
    return w_a, w_b, max(0.0, 1 - w_a - w_b)


MEASURED = {}


@needs_ffmpeg
@pytest.mark.parametrize("easing", ["linear", "ease_in", "ease_out", "ease_in_out"])
@pytest.mark.parametrize("kind", ["fade", "fadeblack", "fadewhite"])
def test_eased_fades_match_preview_weights(tmp_path, kind, easing):
    ya, yb = 64, 192
    out = _render(tmp_path, _src("0x404040"), _src("0xC0C0C0"),
                  xfade_filter_args(kind, FRAMES / FPS, OFFSET_FRAMES / FPS, easing).split(":duration")[0])
    a_y = float(out[OFFSET_FRAMES - 1, 0].mean())
    b_y = float(out[-1, 0].mean())
    errs = []
    for k in SAMPLES:
        q = _ease(easing, k / FRAMES)
        y = float(out[OFFSET_FRAMES + k, 0].mean())
        if kind == "fade":
            pred = a_y * (1 - q) + b_y * q
        else:
            w_a, w_b, bridge = _preview_bridge(q)
            k_y = 0.0 if kind == "fadeblack" else 255.0   # xfade's own bridge level
            pred = w_a * a_y + w_b * b_y + bridge * k_y
        errs.append(abs(y - pred) / abs(b_y - a_y) if kind == "fade" else abs(y - pred) / 255)
    MEASURED[(kind, easing)] = max(errs)
    # fade: preview == render to rounding. fadeblack/fadewhite: bounded by the
    # preview's documented bridge approximation (preview_render_parity.md §7).
    limit = 0.01
    assert max(errs) <= limit, f"{kind}/{easing}: {errs}"


@needs_ffmpeg
@pytest.mark.parametrize("easing", ["linear", "ease_in", "ease_out", "ease_in_out"])
@pytest.mark.parametrize("kind", ["wipeleft", "wiperight", "wipeup", "wipedown",
                                  "slideleft", "slideright", "slideup", "slidedown"])
def test_eased_wipes_and_slides_match_preview_geometry(tmp_path, kind, easing):
    horizontal = kind.endswith(("left", "right"))
    size = W if horizontal else H
    if kind.startswith("slide"):
        # A carries its own coordinate (0..200 along the travel axis), B is flat 250.
        coord = "X" if horizontal else "Y"
        a_src = _src(f"geq=lum='{coord}*200/({'W' if horizontal else 'H'}-1)':cb=128:cr=128")
        b_src = _src("geq=lum=250:cb=128:cr=128")
    else:
        a_src, b_src = _src("black"), _src("white")
    out = _render(tmp_path, a_src, b_src,
                  xfade_filter_args(kind, FRAMES / FPS, OFFSET_FRAMES / FPS, easing).split(":duration")[0])
    errs = []
    for k in SAMPLES:
        q = _ease(easing, k / FRAMES)
        y = out[OFFSET_FRAMES + k, 0].astype(float)
        line = y[H // 2, :] if horizontal else y[:, W // 2]
        is_b = line > 235 if kind.startswith("slide") else line > 128
        b_extent = float(is_b.sum())
        # Preview: B owns q*size along the travel axis (rect for wipes,
        # (1-q)*size offset for slides) -- SequencePlayer clipIncomingRegion /
        # slideOffsets with the eased q.
        err = abs(b_extent - q * size)
        if kind.startswith("slide"):
            # A's displacement: the source coordinate each A pixel shows.
            idx = np.nonzero(~is_b)[0]
            src = line[idx] * (size - 1) / 200
            sign = -1 if kind in ("slideleft", "slideup") else 1
            shift = float(np.median(idx - src))
            err = max(err, abs(shift - sign * q * size))
        errs.append(err)
    MEASURED[(kind, easing)] = max(errs)
    # Tolerance: preview_render_parity.md §7.2 measured slide <= 1.8 px and
    # wipe <= 1 column on the built-ins; + 1 px for the truncation of W*E.
    assert max(errs) <= 2.0, f"{kind}/{easing}: {errs} px"

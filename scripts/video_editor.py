import atexit
import subprocess
import json
import math
import os
import re
import sys
import threading
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass
from typing import Any, List, Dict, Tuple, Callable, Optional
from scripts.config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    FPS,
    MIN_SHOT_DURATION,
    MAX_SHOT_DURATION,
    FONTS_DIR,
    STICKERS_DIR,
    EFFECTS_DIR,
    PROJECTS_DIR,
)
from scripts.overlay_recolor import (
    build_overlay_hue_filter,
    overlay_asset_recolor_metadata,
    resolve_overlay_recolor,
)
from scripts.spotlight_effect import build_ffmpeg_filter
from scripts.proxy_manager import is_proxy_path
from scripts.render_jobs import RenderCancelled
from scripts.ffmpeg_graph import cleanup_graph_file, externalize_filter_graph

# Above this speed, duplicated frames are not visible enough to be worth
# minterpolate's cost, so the smooth-slowmo flag is ignored.
SMOOTH_SLOWMO_MAX_SPEED = 0.7
from scripts.media_probe_cache import MediaProbeCache
from scripts.style_motion_policy import STYLE_MOTION_POLICIES
from scripts.background_isolation_compositor import (
    build_alpha_composite_filter_fragment,
    build_compositing_plan,
    normalize_compositor_config,
    resolve_background_isolation_config,
    split_ass_layers_for_subject,
)
from scripts.background_isolation_video_worker import VIDEO_NAMESPACE, VIDEO_NAME, VIDEO_SCHEMA_VERSION

# ffmpeg child processes spawned for the final render, tracked so a hard
# external kill of this backend (task manager, a dev-server reload, an
# uncaught exception unwinding to interpreter exit) doesn't leave one
# orphaned and still holding a write handle on its output file -- which
# makes the next render attempt hit a Windows file-lock error or produce a
# corrupt .mp4. Each render registers itself here on spawn and unregisters
# on its own normal cleanup; whatever is left when the interpreter exits
# gets a best-effort terminate/kill below. This only covers exits the
# interpreter gets to run code for (normal exit, unhandled exception,
# Ctrl+C) -- a bare TerminateProcess/kill -9 on this process can't run any
# Python code at all, atexit included.
_active_ffmpeg_procs: set = set()
_active_ffmpeg_procs_lock = threading.Lock()

_BACKGROUND_SEQUENCE_NAMESPACE = "background-isolation-foreground-sequences"
_BACKGROUND_SEQUENCE_ID_RE = re.compile(r"^bgseq1-[0-9a-f]{16}$")
_BACKGROUND_FRAME_RE = re.compile(r"^frame_([0-9]{6})\.png$")
_BACKGROUND_ISOLATION_KEY = "background_" + "isolation"
# Canvas blur(12px) is applied on a 540x960 transparent draw surface before
# compositing over black. At render resolution, a black pad plus sigma 20
# reproduces both its soft edges and the blurred frame interior.
_BACKGROUND_BLUR_PAD = 72
_BACKGROUND_BLUR_FILTER = (
    f"pad={VIDEO_WIDTH + 2 * _BACKGROUND_BLUR_PAD}:{VIDEO_HEIGHT + 2 * _BACKGROUND_BLUR_PAD}:"
    f"{_BACKGROUND_BLUR_PAD}:{_BACKGROUND_BLUR_PAD}:color=black,"
    "gblur=sigma=20,"
    f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{_BACKGROUND_BLUR_PAD}:{_BACKGROUND_BLUR_PAD}"
)


def _write_subject_ass_layers(ass_subtitle_path: str) -> tuple[Path, Path]:
    """Create temporary ASS passes so Hook text can sit behind the Subject."""

    source = Path(ass_subtitle_path).resolve()
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    hook_lines, foreground_lines = split_ass_layers_for_subject(lines)
    hook_path = source.with_name(f"{source.stem}_subject_hook.ass")
    foreground_path = source.with_name(f"{source.stem}_subject_foreground.ass")
    for path, payload in ((hook_path, hook_lines), (foreground_path, foreground_lines)):
        path.write_text("\n".join(payload) + "\n", encoding="utf-8")
    return hook_path, foreground_path


def _background_sequence_root() -> Path:
    """Return the only cache root accepted by the renderer.

    The renderer intentionally derives this path from the project root and
    sequence id.  A render payload can select an artifact, but can never
    redirect FFmpeg to an arbitrary absolute path.
    """

    return (PROJECTS_DIR / ".cache" / _BACKGROUND_SEQUENCE_NAMESPACE).resolve()


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _read_ready_background_video(
    config: Mapping[str, Any], artifact_id: str, trim_start: float, source_span: float,
) -> Optional[Dict[str, Any]]:
    root = Path(PROJECTS_DIR).resolve(strict=False) / ".cache" / VIDEO_NAMESPACE
    directory = root / artifact_id
    manifest_path = directory / "manifest.json"
    video_path = directory / VIDEO_NAME
    if any(path.is_symlink() for path in (root, directory, manifest_path, video_path)):
        return None
    if not manifest_path.is_file() or not video_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("schema_version") != VIDEO_SCHEMA_VERSION
                or manifest.get("artifact_id") != artifact_id
                or manifest.get("status") != "ready"
                or manifest.get("video_file") != VIDEO_NAME
                or manifest.get("codec") != "vp9-alpha"):
            return None
        if config.get("scope_mode") == "behind_text_windows":
            artifact = config.get("artifact")
            if not isinstance(artifact, Mapping) or artifact.get("status") != "ready":
                return None
            requested = config.get("active_intervals")
            if not isinstance(requested, list) or [
                [item.get("start"), item.get("end")] for item in requested if isinstance(item, Mapping)
            ] != manifest.get("active_intervals") or any(not isinstance(item, Mapping) for item in requested):
                return None
        fingerprint = config.get("artifact", {}).get("source_fingerprint")
        if fingerprint and fingerprint != manifest.get("source_fingerprint"):
            return None
        fps = Fraction(str(manifest["fps"]))
        frame_count = int(manifest["frame_count"])
        width = int(manifest["width"])
        height = int(manifest["height"])
        source_start = float(manifest["source_start"])
        source_duration = float(manifest["source_duration"])
        local_start = float(trim_start) - source_start
        if (fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0
                or local_start < -1e-6 or source_span <= 0
                or local_start + source_span > source_duration + 1 / float(fps) + 1e-6):
            return None
        if video_path.stat().st_size == 0:
            return None
    except (OSError, KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    return {
        "artifact_id": artifact_id, "video_path": video_path,
        "video_start": max(0.0, local_start), "fps_ratio": str(manifest["fps"]),
        "frame_count": frame_count, "width": width, "height": height,
        "manifest": manifest,
        "plan": {"filter_fragment": build_alpha_composite_filter_fragment()},
    }


def _read_ready_background_sequence(
    config: Any,
    trim_start: float,
    source_span: float,
) -> Optional[Dict[str, Any]]:
    """Validate a derived RGBA sequence and return render-only metadata.

    This is deliberately fail-closed.  Invalid config, stale/missing
    manifests, symlinks, incomplete frame ranges, non-RGBA frames, and a
    sequence too short for the requested source span all return ``None`` so
    the caller remains on the original graph.
    """

    if not isinstance(config, Mapping):
        return None
    artifact = config.get("artifact")
    artifact_id = artifact.get("sequence_id", artifact.get("id")) if isinstance(artifact, Mapping) else None
    if (
        not isinstance(artifact_id, str)
        or not _BACKGROUND_SEQUENCE_ID_RE.fullmatch(artifact_id)
    ):
        return None

    video_info = _read_ready_background_video(config, artifact_id, trim_start, source_span)
    if video_info is not None:
        return video_info
    if config.get("scope_mode") == "behind_text_windows":
        return None

    root = _background_sequence_root()
    artifact_dir = (root / artifact_id).resolve(strict=False)
    frames_dir = (artifact_dir / "frames").resolve(strict=False)
    manifest_path = (artifact_dir / "manifest.json").resolve(strict=False)
    # Older/informal callers sometimes included a concrete frames path in
    # their payload.  Accept it only as an exact, derived-path assertion; it
    # must never become the path FFmpeg actually opens.
    for path_value in (
        config.get("frames_path"),
        config.get("foreground_path"),
        (config.get("sequence") or {}).get("frames_path")
        if isinstance(config.get("sequence"), Mapping)
        else None,
        (config.get("sequence") or {}).get("frames_dir")
        if isinstance(config.get("sequence"), Mapping)
        else None,
        (config.get("artifact") or {}).get("frames_path")
        if isinstance(config.get("artifact"), Mapping)
        else None,
    ):
        if path_value is None:
            continue
        try:
            if Path(path_value).expanduser().resolve(strict=False) != frames_dir:
                return None
        except (TypeError, ValueError, OSError):
            return None
    if not (_path_is_under(artifact_dir, root) and _path_is_under(frames_dir, root)):
        return None
    if any(path.is_symlink() for path in (root, artifact_dir, frames_dir, manifest_path)):
        return None
    if not manifest_path.is_file() or not frames_dir.is_dir():
        return None

    try:
        disk_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        disk_config = normalize_compositor_config(config, disk_manifest)
    except Exception:
        return None
    if not disk_config.get("enabled") or not disk_config.get("ready"):
        return None
    disk_sequence = disk_config.get("sequence")
    if not isinstance(disk_sequence, Mapping) or disk_sequence.get("artifact_id") != artifact_id:
        return None

    try:
        frame_count = int(disk_sequence["frame_count"])
        width = int(disk_sequence["width"])
        height = int(disk_sequence["height"])
        fps_ratio = str(disk_sequence["fps_ratio"])
        fps = float(disk_sequence["fps"])
        start = max(0.0, float(trim_start))
        span = max(0.2, float(source_span))
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if frame_count <= 0 or width <= 0 or height <= 0 or fps <= 0:
        return None

    try:
        plan = build_compositing_plan(config, disk_manifest, start)
    except Exception:
        return None
    if not plan.get("enabled") or plan.get("artifact_id") != artifact_id:
        return None
    start_frame = plan.get("frame_index")
    if (
        isinstance(start_frame, bool)
        or not isinstance(start_frame, int)
        or start_frame < 0
        or start_frame >= frame_count
    ):
        return None
    needed_frames = max(1, math.ceil(span * fps - 1e-9))
    if start_frame + needed_frames > frame_count:
        # Allow 1-frame boundary tolerance when math.ceil() rounds up fractional
        # sub-frames at the clip tail, provided the integral frame span fits.
        if start_frame + math.floor(span * fps) > frame_count:
            return None

    expected_names = {f"frame_{index:06d}.png" for index in range(frame_count)}
    try:
        entries = list(frames_dir.iterdir())
    except OSError:
        return None
    actual_names = {entry.name for entry in entries if _BACKGROUND_FRAME_RE.fullmatch(entry.name)}
    if actual_names != expected_names:
        return None
    for name in sorted(expected_names):
        frame_path = frames_dir / name
        if (
            frame_path.is_symlink()
            or not frame_path.is_file()
            or not _path_is_under(frame_path, frames_dir)
        ):
            return None
        try:
            with Image.open(frame_path) as image:
                image.verify()
            with Image.open(frame_path) as image:
                if image.mode != "RGBA" or image.size != (width, height):
                    return None
        except Exception:
            return None

    return {
        "artifact_id": artifact_id,
        "frames_dir": frames_dir,
        "frame_pattern": str(frames_dir / "frame_%06d.png"),
        "frame_index": start_frame,
        "fps_ratio": fps_ratio,
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "rotation": int(disk_sequence.get("rotation", 0)),
        "manifest": dict(disk_manifest),
        "plan": plan,
    }


def _register_ffmpeg_proc(proc: "subprocess.Popen") -> None:
    with _active_ffmpeg_procs_lock:
        _active_ffmpeg_procs.add(proc)


def _unregister_ffmpeg_proc(proc: "subprocess.Popen") -> None:
    with _active_ffmpeg_procs_lock:
        _active_ffmpeg_procs.discard(proc)


def _kill_tracked_ffmpeg_procs() -> None:
    """atexit hook: best-effort terminate/kill of any ffmpeg child still
    tracked when the interpreter shuts down."""
    with _active_ffmpeg_procs_lock:
        procs = list(_active_ffmpeg_procs)
    for proc in procs:
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception:
            pass
    for proc in procs:
        try:
            if proc.poll() is None:
                proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


atexit.register(_kill_tracked_ffmpeg_procs)


# ffmpeg's xfade transitions we expose. Anything outside this set falls back to
# "fade" rather than reaching the filter graph -- an unknown name there kills
# the whole render, and the name comes from the UI.
XFADE_TRANSITIONS = (
    "fade", "fadeblack", "fadewhite", "dissolve",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose",
)
DEFAULT_TRANSITION_DURATION = 0.4
MAX_TRANSITION_DURATION = 2.0

# Eased transition progress (EDITOR-CUT-QUALITY-R2 lane TM spike). xfade's
# built-in transitions only run linear progress, so an eased boundary is
# rendered with `xfade=transition=custom:expr=...` that re-implements the
# built-in geometry from libavfilter/vf_xfade.c at an eased progress. Only
# the types listed here were proven pixel-equal to the built-in at linear
# progress by a real render (tests/test_transition_easing.py); every other
# type ignores `easing` and stays on the built-in, linear. Mirrored by
# EASED_TRANSITIONS in frontend/src/lib/timelineMath.js.
EASED_TRANSITIONS = (
    "fade", "fadeblack", "fadewhite",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
)


def transition_easing_name(kind: str, value: Any) -> str:
    """Easing a boundary actually renders with; 'linear' unless honoured."""
    if kind not in EASED_TRANSITIONS:
        return "linear"
    return value if isinstance(value, str) and value in CAMERA_EASINGS else "linear"


def eased_xfade_progress_expr(easing: str) -> str:
    """xfade's own progress P runs 1 -> 0. The curves are the camera ones
    (ease_camera_ratio, applied to forward progress 1-P), returned in P's
    direction: E = 1 - ease(1 - P), simplified so P appears without nesting."""
    if easing == "ease_in":       # 1 - (1-P)^2
        return "(P*(2-P))"
    if easing == "ease_out":      # 1 - (1-P)(1+P)
        return "(P*P)"
    if easing == "ease_in_out":
        return "(if(gt(P,0.5),1-2*(1-P)*(1-P),2*P*P))"
    return "(P)"


# Black/white the fadeblack/fadewhite bridge dips through, per plane, for the
# yuv444p frames xfade negotiates here (measured off the built-in transition).
_XFADE_BRIDGE_LEVELS = {"fadeblack": (0, 128, 128), "fadewhite": (255, 128, 128)}


def _plane_pick(prefix: str, x: str, y: str) -> str:
    return (f"if(eq(PLANE,0),{prefix}0({x},{y}),if(eq(PLANE,1),{prefix}1({x},{y}),"
            f"if(eq(PLANE,2),{prefix}2({x},{y}),{prefix}3({x},{y}))))")


def _smoothstep_expr(edge0: float, edge1: float, x: str) -> str:
    t = f"clip(({x}-{edge0})/{round(edge1 - edge0, 6)},0,1)"
    return f"({t}*{t}*(3-2*{t}))"


def eased_xfade_custom_expr(kind: str, easing: str) -> Optional[str]:
    """The `custom` expression for an eased boundary, or None to stay on the
    built-in transition (linear, or a type that does not honour easing)."""
    if transition_easing_name(kind, easing) == "linear":
        return None
    return xfade_custom_body(kind, eased_xfade_progress_expr(easing))


def xfade_custom_body(kind: str, e: str) -> Optional[str]:
    """Built-in geometry of `kind` as a custom expression at progress `e`.
    With e = "(P)" it must reproduce the built-in transition itself -- that
    is the proof each type in EASED_TRANSITIONS was shipped on."""
    if kind == "fade":
        return f"A*{e}+B*(1-{e})"
    if kind in _XFADE_BRIDGE_LEVELS:
        lv = _XFADE_BRIDGE_LEVELS[kind]
        bg = f"if(eq(PLANE,0),{lv[0]},if(eq(PLANE,1),{lv[1]},{lv[2]}))"
        s_out = _smoothstep_expr(0.8, 1.0, e)
        s_in = _smoothstep_expr(0.2, 1.0, e)
        inner_a = f"(A*{s_out}+{bg}*(1-{s_out}))"
        inner_b = f"({bg}*{s_in}+B*(1-{s_in}))"
        return f"{inner_a}*{e}+{inner_b}*(1-{e})"
    if kind == "wipeleft":
        return f"if(gt(X,trunc(W*{e})),B,A)"
    if kind == "wiperight":
        return f"if(gt(X,trunc(W*(1-{e}))),A,B)"
    if kind == "wipeup":
        return f"if(gt(Y,trunc(H*{e})),B,A)"
    if kind == "wipedown":
        return f"if(gt(Y,trunc(H*(1-{e}))),A,B)"
    if kind == "slideleft":
        zx = f"(X-trunc(W*{e}))"
        return f"if(gte({zx},0),{_plane_pick('b', zx, 'Y')},{_plane_pick('a', f'({zx}+W)', 'Y')})"
    if kind == "slideright":
        zx = f"(X+trunc(W*{e}))"
        return f"if(lt({zx},W),{_plane_pick('b', zx, 'Y')},{_plane_pick('a', f'({zx}-W)', 'Y')})"
    if kind == "slideup":
        zy = f"(Y-trunc(H*{e}))"
        return f"if(gte({zy},0),{_plane_pick('b', 'X', zy)},{_plane_pick('a', 'X', f'({zy}+H)')})"
    if kind == "slidedown":
        zy = f"(Y+trunc(H*{e}))"
        return f"if(lt({zy},H),{_plane_pick('b', 'X', zy)},{_plane_pick('a', 'X', f'({zy}-H)')})"
    return None


def xfade_filter_args(kind: str, fade_dur: float, offset: float, easing: Any = None) -> str:
    """`xfade=...` for one boundary. Linear keeps the exact built-in text."""
    expr = eased_xfade_custom_expr(kind, easing)
    if expr is None:
        return f"xfade=transition={kind}:duration={fade_dur}:offset={offset}"
    return f"xfade=transition=custom:expr='{expr}':duration={fade_dur}:offset={offset}"


_SPOTLIGHT_INTERNAL_LABELS = (
    "spot_src",
    "spot_focus",
    "spot_dim",
    "spot_mask_raw",
    "spot_mask",
    "spot_fg",
    "spot_cut",
)


def _append_spotlight_filter(
    filter_complex: List[str],
    current_v: str,
    spotlight: Any,
) -> str:
    """Append an opt-in SpotlightV1 graph and return its output label.

    ``build_ffmpeg_filter`` is deliberately independent of the editor and
    emits a fragment rooted at ``[0:v]``.  The assembled video may already be
    behind several filter nodes by this point, so re-root that one input and
    namespace every internal label before appending a single labelled output.
    A disabled/invalid/missing effect returns the original label without
    adding anything to the graph.
    """

    fragment = build_ffmpeg_filter(spotlight, VIDEO_WIDTH, VIDEO_HEIGHT)
    if not fragment:
        return current_v

    namespace = f"spotlight_{len(filter_complex)}"
    for label in _SPOTLIGHT_INTERNAL_LABELS:
        fragment = fragment.replace(f"[{label}]", f"[{namespace}_{label}]")
    fragment = fragment.replace("[0:v]", current_v, 1)
    # FFmpeg's filter-option parser treats the commas in geq's if() as
    # option separators unless the expression is quoted. The pure builder
    # intentionally returns a shell-independent fragment, so quote only this
    # graph-local expression at the composition boundary.
    fragment = fragment.replace("geq=lum=if(", "geq=lum='if(", 1)
    fragment = fragment.replace(")[spotlight_", ")'[spotlight_", 1)
    # The ellipse contract uses the readable ``<=`` operator. FFmpeg's
    # expression evaluator accepts the equivalent ``lte(a,b)`` form here;
    # convert only this generated comparison so the reusable contract stays
    # unchanged for callers that inspect or serialise it.
    fragment = fragment.replace("geq=lum='if((", "geq=lum='if(lte(", 1)
    fragment = fragment.replace("<=1)\\,255", ",1)\\,255", 1)
    output_label = f"[{namespace}_out]"
    filter_complex.append(f"{fragment}{output_label};")
    return output_label


# Per-clip colour ranges. Wider than this and a review clip stops looking like
# the product; ffmpeg's eq would happily accept anything.
EQ_LIMITS = {
    "brightness": (-0.3, 0.3, 0.0),
    "contrast": (0.5, 2.0, 1.0),
    "saturation": (0.0, 3.0, 1.0),
}


ACCENT_PALETTES = {
    key: {
        "primary": policy.accent_color,
        "status": policy.status_color,
        "neutral": policy.neutral_color,
    }
    for key, policy in STYLE_MOTION_POLICIES.items()
}
DEFAULT_ACCENT_PALETTE = "clean_tech_review"
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _finite_number(value: Any, fallback: float) -> float:
    """Parse a numeric style value without allowing NaN/Infinity into ffmpeg."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def _normalise_hex_color(value: Any, fallback: str) -> str:
    """Return a canonical six-digit colour, or the supplied safe fallback."""
    if isinstance(value, str):
        value = value.strip()
        if len(value) == 4 and value.startswith("#"):
            value = "#" + "".join(char * 2 for char in value[1:])
        if _HEX_COLOR_RE.fullmatch(value):
            return value.upper()
    return fallback


def resolve_accent_palette(
    palette: Any = None,
    *,
    style_preset: Optional[str] = None,
) -> Dict[str, str]:
    """Resolve the small accent vocabulary shared by renderer-facing data.

    ``palette`` may be an existing palette id or an object containing
    ``primary``, ``status`` and/or ``neutral`` colours. Unknown ids and invalid
    colours fall back to the Golden Master palette. This is intentionally a
    pure resolver: it does not mutate a project manifest or source media.
    """
    requested_style = str(style_preset or DEFAULT_ACCENT_PALETTE).strip().lower()
    base_name = requested_style if requested_style in ACCENT_PALETTES else DEFAULT_ACCENT_PALETTE
    base = ACCENT_PALETTES[base_name]
    requested = {}
    if isinstance(palette, str):
        palette_name = palette.strip().lower()
        if palette_name in ACCENT_PALETTES:
            base_name = palette_name
            base = ACCENT_PALETTES[base_name]
    elif isinstance(palette, dict):
        requested = palette

    return {
        "name": base_name,
        "primary": _normalise_hex_color(requested.get("primary", requested.get("accent")), base["primary"]),
        "status": _normalise_hex_color(requested.get("status", requested.get("status_color")), base["status"]),
        "neutral": _normalise_hex_color(requested.get("neutral"), base["neutral"]),
    }


def resolve_color_finish(
    clip: Any,
    *,
    style_preset: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize a clip's look contract before it enters the filter graph.

    Older editor manifests store colour values flat on a clip. Newer callers
    may put them in ``look`` or ``color_grade``. Flat values win, while absent
    values remain at neutral defaults so a legacy clip emits no extra filter.
    The result also carries a validated accent palette for future overlay
    emitters; the current renderer deliberately leaves baked PNG/WebM colours
    untouched.
    """
    data = clip if isinstance(clip, dict) else {}
    nested_sources = []
    for key in ("color_grade", "colorGrade", "look"):
        value = data.get(key)
        if isinstance(value, dict):
            nested_sources.append(value)

    sources = [*nested_sources, data]
    resolved_style = next(
        (
            value
            for source in reversed(sources)
            for key in ("style_preset", "stylePreset")
            if (value := source.get(key)) is not None
        ),
        style_preset,
    )
    style_key = str(resolved_style or DEFAULT_ACCENT_PALETTE).strip().lower()
    if style_key not in ACCENT_PALETTES:
        style_key = DEFAULT_ACCENT_PALETTE

    eq = {}
    for key, (low, high, default) in EQ_LIMITS.items():
        value = None
        for source in reversed(sources):
            if key not in source or source[key] is None:
                continue
            try:
                candidate = float(source[key])
            except (TypeError, ValueError):
                continue
            if not math.isfinite(candidate):
                continue
            value = min(high, max(low, candidate))
            break
        if value is None:
            continue
        if abs(value - default) > 1e-3:
            eq[key] = value

    palette_value = next(
        (
            source[key]
            for source in reversed(sources)
            for key in ("accent_palette", "accentPalette")
            if key in source
        ),
        None,
    )
    palette = resolve_accent_palette(palette_value, style_preset=style_key)
    # Individual colour aliases are useful to existing flat clip payloads and
    # should override only their corresponding palette slot.
    direct_accent = next(
        (source[key] for source in reversed(sources) for key in ("accent_color", "accentColor") if key in source),
        None,
    )
    direct_status = next(
        (source[key] for source in reversed(sources) for key in ("status_color", "statusColor") if key in source),
        None,
    )
    if direct_accent is not None:
        palette["primary"] = _normalise_hex_color(direct_accent, palette["primary"])
    if direct_status is not None:
        palette["status"] = _normalise_hex_color(direct_status, palette["status"])

    return {"style_preset": style_key, "eq": eq, "palette": palette}


def normalize_lut_intensity(value: Any, default: float = 1.0) -> float:
    """Keep LUT blend strength finite and within FFmpeg's opacity contract."""
    return min(1.0, max(0.0, _finite_number(value, default)))


def build_eq_filter(clip: Dict[str, Any]) -> str:
    """`eq=...,` for one clip, or "" when every value is still the default."""
    parts = []
    for key, value in resolve_color_finish(clip)["eq"].items():
        parts.append(f"{key}={value}")
    return f"eq={':'.join(parts)}," if parts else ""


ZOOM_LIMITS = (1.0, 3.0)

# Badge corners as ffmpeg overlay expressions. 40px from the sides; the top
# offset clears the caption-free zone the hook header uses.
STICKER_POSITIONS = {
    "top_right": ("(W-w-40)", "140"),
    "top_left": ("40", "140"),
    "top_center": ("(W-w)/2", "140"),
    "bottom_right": ("(W-w-40)", "(H-h-420)"),
    "bottom_left": ("40", "(H-h-420)"),
    "bottom_center": ("(W-w)/2", "(H-h-420)"),
}
STICKER_BASE_WIDTH = 160

# Video overlay effects (checkmark/warning/arrow/etc) render into a square
# region this many px wide at scale=1.0 before the user's per-instance scale
# factor is applied -- bigger than a sticker badge since these read as a
# momentary full graphic, not a small corner accent.
EFFECT_BASE_SIZE = 360

# Keep the Hook scrim's peak opacity aligned with SequencePlayer's Canvas
# gradient.  The frontend deliberately leaves 25% of the footage visible so
# the backdrop improves legibility without turning the banner area opaque.
OVERLAY_SCRIM_OPACITY = 0.75


def sticker_geometry(
    position: str,
    scale: float,
    norm_x: Optional[float] = None,
    norm_y: Optional[float] = None,
    canvas_w: int = VIDEO_WIDTH,
    canvas_h: int = VIDEO_HEIGHT,
):
    """(width, x expression, y expression) for the badge overlay."""
    try:
        factor = min(3.5, max(0.3, float(scale or 1.0)))
    except (TypeError, ValueError):
        factor = 1.0
    # SequencePlayer paints the canonical sticker geometry on a 540x960
    # Canvas. FFmpeg may render at 720x1280 or 1080x1920, so scale both the
    # asset and the safe-zone offsets into the export raster before the final
    # frame is downsampled. Keeping the old fixed 160px width made Preview
    # stickers visibly smaller in every rendered export.
    canvas_scale_x = float(canvas_w) / 540.0
    canvas_scale_y = float(canvas_h) / 960.0
    width = int(round(STICKER_BASE_WIDTH * canvas_scale_x * factor))
    width = width if width % 2 == 0 else width + 1
    if norm_x is not None and norm_y is not None:
        px_x = int(round(canvas_w * float(norm_x) - width / 2))
        px_x = max(10, min(canvas_w - width - 10, px_x))
        target_center_y = int(round(canvas_h * float(norm_y)))
        x = str(px_x)
        y = f"({target_center_y}-h/2)"
    else:
        edge_x = int(round(40 * canvas_scale_x))
        top_y = int(round(140 * canvas_scale_y))
        bottom_margin = int(round(420 * canvas_scale_y))
        positions = {
            "top_right": (f"(W-w-{edge_x})", str(top_y)),
            "top_left": (str(edge_x), str(top_y)),
            "top_center": ("(W-w)/2", str(top_y)),
            "bottom_right": (f"(W-w-{edge_x})", f"(H-h-{bottom_margin})"),
            "bottom_left": (str(edge_x), f"(H-h-{bottom_margin})"),
            "bottom_center": ("(W-w)/2", f"(H-h-{bottom_margin})"),
        }
        x, y = positions.get(position, positions["top_right"])
    return width, x, y


# Sticker/effect entrance + exit animation, mirrored 1:1 by
# frontend/src/lib/stickerAnimation.js (tests/test_preview_render_parity.py
# evaluates both on the same inputs). Entrance = linear alpha fade plus, for
# stickers, an ease_out scale settle 0.88 -> 1.0 about the resting centre;
# exit = linear alpha fade. Durations are whole frames, capped at 40% of the
# visible window so a short sticker still reaches full opacity. Only the
# transient frames change: the resting frame is bit-identical to the old
# hard on/off overlay (same scale, same overlay x/y, alpha untouched).
OVERLAY_ANIM_IN_FRAMES = 7       # 7/30 s = 0.233 s (<= 0.25 s)
OVERLAY_ANIM_OUT_FRAMES = 6      # 6/30 s = 0.2 s
OVERLAY_ANIM_MAX_SHARE = 0.4
OVERLAY_ANIM_SCALE_FROM = 0.88
OVERLAY_ANIM_OPEN_END = 99999.0  # Canvas uses end=999999 for "no end"


def overlay_anim_timing(start: float, end: Optional[float], fps: int = FPS) -> Tuple[float, float]:
    """(entrance seconds, exit seconds) on the 1/fps grid; exit 0 without an end."""
    start = float(start)
    has_end = end is not None and math.isfinite(float(end)) and float(end) < OVERLAY_ANIM_OPEN_END
    if has_end:
        visible = float(end) - start
        if visible <= 0:
            return 0.0, 0.0
        cap = int(math.floor(visible * OVERLAY_ANIM_MAX_SHARE * fps + 1e-6))
    else:
        cap = OVERLAY_ANIM_IN_FRAMES
    in_frames = max(0, min(OVERLAY_ANIM_IN_FRAMES, cap))
    out_frames = max(0, min(OVERLAY_ANIM_OUT_FRAMES, cap)) if has_end else 0
    return in_frames / fps, out_frames / fps


def overlay_anim_state(
    t: float, start: float, end: Optional[float], *, scale_in: bool = True, fps: int = FPS
) -> Tuple[float, float]:
    """(alpha, scale) at timeline time t; the reference the ffmpeg chain follows."""
    d_in, d_out = overlay_anim_timing(start, end, fps)
    alpha, scale = 1.0, 1.0
    if d_in > 0:
        p = min(1.0, max(0.0, (float(t) - float(start)) / d_in))
        alpha = p
        if scale_in:
            scale = OVERLAY_ANIM_SCALE_FROM + (1.0 - OVERLAY_ANIM_SCALE_FROM) * ease_camera_ratio("ease_out", p)
    if d_out > 0:
        # Two chained ffmpeg `fade` filters multiply their factors.
        alpha *= min(1.0, max(0.0, (float(end) - float(t)) / d_out))
    return alpha, scale


def overlay_anim_filters(
    start: float,
    end: Optional[float],
    *,
    rest_w: Optional[int] = None,
    rest_h: Optional[int] = None,
    fps: int = FPS,
) -> str:
    """Filter chain (no leading comma, "" when nothing animates) for a
    rest-size overlay stream with an alpha plane and real per-frame time.

    The scale settle needs the resting size: `pad` keeps the stream at
    rest_w x rest_h, so overlay's w/h -- and every resting x/y expression --
    stays exactly as before. Without it (or for effects) only alpha fades.
    """
    d_in, d_out = overlay_anim_timing(start, end, fps)
    start = float(start)
    parts = []
    if d_in > 0 and rest_w and rest_h:
        # ffmpeg form of ease_camera_ratio("ease_out", p) = p*(2-p).
        p = f"clip((t-{start:.6f})/{d_in:.6f},0,1)"
        s = f"({OVERLAY_ANIM_SCALE_FROM:g}+{1.0 - OVERLAY_ANIM_SCALE_FROM:g}*{p}*(2-{p}))"
        # rgba: `pad` rounds a subsampled (yuva420p) size down to even, which
        # would reject an odd resting height. Rest frames stay bit-identical.
        parts.append("format=rgba")
        parts.append(
            f"scale=w='min(iw,2*trunc(iw*{s}/2+0.5))':h='min(ih,2*trunc(ih*{s}/2+0.5))':eval=frame"
        )
        parts.append("format=rgba")
        parts.append(
            f"pad=w={int(rest_w)}:h={int(rest_h)}:x='(ow-iw)/2':y='(oh-ih)/2':color=black@0:eval=frame"
        )
    if d_in > 0:
        parts.append(f"fade=t=in:st={start:.6f}:d={d_in:.6f}:alpha=1")
    if d_out > 0:
        parts.append(f"fade=t=out:st={float(end) - d_out:.6f}:d={d_out:.6f}:alpha=1")
    return ",".join(parts)


def overlay_rest_height(path: Path, rest_w: int) -> Optional[int]:
    """Height ffmpeg's `scale=rest_w:-1` produces (av_rescale, round half up)."""
    try:
        with Image.open(path) as img:
            iw, ih = img.size
    except Exception:
        return None
    if iw <= 0 or ih <= 0:
        return None
    return (int(rest_w) * ih + iw // 2) // iw

# What "export quality" means, end to end. Draft trades resolution and encode
# effort for wall clock.
#
# `qp` is the hardware encoders' equivalent knob. On this project's footage
# h264_amf at qp 20/22 measured SSIM 0.9942 and PSNR 49.3 dB against libx264
# crf 18 -- indistinguishable -- in a smaller file (8.0MB against 11.1MB) and
# 3.6x less wall clock.
EXPORT_PRESETS = {
    "post": {"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT, "crf": 18, "x264_preset": "medium",
             "qp_i": 20, "qp_p": 22},
    "draft": {"width": 720, "height": 1280, "crf": 26, "x264_preset": "veryfast",
              "qp_i": 26, "qp_p": 28},
}

# Hardware encoders, best first. NVENC and QSV lead because on a machine that
# has both an integrated and a discrete GPU -- an ordinary laptop -- the
# discrete one is the better encoder, and probing costs a fraction of a second
# per miss. videotoolbox is macOS only and simply fails to probe elsewhere.
#
# Being listed by `ffmpeg -encoders` says nothing about whether the machine can
# use one: this build lists NVENC and QSV on a box that has neither, and both
# fail only when asked to encode.
HW_ENCODER_CANDIDATES = ("h264_nvenc", "h264_qsv", "h264_amf", "h264_videotoolbox")

# The quality gate below compares the candidate against libx264 on the same
# frames. It exists because each family's quality knob is on its own scale, and
# only the machine that has the hardware can say whether the setting chosen for
# it is sane -- guessing NVENC's numbers from an AMD box is how a render ends
# up smeared. Measured with these settings: h264_amf reaches 0.98 here.
HW_QUALITY_FLOOR = 0.95
_PROBE_SOURCE = "testsrc2=size=480x854:rate=30:duration=1,format=yuv420p"

_hw_encoder_probe: Optional[str] = None
_hw_encoder_probed = False


def _encoder_quality_ok(name: str) -> Optional[float]:
    """
    SSIM of `name`'s output against libx264's on the same frames, or None if it
    could not be measured. Both encode the same synthetic clip at this
    project's own settings.
    """
    import re
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ref = Path(tmp) / "ref.mp4"
        got = Path(tmp) / "got.mp4"
        base = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", _PROBE_SOURCE]
        try:
            subprocess.run(base + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(ref)],
                           capture_output=True, timeout=120, check=True)
            subprocess.run(base + _hw_args(name, 20, 22) + [str(got)],
                           capture_output=True, timeout=120, check=True)
            cmp = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(got), "-i", str(ref),
                                  "-lavfi", "[0:v][1:v]ssim", "-f", "null", "-"],
                                 capture_output=True, text=True, timeout=120)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
        match = re.search(r"All:(\d+\.\d+)", cmp.stderr)
        return float(match.group(1)) if match else None


def hardware_encoder() -> Optional[str]:
    """
    The best hardware H.264 encoder this machine can actually use, or None.

    A candidate has to encode a frame AND hold up against libx264 on the same
    frames before it is trusted. `OMNICUT_ENCODER` overrides: `cpu` forces
    libx264, any other value names an encoder and skips both checks.
    """
    global _hw_encoder_probe, _hw_encoder_probed
    forced = os.environ.get("OMNICUT_ENCODER", "").strip()
    if forced:
        return None if forced.lower() in ("cpu", "x264", "libx264", "software") else forced
    if _hw_encoder_probed:
        return _hw_encoder_probe
    _hw_encoder_probed = True
    for name in HW_ENCODER_CANDIDATES:
        try:
            probe = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=black:s=256x256:d=0.1:r=30",
                "-c:v", name, "-f", "null", "-",
            ], capture_output=True, text=True, timeout=60)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        if probe.returncode == 0:
            ssim = _encoder_quality_ok(name)
            if ssim is None:
                print(f"   ⚠️  วัดคุณภาพ {name} ไม่ได้ — ข้ามไปใช้ตัวถัดไป")
                continue
            if ssim < HW_QUALITY_FLOOR:
                print(f"   ⚠️  {name} คุณภาพต่ำกว่าเกณฑ์ (SSIM {ssim:.3f} < {HW_QUALITY_FLOOR}) — ไม่ใช้")
                continue
            _hw_encoder_probe = name
            print(f"   ⚡ ใช้ตัวเข้ารหัสของการ์ดจอ ({name}, SSIM {ssim:.3f}) — เรนเดอร์เร็วขึ้นหลายเท่า")
            return name
    print("   💻 ไม่พบตัวเข้ารหัสของการ์ดจอที่ใช้ได้ — ใช้ CPU (libx264)")
    return None


def _hw_args(name: str, qp_i: int, qp_p: int) -> List[str]:
    """Output args for one hardware encoder at the given quality level."""
    if name == "h264_amf":
        # Measured on this project's footage: SSIM 0.9942 / PSNR 49.3 dB
        # against libx264 crf 18, in a smaller file.
        return ["-c:v", name, "-profile:v", "high", "-quality", "balanced",
                "-rc", "cqp", "-qp_i", str(qp_i), "-qp_p", str(qp_p)]
    if name == "h264_nvenc":
        # NVENC's constant-quality mode is VBR with -cq, which the driver
        # documents as its crf equivalent; constqp at the same number comes out
        # noticeably softer.
        return ["-c:v", name, "-profile:v", "high", "-preset", "p5",
                "-rc", "vbr", "-cq", str(qp_i), "-b:v", "0"]
    if name == "h264_qsv":
        return ["-c:v", name, "-profile:v", "high", "-global_quality", str(qp_i),
                "-look_ahead", "0"]
    if name == "h264_videotoolbox":
        # No crf equivalent; -q:v is 0-100 with higher meaning better, so the
        # quality knob has to be inverted onto that range.
        return ["-c:v", name, "-profile:v", "high", "-q:v", str(max(1, min(100, 100 - qp_i * 2)))]
    return ["-c:v", name]


def framing_filters(media_info: Dict[str, Any], scaled_w: int, scaled_h: int,
                    crop_x: int, crop_y: int) -> Optional[str]:
    """
    One resample where the chain used two, or None when it cannot be done.

    The chain scales the source up to cover the frame, centre-crops it, then
    scales that by the zoom and crops again -- two full-frame resamples per
    frame, the second with lanczos. Both stages together only ever show one
    rectangle of the source, so cropping there and scaling once straight to the
    frame gives the same picture for half the resampling. Measured: 25.8s ->
    21.1s on eight clips, at SSIM 0.985 and PSNR 39.5 dB against the two-stage
    chain -- and one lanczos pass instead of two is the sharper of the pair.

    The catch is which dimensions to compute from. ffmpeg auto-rotates before
    the filter graph, so a clip carrying `rotation -90` -- ordinary phone
    footage -- reaches the filters as 1080x1920 while the container still says
    1920x1080. Computing from the container numbers put the window in the wrong
    place entirely (SSIM 0.74) and looked like a plausible crop until it was
    compared frame by frame. Returns None when the dimensions are not known, so
    the caller keeps the two-stage chain, which asks `scale` to work it out and
    is immune to this.
    """
    sw = int(media_info.get("width") or 0)
    sh = int(media_info.get("height") or 0)
    if sw <= 0 or sh <= 0:
        return None
    if int(abs(float(media_info.get("rotation") or 0))) % 180 == 90:
        sw, sh = sh, sw

    cover = max(VIDEO_WIDTH / sw, VIDEO_HEIGHT / sh)   # stage 1: cover the frame
    total = cover * (scaled_w / VIDEO_WIDTH)           # stage 2: the zoom on top
    if total <= 0:
        return None

    # The visible window, in source pixels.
    win_w = VIDEO_WIDTH / total
    win_h = VIDEO_HEIGHT / total
    off_x = ((sw * total - scaled_w) / 2 + crop_x) / total
    off_y = ((sh * total - scaled_h) / 2 + crop_y) / total

    def even(v: float) -> int:
        n = int(round(v))
        return max(2, n - (n % 2))

    w, h = even(win_w), even(win_h)
    x, y = max(0, int(round(off_x))), max(0, int(round(off_y)))
    # A window smaller than the largest allowed zoom could ever call for means
    # the numbers do not describe this file; upscaling a handful of pixels to a
    # full frame would "work" and look nothing like the render.
    if w < VIDEO_WIDTH / (ZOOM_LIMITS[1] * 1.05) or h < VIDEO_HEIGHT / (ZOOM_LIMITS[1] * 1.05):
        return None
    # A window that would reach past the source means the arithmetic disagrees
    # with the file; fall back rather than emit a crop ffmpeg will reject.
    if w > sw or h > sh or x + w > sw or y + h > sh:
        return None
    return f"crop={w}:{h}:{x}:{y},scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:flags=lanczos,setsar=1"


def encoder_args(profile: Dict[str, Any]) -> List[str]:
    """ffmpeg output args for the fastest encoder this machine can use."""
    hw = hardware_encoder()
    if hw:
        return _hw_args(hw, int(profile.get("qp_i", 20)), int(profile.get("qp_p", 22)))
    return ["-c:v", "libx264", "-profile:v", "high", "-level", "4.2",
            "-preset", profile["x264_preset"], "-crf", str(profile["crf"])]


def frame_geometry(clip: Dict[str, Any], default_scale: float):
    """
    Scale + crop offsets for one clip. pan_x/pan_y run -1..1 across whatever
    room the zoom leaves; the offsets are clamped to the frame because ffmpeg
    errors out on a crop that starts outside the scaled image.
    """
    raw_zoom = clip.get("zoom")
    try:
        scale = default_scale if raw_zoom is None else float(raw_zoom)
    except (TypeError, ValueError):
        scale = default_scale
    scale = min(ZOOM_LIMITS[1], max(ZOOM_LIMITS[0], scale))

    scaled_w = int(VIDEO_WIDTH * scale)
    scaled_h = int(VIDEO_HEIGHT * scale)
    scaled_w = scaled_w if scaled_w % 2 == 0 else scaled_w + 1
    scaled_h = scaled_h if scaled_h % 2 == 0 else scaled_h + 1

    room_x = scaled_w - VIDEO_WIDTH
    room_y = scaled_h - VIDEO_HEIGHT

    def offset(room, key):
        try:
            pan = min(1.0, max(-1.0, float(clip.get(key) or 0.0)))
        except (TypeError, ValueError):
            pan = 0.0
        return int(min(room, max(0, round(room / 2 * (1 + pan)))))

    return scale, offset(room_x, "pan_x"), offset(room_y, "pan_y"), scaled_w, scaled_h


# Camera keyframe easing (EDITOR-CUT-QUALITY-R2 E1). Same curves as
# scripts/subtitle/motion_contract.py, scripts/keyframe_engine.py and
# frontend/src/lib/timelineMath.js CAMERA_EASINGS. A point's `easing` shapes
# the segment that ENDS at that point (keyframe_engine / keyframeModel rule).
# Missing or unknown easing == linear, so old projects render unchanged.
CAMERA_EASINGS = ("linear", "ease_in", "ease_out", "ease_in_out")


def camera_easing_name(value: Any) -> str:
    return value if isinstance(value, str) and value in CAMERA_EASINGS else "linear"


def ease_camera_ratio(name: str, ratio: float) -> float:
    t = min(1.0, max(0.0, ratio))
    if name == "ease_in":
        return t * t
    if name == "ease_out":
        return t * (2.0 - t)
    if name == "ease_in_out":
        return 2.0 * t * t if t < 0.5 else -1.0 + (4.0 - 2.0 * t) * t
    return t


def interpolate_keyframes(keyframes: Any, time: float, fallback: float) -> float:
    """Deterministically resolve a numeric keyframe track at local time."""
    points = []
    for point in keyframes if isinstance(keyframes, list) else []:
        try:
            points.append((float(point["time"]), float(point["value"]), camera_easing_name(point.get("easing"))))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    points.sort(key=lambda item: item[0])
    if not points:
        return fallback
    if time <= points[0][0]:
        return points[0][1]
    if time >= points[-1][0]:
        return points[-1][1]
    for (left_t, left_v, _), (right_t, right_v, easing) in zip(points, points[1:]):
        if time <= right_t:
            ratio = (time - left_t) / (right_t - left_t) if right_t > left_t else 1.0
            return left_v + (right_v - left_v) * ease_camera_ratio(easing, ratio)
    return points[-1][1]


CAMERA_MOTION_LIMITS = {
    "zoom": (1.0, 3.0),
    "pan_x": (-1.0, 1.0),
    "pan_y": (-1.0, 1.0),
}


def _camera_track(clip: Dict[str, Any], prop: str) -> List[Dict[str, Any]]:
    """Extract one camera property from the mixed keyframe vocabulary."""
    out = []
    for point in clip.get("keyframes") if isinstance(clip.get("keyframes"), list) else []:
        if not isinstance(point, dict):
            continue
        if prop in point:
            out.append({"time": point.get("time"), "value": point.get(prop), "easing": point.get("easing")})
        elif point.get("property") == prop:
            out.append({"time": point.get("time"), "value": point.get("value"), "easing": point.get("easing")})
    return out


def _clamp_camera_value(prop: str, value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    low, high = CAMERA_MOTION_LIMITS[prop]
    return min(high, max(low, number))


def resolve_clip_transforms(clip: Dict[str, Any], local_time: float, default_zoom: float = 1.0) -> Dict[str, float]:
    """Resolve the live camera contract at played local clip time."""
    try:
        base_zoom = float(clip.get("zoom") if clip.get("zoom") is not None else default_zoom)
    except (TypeError, ValueError):
        base_zoom = default_zoom
    try:
        base_pan_x = float(clip.get("pan_x") if clip.get("pan_x") is not None else 0.0)
    except (TypeError, ValueError):
        base_pan_x = 0.0
    try:
        base_pan_y = float(clip.get("pan_y") if clip.get("pan_y") is not None else 0.0)
    except (TypeError, ValueError):
        base_pan_y = 0.0
    bases = {"zoom": base_zoom, "pan_x": base_pan_x, "pan_y": base_pan_y}
    return {
        prop: _clamp_camera_value(
            prop,
            interpolate_keyframes(_camera_track(clip, prop), local_time, bases[prop])
            if _camera_track(clip, prop) else bases[prop],
            bases[prop],
        )
        for prop in bases
    }


def has_camera_keyframes(clip: Dict[str, Any]) -> bool:
    """Whether a clip asks for per-frame zoom or pan evaluation."""
    return any(_camera_track(clip, prop) for prop in CAMERA_MOTION_LIMITS)


def _ffmpeg_keyframe_expression(track: List[Dict[str, Any]], fallback: float, prop: str) -> str:
    """Build a comma-escaped, piecewise-linear FFmpeg expression."""
    points = []
    low, high = CAMERA_MOTION_LIMITS[prop]
    for point in track:
        try:
            points.append((float(point["time"]), min(high, max(low, float(point["value"])))))
        except (KeyError, TypeError, ValueError):
            continue
    points.sort(key=lambda item: item[0])
    if not points:
        return f"{_clamp_camera_value(prop, fallback, fallback):.6f}"

    expr = f"{points[-1][1]:.6f}"
    for (left_t, left_v), (right_t, right_v) in reversed(list(zip(points, points[1:]))):
        if right_t <= left_t:
            continue
        segment = (
            f"{left_v:.6f}+({right_v - left_v:.6f})*"
            f"(t-{left_t:.6f})/({right_t - left_t:.6f})"
        )
        expr = f"if(lt(t\\,{right_t:.6f})\\,{segment}\\,{expr})"
    return f"if(lt(t\\,{points[0][0]:.6f})\\,{points[0][1]:.6f}\\,{expr})"


def _ffmpeg_keyframe_expression_live(track: List[Dict[str, Any]], fallback: float, prop: str) -> str:
    """Build the live expression, clamping only after interpolation.

    Each segment's progress r = (t-left)/span is shaped by the easing of the
    point that ends it (see CAMERA_EASINGS) as a plain polynomial, so the
    expression stays sin/cos free; linear segments keep the exact old text.
    """
    points = []
    low, high = CAMERA_MOTION_LIMITS[prop]
    for point in track:
        try:
            points.append((float(point["time"]), float(point["value"]), camera_easing_name(point.get("easing"))))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    points.sort(key=lambda item: item[0])
    if not points:
        return f"{_clamp_camera_value(prop, fallback, fallback):.6f}"
    expr = f"{points[-1][1]:.6f}"
    for (left_t, left_v, _), (right_t, right_v, easing) in reversed(list(zip(points, points[1:]))):
        if right_t <= left_t:
            continue
        ratio = f"(t-{left_t:.6f})/({right_t - left_t:.6f})"
        if easing == "linear":
            segment = f"{left_v:.6f}+({right_v - left_v:.6f})*{ratio}"
        else:
            r = f"({ratio})"
            curve = {
                "ease_in": f"{r}*{r}",
                "ease_out": f"{r}*(2-{r})",
                "ease_in_out": f"if(lt({r}\\,0.5)\\,2*{r}*{r}\\,-1+(4-2*{r})*{r})",
            }[easing]
            segment = f"{left_v:.6f}+({right_v - left_v:.6f})*({curve})"
        expr = f"if(lt(t\\,{right_t:.6f})\\,{segment}\\,{expr})"
    expr = f"if(lt(t\\,{points[0][0]:.6f})\\,{points[0][1]:.6f}\\,{expr})"
    return f"min({high:.6f}\\,max({low:.6f}\\,{expr}))"


def dynamic_camera_filter(clip: Dict[str, Any], fallback_zoom: float, *, input_is_canvas: bool = False) -> Optional[str]:
    """Return the per-frame crop graph for a clip with camera keyframes."""
    if not has_camera_keyframes(clip):
        return None
    transforms = resolve_clip_transforms(clip, 0.0, fallback_zoom)
    zoom = _ffmpeg_keyframe_expression_live(_camera_track(clip, "zoom"), transforms["zoom"], "zoom")
    pan_x = _ffmpeg_keyframe_expression_live(_camera_track(clip, "pan_x"), transforms["pan_x"], "pan_x")
    pan_y = _ffmpeg_keyframe_expression_live(_camera_track(clip, "pan_y"), transforms["pan_y"], "pan_y")
    prefix = "" if input_is_canvas else (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(iw-{VIDEO_WIDTH})/2:(ih-{VIDEO_HEIGHT})/2,"
    )
    scaled_w = f"ceil({VIDEO_WIDTH}*({zoom})/2)*2"
    scaled_h = f"ceil({VIDEO_HEIGHT}*({zoom})/2)*2"
    # crop's iw/ih are negotiated when the graph starts and may stay at the
    # first frame's size even though scale=eval=frame changes its output.
    # Drive the crop origin from the same per-frame zoom expression instead.
    return (
        f"{prefix}"
        f"scale={scaled_w}:{scaled_h}:eval=frame,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        f"(({scaled_w}-{VIDEO_WIDTH})/2)*(1+({pan_x})):"
        f"(({scaled_h}-{VIDEO_HEIGHT})/2)*(1+({pan_y})),setsar=1"
    )


def normalize_transitions(transitions: List[Any]) -> List[Dict[str, Any]]:
    """
    Accept both shapes a caller may send for one boundary:
    `"fade"` / `"cut"` (the original), or `{"type": ..., "duration": ...}`.
    Returns one dict per boundary with a whitelisted type and a sane duration.
    """
    out: List[Dict[str, Any]] = []
    for entry in transitions or []:
        if isinstance(entry, dict):
            kind = str(entry.get("type") or "cut")
            raw = entry.get("duration")
            # `or` would swallow a deliberate 0 here; only a missing/unusable
            # value falls back to the default, an explicit 0 gets clamped.
            try:
                dur = DEFAULT_TRANSITION_DURATION if raw is None else float(raw)
            except (TypeError, ValueError):
                dur = DEFAULT_TRANSITION_DURATION
        else:
            kind = str(entry or "cut")
            dur = DEFAULT_TRANSITION_DURATION

        if kind != "cut" and kind not in XFADE_TRANSITIONS:
            kind = "fade"
        dur = min(MAX_TRANSITION_DURATION, max(0.1, dur))
        normalized = {"type": kind, "duration": dur}
        # Only a non-linear easing on a type that honours it is carried, so a
        # linear/old boundary stays the exact dict (and graph) it always was.
        easing = transition_easing_name(kind, entry.get("easing") if isinstance(entry, dict) else None)
        if easing != "linear":
            normalized["easing"] = easing
        out.append(normalized)
    return out


# --------------------------------------------------------------------------
# Whole-frame sequence timing (EDITOR-CUT-QUALITY-R2 lane TM, audit B5).
# Every clip used to come out of its own chain as round(duration*30) frames,
# so the rounding error of each clip added up along the chain (measured
# +0.04..+1.52 frames at the end of 12-24 clips) while the preview kept the
# exact float. Quantising CUMULATIVE boundaries instead -- boundary_k =
# floor(t_k*FPS + 0.5) and every length a difference of two boundaries --
# keeps the error of any boundary under half a frame, never accumulating,
# and the total equals round(total*FPS). frontend/src/lib/timelineMath.js
# planSequenceFrames() is the same function, operation for operation; the
# parity test feeds both the same clip list and compares every frame number.
# --------------------------------------------------------------------------
def sequence_frame_index(seconds: float, fps: int = FPS) -> int:
    """Nearest frame, halves up -- Math.floor(x * fps + 0.5) in the preview."""
    return int(math.floor(float(seconds) * fps + 0.5))


def plan_sequence_frames(
    durations: List[float], boundaries: List[Dict[str, Any]], fps: int = FPS
) -> Dict[str, List[int]]:
    """Lay played clip durations on the frame grid.

    `boundaries` are normalize_transitions() entries (one per boundary).
    Returns per-clip `start`/`end` frame numbers on the output timeline and
    the `overlap` frames each boundary's transition uses (0 for a cut).
    xfade offset = start (= previous end - overlap); xfade duration = overlap.
    """
    starts: List[int] = []
    ends: List[int] = []
    overlaps: List[int] = []
    acc = 0.0
    for i, raw_dur in enumerate(durations):
        dur = float(raw_dur)
        boundary = boundaries[i - 1] if 0 < i <= len(boundaries) else None
        is_transition = bool(i > 0 and boundary and boundary.get("type", "cut") != "cut")
        if is_transition:
            # Same clamp as the xfade fold: never more than the shorter side
            # has to give (minus a 50 ms margin).
            fade = min(float(boundary["duration"]), max(0.05, min(acc, dur) - 0.05))
            start_s = max(0.0, acc - fade)
        else:
            start_s = acc if i > 0 else 0.0
        end_s = start_s + dur
        acc = end_s

        if i == 0:
            start_f = 0
        elif is_transition:
            prev_end = ends[i - 1]
            # A transition keeps at least one frame and starts at or after 0.
            start_f = max(0, min(sequence_frame_index(start_s, fps), prev_end - 1))
        else:
            start_f = ends[i - 1]
        end_f = max(sequence_frame_index(end_s, fps), start_f + 1)
        if is_transition:
            # The incoming clip must outlast its own transition by a frame.
            end_f = max(end_f, ends[i - 1] + 1)
        starts.append(start_f)
        ends.append(end_f)
        overlaps.append(ends[i - 1] - start_f if is_transition else 0)
    return {"start": starts, "end": ends, "overlap": overlaps}


def frames_to_seconds(frames: int, fps: int = FPS) -> float:
    """Seconds for the filter graph; 6 decimals is exact to ffmpeg's 1 us parse."""
    return round(frames / fps, 6)


class VideoEditor:
    """Automates rhythmic cutting, dynamic zoom motion, subtitle burning, and rendering."""

    @staticmethod
    def get_media_info(video_path: str) -> Dict:
        """Inspect video duration, resolution, rotation."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_format", "-show_streams",
            "-print_format", "json",
            str(video_path)
        ]
        try:
            # timeout=60: an unreadable/hung source (unplugged drive, flaky
            # network share, malformed container) must not block forever --
            # callers of get_media_info may be holding _RENDER_SLOT while
            # waiting on this call, so a hang here can wedge every render.
            # subprocess.TimeoutExpired is a subclass of Exception, so it
            # falls into the same fallback dict this function already
            # returns for any other probing/parsing failure below.
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=60)
            data = json.loads(res.stdout)
            video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
            has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
            duration = float(data.get("format", {}).get("duration", 0.0))
            width = int(video_stream.get("width", 1080))
            height = int(video_stream.get("height", 1920))
            codec_name = video_stream.get("codec_name", "")
            
            # Check rotation tag
            rotation = 0
            for side in video_stream.get("side_data_list", []):
                if "rotation" in side:
                    rotation = int(side["rotation"])
            
            # Check frame rate (30fps standard or 60fps ultra-smooth)
            r_frame_rate = video_stream.get("r_frame_rate", "30/1")
            fps = 30
            if "/" in r_frame_rate:
                try:
                    num, den = r_frame_rate.split("/")
                    if float(den) > 0:
                        raw_fps = float(num) / float(den)
                        fps = 60 if raw_fps >= 45 else 30
                except Exception:
                    pass

            return {
                "duration": duration,
                "width": width,
                "height": height,
                "rotation": rotation,
                "fps": fps,
                "has_audio": has_audio,
                "codec_name": codec_name
            }
        except Exception as e:
            return {"duration": 60.0, "width": 1080, "height": 1920, "rotation": 0, "fps": 30, "has_audio": False, "codec_name": ""}

    @classmethod
    def assemble_tiktok_video(
        cls,
        raw_video_paths: List[str],
        total_duration: float,
        mixed_audio_path: str,
        ass_subtitle_path: str,
        output_mp4_path: str,
        cues: List[Dict] = None,
        ai_matched_shots: List[Dict] = None,
        sticker_path: str = None,
        lut_path: str = None,
        shot_scales: List[float] = None,
        clip_list: List[Dict] = None,
        transitions: List[Any] = None,
        lut_intensity: float = 1.0,
        export_preset: str = "post",
        sticker_position: str = "top_right",
        sticker_scale: float = 1.0,
        sticker_start_time: float = None,
        sticker_end_time: float = None,
        sticker_norm_x: float = None,
        sticker_norm_y: float = None,
        stickers: Optional[List[Dict[str, Any]]] = None,
        effects: Optional[List[Dict[str, Any]]] = None,
        style_preset: Optional[str] = None,
        scrim_spans: list = None,
        auto_blur_landscape: bool = True,
        progress_callback: Optional[Callable[[float, float], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        spotlight: Optional[Dict[str, Any]] = None,
        background_isolation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Takes raw footage, creates fast-paced punch-in cuts synced to audio duration and Gemini Vision scenes,
        burns ASS subtitles, overlays promotional stickers/badges, muxes mixed audio, and renders final MP4.

        `clip_list` (Manual Editor path) switches from "one source video, virtual
        cut points re-cropped from it" (the 1-Click Studio default below) to "N
        real source files concatenated in the given order". Each entry is
        `{"source_path": str, "trim_start": float = 0.0, "trim_end": float | None,
        "speed": float = 1.0, "mirror": bool = False,
        "smooth_slowmo": bool = False}` (`trim_end` omitted/None
        trims to that source's own end; `speed` is clamped to 0.25-4x and
        shortens/lengthens the clip's slot on the timeline accordingly;
        `mirror` flips it horizontally; `smooth_slowmo` fills in synthesized
        frames when the clip is slowed below 0.7x, so the motion does not step
        -- it costs real render time, so it is off unless asked for). Omitting
        `clip_list` entirely keeps every existing caller's behavior unchanged.

        `transitions` (clip_list only) is a list of `len(clip_list) - 1` entries,
        one per boundary between consecutive clips. Each entry is either the
        plain string `"cut"` / `"fade"` (the original shape) or a dict
        `{"type": "wipeleft", "duration": 0.6}`; see XFADE_TRANSITIONS for the
        accepted types, anything else becomes `"fade"`. Omitted entirely, or
        every boundary `"cut"`, keeps the original single `concat` filter --
        the sequential per-boundary reduction only kicks in once a real
        transition is requested.
        """
        out_file = Path(output_mp4_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Per-angle override (see it_angles.py's LOOK_PRESETS) when the
        # caller supplies one; the original alternating pattern is the
        # default for everything else -- this is a strict superset of the
        # old behavior, zero risk to a caller that passes nothing.
        # A manual Editor clip without an explicit zoom is 1.0 in the
        # SequencePlayer.  Only a caller that supplies shot_scales opts into
        # the automatic punch-zoom fallback for clip_list rendering.
        manual_default_scale = 1.0 if not shot_scales else None
        shot_scales = shot_scales or [1.25, 1.0, 1.35, 1.05, 1.3, 1.0]

        # Keep the final delivery cadence at the project standard (30 FPS).
        # Source clips may be 60 FPS, but the filter graph already normalizes
        # every input to FPS before transitions and composition. Re-promoting
        # the output to 60 FPS only duplicates frames and makes platform
        # transcoding less predictable without adding detail.
        target_fps = FPS

        filter_complex = []
        accent_palette = resolve_accent_palette(style_preset=style_preset)
        concat_inputs = []
        video_input_paths: List[str] = []
        clip_durations: List[float] = []
        # Per input: the span to seek to before decoding, or None to decode the
        # whole file. A clip_list gives one input per clip, and each clip wants
        # a few seconds from somewhere in a long source -- cutting that span
        # with a `trim` filter makes the decoder walk the file from frame zero
        # every time, so 21 clips spread over 91 seconds decoded roughly ten
        # times more video than the render uses. Seeking the input instead
        # decodes only the span. Measured on this project's own footage, 8 such
        # clips: 97.7s -> 25.8s, and the output was bit-identical (SSIM 1.0000,
        # PSNR infinite).
        input_seeks: List[Optional[Tuple[float, float]]] = []
        raw_audio_nodes: List[Tuple[str, float, int]] = []
        foreground_inputs: List[Dict[str, Any]] = []
        isolated_subject_nodes: List[Tuple[int, str]] = []
        used_clip_list = bool(clip_list)
        media_probe = MediaProbeCache(cls.get_media_info)

        if (isinstance(background_isolation, Mapping)
                and background_isolation.get("enabled") is True
                and background_isolation.get("scope_mode") == "behind_text_windows"):
            active_ids = background_isolation.get("active_clip_ids")
            intervals_by_clip = background_isolation.get("active_intervals_by_clip")
            if not isinstance(active_ids, list) or not isinstance(intervals_by_clip, Mapping):
                raise ValueError("Scoped Cutout needs an active clip plan before rendering")
            render_ids = {clip.get("id") for clip in (clip_list or [])
                          if isinstance(clip, Mapping) and isinstance(clip.get("id"), str)}
            if any(not isinstance(clip_id, str) or clip_id not in render_ids
                   or clip_id not in intervals_by_clip for clip_id in active_ids):
                raise ValueError("Scoped Cutout clip plan no longer matches the render clips")

        if clip_list:
            # Manual Editor: one real ffmpeg input per clip, each independently
            # scaled/cropped/trimmed to its own in/out point, then concatenated
            # in the given order. (An empty list is falsy, so it never reaches
            # this branch -- it falls through to the legacy path below, same
            # as omitting clip_list entirely.)
            for idx, clip in enumerate(clip_list):
                source_path = Path(clip["source_path"]).resolve()
                # Editing proxies are 540p stand-ins for timeline playback
                # only. One reaching here would export at preview resolution
                # and look like a bad encode rather than a wiring mistake, so
                # this fails closed instead of degrading quietly.
                if is_proxy_path(source_path):
                    raise ValueError(
                        f"ห้ามเรนเดอร์จากไฟล์พรีวิวย่อ (proxy): {source_path} "
                        "— ต้องใช้ไฟล์ต้นฉบับเท่านั้น"
                    )
                video_input_paths.append(str(source_path))

                media_info = media_probe.get(source_path)
                trim_start = float(clip.get("trim_start", 0.0))
                trim_end = clip.get("trim_end")
                if trim_end is None:
                    trim_end = media_info["duration"]
                minimum_source_span = 1 / FPS if isinstance(clip.get("source_window"), Mapping) else 0.2
                source_span = max(minimum_source_span, float(trim_end) - trim_start)
                # FFmpeg can round a decimal frame-edge seek up to the next
                # frame. Start halfway before a bounded frame; decoding still
                # emits its intended first frame and excludes the next topic.
                seek_rate = max(FPS, float(media_info.get("fps") or FPS))
                seek_start = max(0.0, trim_start - .5 / seek_rate) if "source_window" in clip else trim_start
                input_seeks.append((seek_start, source_span))

                # Per-clip speed: setpts stretches/squashes presentation time,
                # so the clip's contribution to the sequence is span/speed.
                # clip_durations MUST carry the post-speed value or every
                # xfade offset after this clip lands in the wrong place.
                speed = float(clip.get("speed") or 1.0)
                speed = min(4.0, max(0.25, speed))
                duration = max(minimum_source_span, source_span / speed)

                # Freeze tail: hold the clip's last frame for N more seconds.
                # It has to be added to `duration` as well, or every xfade
                # offset after this clip lands in the wrong place -- the same
                # trap speed had.
                try:
                    freeze_tail = min(10.0, max(0.0, float(clip.get("freeze_tail") or 0.0)))
                except (TypeError, ValueError):
                    freeze_tail = 0.0
                # Hold the last frame on the output grid. Padding a 60 FPS
                # source first can introduce its next half-frame at the hold
                # boundary and change the picture when a held chunk resumes.
                freeze_filter = (
                    (f"fps={FPS}," if "source_window" in clip else "")
                    + f"tpad=stop_mode=clone:stop_duration={freeze_tail},"
                    if freeze_tail > 0.01 else ""
                )
                duration += freeze_tail
                # Slowing a clip with setpts alone just shows each source
                # frame for longer, so below ~0.7x the motion visibly steps.
                # minterpolate synthesizes the missing frames instead. It is
                # expensive (motion estimation per frame pair), so it is opt-in
                # per clip and only where the judder would actually show.
                smooth_slowmo = bool(clip.get("smooth_slowmo"))
                interpolate_filter = ""
                if smooth_slowmo and speed < SMOOTH_SLOWMO_MAX_SPEED:
                    interpolate_filter = (
                        f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:"
                        f"me_mode=bidir:vsbmc=1,"
                    )
                speed_filter = "" if abs(speed - 1.0) < 1e-3 else f"setpts=PTS/{speed},"
                # Order matters: retime first, then fill in the gaps the
                # retime opened. Interpolating before setpts would generate
                # frames for the original timing and throw them away.
                speed_filter = f"{speed_filter}{interpolate_filter}"

                # Rotation: 90, 180, 270 degrees
                rotation = int(clip.get("rotation") or 0) % 360
                rot_filter = ""
                if rotation == 90:
                    rot_filter = "transpose=1,"
                elif rotation == 180:
                    rot_filter = "hflip,vflip,"
                elif rotation == 270:
                    rot_filter = "transpose=2,"

                # Mirror is a plain horizontal flip, applied before the
                # scale/crop chain so the punch-zoom framing is unaffected.
                mirror_filter = "hflip," if clip.get("mirror") else ""

                # Per-clip colour correction. Only emitted when a value is
                # actually off-default, so an untouched clip's filter chain
                # (and its render time) stays exactly as it was.
                eq_filter = build_eq_filter(clip)

                # Framing: `zoom`/`pan_x`/`pan_y` on the clip win over the
                # alternating punch-zoom pattern, which is what the 1-Click
                # path relies on and the editor's user cannot see coming.
                scale, crop_x, crop_y, scaled_w, scaled_h = frame_geometry(
                    clip, manual_default_scale if manual_default_scale is not None else shot_scales[idx % len(shot_scales)]
                )
                # Record what was actually used. Leaving the fallback implicit
                # is what made the preview disagree with the render: the clip
                # said nothing about zoom, so the preview drew 1.0 while this
                # punched in to 1.35. Writing it back makes the decision
                # visible in the editor and editable next time.
                clip["zoom"] = round(scale, 3)
                clip.setdefault("pan_x", 0.0)
                clip.setdefault("pan_y", 0.0)
                camera_filter = dynamic_camera_filter(
                    clip,
                    scale,
                    input_is_canvas=False,
                )

                node_name = f"clip_{idx}"
                use_bg_blur = bool(clip.get("bg_blur")) or (clip.get("fit_mode") == "blur")
                # A blurred canvas has its own contain/overlay geometry.  Do
                # not guess at a second geometry for the RGBA sequence: an
                # isolation artifact is therefore fail-closed for this one
                # clip and the proven legacy blur graph remains untouched.
                effective_background_isolation = resolve_background_isolation_config(
                    clip, background_isolation
                )
                isolation_requested = (
                    isinstance(effective_background_isolation, Mapping)
                    and effective_background_isolation.get("enabled") is True
                )
                if isolation_requested and use_bg_blur:
                    raise ValueError(
                        f"Background Cutout conflict on clip {idx + 1}: disable bg_blur/fit_mode=blur before rendering"
                    )
                bg_info = None if use_bg_blur else _read_ready_background_sequence(
                    effective_background_isolation,
                    trim_start,
                    source_span,
                )
                if isolation_requested and bg_info is None:
                    raise ValueError(
                        f"Background Cutout is not ready for clip {idx + 1}; prepare a complete artifact before rendering"
                    )
                if bg_info:
                    clip_trim = f"trim=duration={source_span}"
                    fg_input_idx = len(clip_list) + 1 + len(foreground_inputs)
                    bg_info["input_index"] = fg_input_idx
                    if "source_window" in clip and bg_info.get("video_path"):
                        bg_info["video_start"] = max(0.0, bg_info["video_start"] - .5 / FPS)
                    foreground_inputs.append(bg_info)

                    transformed_node = f"{node_name}_transformed"
                    if camera_filter:
                        source_transform = (
                            f"[{idx}:v]trim=start=0:duration={source_span},setpts=PTS-STARTPTS,"
                            f"{speed_filter}{rot_filter}{mirror_filter}{eq_filter}{freeze_filter}"
                            f"fps={FPS},{camera_filter}[{transformed_node}];"
                        )
                        foreground_transform = (
                            f"[{fg_input_idx}:v]{clip_trim},setpts=PTS-STARTPTS,"
                            f"format=rgba,{speed_filter}{rot_filter}{mirror_filter}{eq_filter}{freeze_filter}"
                            f"fps={FPS},{camera_filter}[bg_fg_transformed_{idx}];"
                        )
                    else:
                        one_pass = None if rot_filter or mirror_filter else framing_filters(
                            media_info, scaled_w, scaled_h, crop_x, crop_y
                        )
                        if one_pass:
                            source_transform = (
                                f"[{idx}:v]{clip_trim},setpts=PTS-STARTPTS,"
                                f"{speed_filter}{eq_filter}{freeze_filter}fps={FPS},{one_pass}[{transformed_node}];"
                            )
                            foreground_transform = (
                                f"[{fg_input_idx}:v]{clip_trim},setpts=PTS-STARTPTS,"
                                f"format=rgba,{speed_filter}{eq_filter}{freeze_filter}fps={FPS},{one_pass}[bg_fg_transformed_{idx}];"
                            )
                        else:
                            common_transform = (
                                f"{speed_filter}{rot_filter}{mirror_filter}{eq_filter}{freeze_filter}"
                                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps={FPS},"
                                f"scale={scaled_w}:{scaled_h}:flags=lanczos,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{crop_x}:{crop_y},setsar=1"
                            )
                            source_transform = (
                                f"[{idx}:v]{clip_trim},setpts=PTS-STARTPTS,"
                                f"{common_transform}[{transformed_node}];"
                            )
                            foreground_transform = (
                                f"[{fg_input_idx}:v]{clip_trim},setpts=PTS-STARTPTS,"
                                f"format=rgba,{common_transform}[bg_fg_transformed_{idx}];"
                            )

                    fg_rgba = f"[bg_fg_transformed_{idx}]"
                    fg_rgb = f"[bg_fg_rgb_{idx}]"
                    fg_rgb_output = f"[bg_fg_rgb_{idx}_rgb]"
                    source_base = f"[bg_source_base_{idx}]"
                    fg_alpha = f"[bg_fg_alpha_{idx}]"
                    subject_for_clip = f"[bg_subject_clip_{idx}]"
                    subject_for_base = f"[bg_subject_base_{idx}]"
                    subject_for_overlay = f"[bg_subject_overlay_{idx}]"
                    compositor_plan = bg_info["plan"]
                    compositor_fragment = compositor_plan["filter_fragment"]
                    compositor_fragment = compositor_fragment.replace(
                        "[clip_transformed]", source_base, 1
                    ).replace("[foreground_frame]", fg_rgb_output, 1).replace(
                        "[alpha_frame]", fg_alpha, 1
                    ).replace("[clip_composited]", f"[{node_name}]", 1).replace(
                        "[subject_rgba]", subject_for_clip
                    )
                    compositor_fragment = compositor_fragment.replace(
                        f"alphamerge{subject_for_clip};",
                        f"alphamerge{subject_for_clip};"
                        f"{subject_for_clip}split=2{subject_for_base}{subject_for_overlay};",
                        1,
                    ).replace(
                        f"{source_base}{subject_for_clip}overlay",
                        f"{source_base}{subject_for_base}overlay",
                        1,
                    )
                    # NOTE: do not paint over the base layer here. Round
                    # RESTORE-ORIGINAL-FOOTAGE-BG-FOR-CUTOUT-SANDWICH-20260925
                    # removed a drawbox fill from the PNG-sequence path so the
                    # sandwich reads [original footage] -> [hook text] ->
                    # [cut-out subject] -> [subtitles]. The video-cutout path
                    # added later reintroduced the same fill and flattened the
                    # background back to solid #0B1220. The footage stays as
                    # the base layer; the cut-out subject is composited over
                    # the text above it.
                    filter_complex.append(
                        source_transform
                        + foreground_transform
                        # The subject gets RGB from the same transformed source
                        # as the base. The artifact contributes only its alpha.
                        + f"[{transformed_node}]split=2{source_base}{fg_rgb};"
                        + f"{fg_rgb}format=rgb24{fg_rgb_output};"
                        + f"{fg_rgba}format=rgba,alphaextract{fg_alpha};"
                        + compositor_fragment
                        + ";"
                    )
                    isolated_subject_nodes.append((idx, subject_for_overlay))
                elif use_bg_blur:
                    pre_node = f"c_{idx}_pre"
                    bg_node = f"c_{idx}_bg"
                    fg_node = f"c_{idx}_fg"
                    base_node = f"c_{idx}_base"
                    filter_complex.append(
                        f"[{idx}:v]trim=duration={source_span},setpts=PTS-STARTPTS,"
                        f"{speed_filter}{rot_filter}{mirror_filter}{eq_filter}{freeze_filter}setsar=1,fps={FPS}[{pre_node}];"
                        f"[{pre_node}]split=2[{bg_node}][{fg_node}];"
                        f"[{bg_node}]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},{_BACKGROUND_BLUR_FILTER}[{bg_node}2];"
                        f"[{fg_node}]scale={VIDEO_WIDTH}:-1:force_original_aspect_ratio=decrease[{fg_node}2];"
                        f"[{bg_node}2][{fg_node}2]overlay=(W-w)/2:(H-h)/2,setsar=1[{base_node}];"
                        f"[{base_node}]"
                        f"{dynamic_camera_filter(clip, scale, input_is_canvas=True) or f'scale={scaled_w}:{scaled_h}:flags=lanczos,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{crop_x}:{crop_y},setsar=1'}"
                        f"[{node_name}];"
                    )
                else:
                    # Mirror/rotate change which source pixels end up where, so
                    # the composed window is only safe on the plain path.
                    one_pass = None
                    if camera_filter:
                        one_pass = None
                    elif not rot_filter and not mirror_filter:
                        one_pass = framing_filters(media_info, scaled_w, scaled_h, crop_x, crop_y)
                    if camera_filter:
                        filter_complex.append(
                            f"[{idx}:v]trim=start=0:duration={source_span},setpts=PTS-STARTPTS,"
                            f"{speed_filter}{rot_filter}{mirror_filter}{eq_filter}{freeze_filter}"
                            f"fps={FPS},{camera_filter}[{node_name}];"
                        )
                    elif one_pass:
                        filter_complex.append(
                            f"[{idx}:v]trim=duration={source_span},setpts=PTS-STARTPTS,"
                            f"{speed_filter}{eq_filter}{freeze_filter}fps={FPS},{one_pass}[{node_name}];"
                        )
                    else:
                        filter_complex.append(
                            f"[{idx}:v]trim=duration={source_span},setpts=PTS-STARTPTS,"
                            f"{speed_filter}{rot_filter}{mirror_filter}{eq_filter}{freeze_filter}"
                            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps={FPS},"
                            f"scale={scaled_w}:{scaled_h}:flags=lanczos,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{crop_x}:{crop_y},setsar=1[{node_name}];"
                        )
                concat_inputs.append(f"[{node_name}]")
                clip_durations.append(duration)

                # Raw video audio blend (Optional)
                vol = min(1.0, max(0.0, float(clip.get("volume") or 0.0)))
                if vol > 0.01 and media_info.get("has_audio"):
                    tempo_filter = ""
                    if abs(speed - 1.0) >= 0.05:
                        if 0.5 <= speed <= 2.0:
                            tempo_filter = f",atempo={speed:.3f}"
                        elif speed > 2.0:
                            tempo_filter = f",atempo=2.0,atempo={speed/2.0:.3f}"
                        else:
                            tempo_filter = f",atempo=0.5,atempo={speed/0.5:.3f}"
                    a_node = f"a_clip_{idx}"
                    filter_complex.append(
                        f"[{idx}:a]atrim=duration={source_span},asetpts=PTS-STARTPTS{tempo_filter},volume={vol}[{a_node}];"
                    )
                    raw_audio_nodes.append((a_node, duration, idx))
        else:
            # 1-Click Studio path (unchanged): single source video, virtual cut
            # points computed from cues/AI-matched shots (or a fixed rhythm if
            # neither is given), all re-cropped from the same base stream.
            if not raw_video_paths:
                raise ValueError("No raw video files provided.")
            # Every virtual cut comes out of the same input here, so there is no
            # single span to seek to -- this path keeps its `trim` filters.

            raw_path = Path(raw_video_paths[0]).resolve()
            video_input_paths.append(str(raw_path))
            info = media_probe.get(raw_path)
            raw_duration = info["duration"]

            # Calculate shot segments based on cues and AI-matched Vision shots
            shots = []
            curr_t = 0.0

            if cues:
                for idx, c in enumerate(cues):
                    c_start = c["start"]
                    c_end = c["end"]
                    c_dur = c_end - c_start

                    # Check if Gemini Vision matched a specific scene
                    ai_shot = ai_matched_shots[idx] if ai_matched_shots and idx < len(ai_matched_shots) else None
                    if ai_shot:
                        ai_start = float(ai_shot.get("start_time", 0.0))
                        ai_zoom = float(ai_shot.get("punch_zoom", shot_scales[idx % len(shot_scales)]))
                        scale = min(1.4, max(1.0, ai_zoom))
                        raw_offset = max(0.0, min(ai_start, max(0.0, raw_duration - c_dur - 0.2)))
                    else:
                        scale = shot_scales[idx % len(shot_scales)]
                        raw_offset = (idx * 3.5) % max(1.0, raw_duration - c_dur - 1.0)

                    shots.append({
                        "start": c_start,
                        "end": c_end,
                        "scale": scale,
                        "raw_offset": raw_offset
                    })
            else:
                shot_idx = 0
                while curr_t < total_duration:
                    dur = 2.0
                    end_t = min(curr_t + dur, total_duration)
                    scale = shot_scales[shot_idx % len(shot_scales)]
                    raw_offset = (shot_idx * 3.5) % max(1.0, raw_duration - dur - 1.0)
                    shots.append({
                        "start": curr_t,
                        "end": end_t,
                        "scale": scale,
                        "raw_offset": raw_offset
                    })
                    curr_t = end_t
                    shot_idx += 1

            is_landscape = info.get("width", 1080) > info.get("height", 1920)
            if auto_blur_landscape and is_landscape:
                filter_complex.append(
                    f"[0:v]split=2[raw_bg][raw_fg];"
                    f"[raw_bg]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},{_BACKGROUND_BLUR_FILTER}[raw_bg_blur];"
                    f"[raw_fg]scale={VIDEO_WIDTH}:-1:force_original_aspect_ratio=decrease[raw_fg_fit];"
                    f"[raw_bg_blur][raw_fg_fit]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS}[base_v];"
                )
            else:
                filter_complex.append(
                    f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps={FPS}[base_v];"
                )

            for idx, shot in enumerate(shots):
                s_dur = max(0.2, shot["end"] - shot["start"])
                scale = shot["scale"]
                raw_start_offset = shot.get("raw_offset", 0.0)

                scaled_w = int(VIDEO_WIDTH * scale)
                scaled_h = int(VIDEO_HEIGHT * scale)
                scaled_w = scaled_w if scaled_w % 2 == 0 else scaled_w + 1
                scaled_h = scaled_h if scaled_h % 2 == 0 else scaled_h + 1

                crop_x = int((scaled_w - VIDEO_WIDTH) / 2)
                crop_y = int((scaled_h - VIDEO_HEIGHT) / 2)

                node_name = f"shot_{idx}"
                filter_complex.append(
                    f"[base_v]trim=start={raw_start_offset}:duration={s_dur},setpts=PTS-STARTPTS,"
                    f"scale={scaled_w}:{scaled_h}:flags=lanczos,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{crop_x}:{crop_y}[{node_name}];"
                )
                concat_inputs.append(f"[{node_name}]")

        boundaries = normalize_transitions(transitions)
        # A transition needs two sides. With a single clip the reduction below
        # never runs, so nothing emits [v_concat] -- while the code after it
        # sets current_v to that label regardless, leaving the subtitle burn
        # and every other later stage reading a node ffmpeg was never given.
        # Falling through to the plain concat path defines the label.
        has_transition = (
            used_clip_list
            and len(concat_inputs) >= 2
            and any(b["type"] != "cut" for b in boundaries)
        )

        # Whole-frame clip timing (B5). Each clip chain alone yields about
        # round(duration*FPS) frames, and those per-clip roundings added up
        # along the chain. Pin every clip to the frame count of the cumulative
        # grid plan (pad a short chain with its last frame, cut a long one) and
        # derive every start/offset/duration below from the same integers the
        # preview's buildSegments() uses.
        frame_plan = None
        if used_clip_list and clip_durations:
            frame_plan = plan_sequence_frames(clip_durations, boundaries)
            gridded_inputs = []
            for i, inp in enumerate(concat_inputs):
                name = inp.strip("[]")
                frames = frame_plan["end"][i] - frame_plan["start"][i]
                filter_complex.append(
                    f"[{name}]tpad=stop_mode=clone:stop=3,trim=end_frame={frames}[{name}_grid];"
                )
                gridded_inputs.append(f"[{name}_grid]")
            concat_inputs = gridded_inputs
            clip_durations = [
                frames_to_seconds(frame_plan["end"][i] - frame_plan["start"][i])
                for i in range(len(clip_durations))
            ]

        if has_transition:
            # Sequential reduction: fold clips left-to-right, using xfade at a
            # "fade" boundary and a plain 2-way concat at a "cut" boundary.
            # Only taken once a fade is actually requested -- every existing
            # clip_list caller (no transitions, or all "cut") keeps using the
            # single concat=n=N filter below, unchanged from before this
            # param existed.
            node_names = [inp.strip("[]") for inp in concat_inputs]
            acc_node = node_names[0]
            acc_dur = clip_durations[0]
            last_idx = len(node_names) - 1
            clip_starts = [0.0]

            for i in range(1, len(node_names)):
                boundary = boundaries[i - 1] if i - 1 < len(boundaries) else {"type": "cut", "duration": DEFAULT_TRANSITION_DURATION}
                next_node = node_names[i]
                next_dur = clip_durations[i]
                out_node = "v_concat" if i == last_idx else f"reduce_{i}"

                if boundary["type"] != "cut":
                    # A transition can never eat more than the shorter clip has
                    # to give, or xfade produces a negative offset and ffmpeg
                    # errors out.
                    # Both come off the frame plan: offset = boundary - overlap,
                    # each a whole number of frames (the clamp lives there).
                    fade_dur = frames_to_seconds(frame_plan["overlap"][i])
                    offset = frames_to_seconds(frame_plan["start"][i])
                    # Two things drift out from under a mixed xfade/concat
                    # chain on a real clip_list, neither visible on a single
                    # xfade in isolation:
                    # 1. xfade's own SAR math on non-integer scale/crop
                    #    chains can land a hair off 1:1 (e.g. 11061:11056) --
                    #    harmless alone, but the next concat rejects two
                    #    inputs whose SAR doesn't match exactly.
                    # 2. concat's output timebase doesn't stay pinned to
                    #    the 1/FPS every clip was normalized to upstream, so
                    #    a *second* xfade fed by a concat node downstream
                    #    sees a timebase mismatch against its other input.
                    # `setsar=1,fps={FPS}` after every reduction re-pins
                    # both so nothing downstream ever sees the drift.
                    filter_complex.append(
                        f"[{acc_node}][{next_node}]"
                        f"{xfade_filter_args(boundary['type'], fade_dur, offset, boundary.get('easing'))}"
                        f",setsar=1,fps={FPS}[{out_node}];"
                    )
                    clip_starts.append(offset)
                else:
                    filter_complex.append(
                        f"[{acc_node}][{next_node}]concat=n=2:v=1:a=0,setsar=1,fps={FPS}[{out_node}];"
                    )
                    clip_starts.append(frames_to_seconds(frame_plan["start"][i]))
                acc_dur = frames_to_seconds(frame_plan["end"][i])

                acc_node = out_node
        else:
            filter_complex.append(
                f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[v_concat];"
            )
            # Plain concat: every clip starts where the previous one ended.
            clip_starts = []
            _acc = 0.0
            for _d in clip_durations:
                clip_starts.append(_acc)
                _acc += _d
            if frame_plan is not None:
                clip_starts = [frames_to_seconds(f) for f in frame_plan["start"]]

        current_v = "[v_concat]"

        # The render is cut to the voiceover (-t total_duration). When the
        # clips are shorter than that, the file used to end up with audio over
        # no picture at all -- measured once as a 13.6s video stream inside a
        # 28.3s file. Hold the last frame instead, before the grade/sticker/
        # subtitle passes so those still draw over the held tail.
        # When transitions are used, acc_dur is the actual video span after xfade reduction.
        video_span = acc_dur if has_transition else (sum(clip_durations) if clip_durations else 0.0)
        tail_gap = float(total_duration) - video_span
        if used_clip_list and video_span > 0 and tail_gap > 0.05:
            filter_complex.append(
                f"{current_v}tpad=stop_mode=clone:stop_duration={round(tail_gap + 0.2, 3)}[v_filled];"
            )
            current_v = "[v_filled]"

        # Index of the mixed-audio input once every video input is counted --
        # 1 for the legacy single-source path (unchanged from before), N for
        # a clip_list of N real source files.
        audio_input_idx = len(video_input_paths)
        cmd_inputs = []
        for i, video_path in enumerate(video_input_paths):
            seek = input_seeks[i] if i < len(input_seeks) else None
            if seek:
                start, span = seek
                # -ss before -i seeks the input; ffmpeg still lands on the
                # exact frame (it decodes from the previous keyframe and
                # discards). -t stops the read at the end of the span, so the
                # decoder touches neither the head nor the tail of the file.
                #
                # The span is exact. Padding it and letting the graph trim was
                # tried and every clip came out 0.2s long, which pushed each
                # later clip further out of step -- 8 clips still summed to the
                # right total, so only a frame-by-frame comparison caught it.
                cmd_inputs.extend(["-ss", f"{max(0.0, start):.3f}",
                                   "-t", f"{span:.3f}", "-i", video_path])
            else:
                cmd_inputs.extend(["-i", video_path])
        cmd_inputs.extend(["-i", str(Path(mixed_audio_path).resolve())])
        # Foreground sequences are appended after the mixed-audio input so the
        # legacy audio index remains unchanged.  Each input is derived from a
        # validated artifact id and is cadence-controlled by its manifest.
        for bg_info in foreground_inputs:
            if "video_path" in bg_info:
                cmd_inputs.extend([
                    "-c:v", "libvpx-vp9", "-ss", str(bg_info["video_start"]),
                    "-i", str(bg_info["video_path"]),
                ])
            else:
                cmd_inputs.extend([
                    "-framerate", bg_info["fps_ratio"],
                    "-start_number", str(bg_info["frame_index"]),
                    "-i", f"{bg_info['frame_pattern']}",
                ])

        # Optional 3D LUT color grade -- applied before the sticker overlay and
        # subtitle burn so a brand-colored badge and caption colors are never
        # re-graded along with the footage.
        if lut_path and Path(lut_path).exists():
            lut_path_str = str(Path(lut_path).resolve()).replace('\\', '/').replace(':', '\\:')
            strength = normalize_lut_intensity(lut_intensity if lut_intensity is not None else 1.0)
            if strength >= 0.999:
                filter_complex.append(f"{current_v}lut3d='{lut_path_str}'[v_graded];")
            else:
                # Partial strength = blend the graded frame back over the
                # original. Costs one extra pass, so full strength (the
                # default) still takes the single-filter path above.
                filter_complex.append(
                    f"{current_v}split=2[lut_src][lut_in];"
                    f"[lut_in]lut3d='{lut_path_str}'[lut_out];"
                    f"[lut_src][lut_out]blend=all_mode=normal:all_opacity={strength}[v_graded];"
                )
            current_v = "[v_graded]"

        # Optional SpotlightV1 focus grade. Keep this immediately after the
        # footage grade and before stickers/effects/scrims, matching the
        # Canvas preview order. Product callouts and subtitles remain bright
        # and readable above the focus treatment.
        current_v = _append_spotlight_filter(filter_complex, current_v, spotlight)

        profile = EXPORT_PRESETS.get(export_preset, EXPORT_PRESETS["post"])

        # Optional Promotional Sticker Overlays (Multiple Stickers or legacy single sticker)
        effective_stickers = []
        if isinstance(stickers, list):
            for stk in stickers:
                if not isinstance(stk, dict) or stk.get("hidden"):
                    continue
                stk_badge = stk.get("badge") or stk.get("path")
                p = None
                if stk_badge:
                    b_path = Path(stk_badge)
                    if b_path.exists():
                        p = b_path
                    elif (STICKERS_DIR / stk_badge).exists():
                        p = STICKERS_DIR / stk_badge
                    elif not stk_badge.endswith(".png") and (STICKERS_DIR / f"{stk_badge}.png").exists():
                        p = STICKERS_DIR / f"{stk_badge}.png"
                if p and p.exists():
                    asset_id = p.stem
                    recolor_meta = overlay_asset_recolor_metadata("sticker", asset_id)
                    effective_stickers.append({
                        "path": p,
                        "asset_id": asset_id,
                        "scale": stk.get("scale", 1.0),
                        "norm_x": stk.get("norm_x", stk.get("normX")),
                        "norm_y": stk.get("norm_y", stk.get("normY")),
                        "start": stk.get("start", stk.get("start_time")),
                        "end": stk.get("end", stk.get("end_time")),
                        "position": stk.get("position", "top_right"),
                        "recolor": stk.get("recolor", stk.get("tint")),
                        "recolor_source_hue": stk.get(
                            "recolor_source_hue",
                            stk.get("recolorSourceHue", recolor_meta.get("recolor_source_hue")),
                        ),
                    })
        elif sticker_path and Path(sticker_path).exists():
            effective_stickers.append({
                "path": Path(sticker_path),
                "asset_id": Path(sticker_path).stem,
                "scale": sticker_scale,
                "norm_x": sticker_norm_x,
                "norm_y": sticker_norm_y,
                "start": sticker_start_time,
                "end": sticker_end_time,
                "position": sticker_position,
                "recolor": None,
            })

        for s_idx, stk_info in enumerate(effective_stickers):
            badge_w, badge_x, badge_y = sticker_geometry(
                stk_info.get("position", "top_right"),
                stk_info.get("scale", 1.0),
                norm_x=stk_info.get("norm_x"),
                norm_y=stk_info.get("norm_y"),
                # The filter graph is still at the canonical 1080x1920
                # working raster here; the draft/post profile scale is the
                # final graph node after all overlays have been composited.
                canvas_w=VIDEO_WIDTH,
                canvas_h=VIDEO_HEIGHT,
            )
            # The stickers are appended right after the mixed audio and preceding stickers
            st_idx = audio_input_idx + 1 + len(foreground_inputs) + s_idx
            st_start = stk_info.get("start")
            st_end = stk_info.get("end")
            anim_start, anim_end = 0.5, None
            if st_start is not None or st_end is not None:
                st_start_val = max(0.0, float(st_start if st_start is not None else 0.5))
                anim_start = st_start_val
                if st_end is not None and float(st_end) > st_start_val:
                    enable_expr = f"between(t,{st_start_val:.2f},{float(st_end):.2f})"
                    anim_end = float(st_end)
                else:
                    enable_expr = f"gte(t,{st_start_val:.2f})"
            else:
                enable_expr = "gte(t,0.5)"
            # Entrance/exit animation (overlay_anim_filters). The PNG is
            # looped at the project frame rate so fade/scale see real
            # per-frame time; a single still frame would never animate.
            stk_anim = overlay_anim_filters(
                anim_start,
                anim_end,
                rest_w=badge_w,
                rest_h=overlay_rest_height(stk_info["path"], badge_w),
            )
            if stk_anim:
                cmd_inputs.extend([
                    "-loop", "1", "-framerate", str(FPS),
                    "-t", f"{float(total_duration) + 1.0:.3f}",
                    "-i", str(stk_info["path"].resolve()),
                ])
            else:
                cmd_inputs.extend(["-i", str(stk_info["path"].resolve())])
            stk_node = "sticker_scaled" if s_idx == 0 else f"sticker_scaled_{s_idx}"
            stk_source = f"[{st_idx}:v]"
            recolor_node = f"[sticker_recolored_{s_idx}]"
            recolor = resolve_overlay_recolor(
                stk_info,
                accent_palette,
                kind="sticker",
                asset_id=stk_info.get("asset_id"),
            )
            if recolor:
                filter_complex.append(
                    build_overlay_hue_filter(
                        stk_source,
                        recolor_node,
                        stk_info,
                        accent_palette,
                        kind="sticker",
                        asset_id=stk_info.get("asset_id"),
                    )
                )
                stk_source = recolor_node
            out_label = f"[v_stickered_{s_idx}]"
            filter_complex.append(
                f"{stk_source}scale={badge_w}:-1{',' + stk_anim if stk_anim else ''}[{stk_node}];"
                f"{current_v}[{stk_node}]overlay=x={badge_x}:y={badge_y}:enable='{enable_expr}':format=auto{out_label};"
            )
            current_v = out_label

        # Optional Video Overlay Effects (checkmark/warning/arrow/etc, white-bg
        # clips composited via "multiply" blend so the white vanishes -- these
        # have no real alpha channel, unlike the sticker PNGs above which rely
        # on `overlay`'s native alpha compositing. `overlay` has no blend-mode
        # option, so each instance: split the current frame, crop out just the
        # target region, multiply-blend the effect clip onto that crop, then
        # overlay the (now fully-opaque, already-composited) result back at
        # the same position. `-itsoffset` delays the whole input so its own
        # t=0 lands at the requested global start time, no setpts needed.
        effective_effects = []
        if effects and isinstance(effects, list):
            for fx in effects:
                if not isinstance(fx, dict) or fx.get("hidden"):
                    continue
                fx_id = fx.get("effectId") or fx.get("effect_id")
                if not fx_id:
                    continue
                fx_path = None
                for ext in (".webm", ".mov"):
                    candidate = EFFECTS_DIR / f"{fx_id}{ext}"
                    if candidate.exists():
                        fx_path = candidate
                        break
                if fx_path is None:
                    continue
                recolor_meta = overlay_asset_recolor_metadata("effect", fx_id)
                effective_effects.append({
                    "path": fx_path,
                    "asset_id": fx_id,
                    "scale": fx.get("scale", 1.0),
                    "norm_x": fx.get("norm_x", fx.get("normX", 0.5)),
                    "norm_y": fx.get("norm_y", fx.get("normY", 0.35)),
                    "start": fx.get("start", fx.get("start_time", 0.5)),
                    "end": fx.get("end", fx.get("end_time")),
                    "recolor": fx.get("recolor", fx.get("tint")),
                    "recolor_source_hue": fx.get(
                        "recolor_source_hue",
                        fx.get("recolorSourceHue", recolor_meta.get("recolor_source_hue")),
                    ),
                })

        for e_idx, fx_info in enumerate(effective_effects):
            try:
                factor = min(3.5, max(0.3, float(fx_info.get("scale") or 1.0)))
            except (TypeError, ValueError):
                factor = 1.0
            fx_size = int(round(EFFECT_BASE_SIZE * factor))
            fx_size = fx_size if fx_size % 2 == 0 else fx_size + 1

            # Effects are composited before the final draft/post downscale,
            # just like stickers. Using the output profile dimensions here
            # made draft exports half-sized and shifted relative to Canvas.
            canvas_w, canvas_h = VIDEO_WIDTH, VIDEO_HEIGHT
            # At max scale (3.5x) this is 1260px -- bigger than the "draft"
            # preset's 720-wide canvas (and right at the edge of "post"'s
            # 1080), which made `crop=` below request a region wider than the
            # frame and fail the whole render. Clamp to the smaller canvas
            # dimension minus a couple px of margin.
            fx_size = min(fx_size, canvas_w - 2, canvas_h - 2)
            fx_size = fx_size if fx_size % 2 == 0 else fx_size - 1
            norm_x = float(fx_info.get("norm_x") if fx_info.get("norm_x") is not None else 0.5)
            norm_y = float(fx_info.get("norm_y") if fx_info.get("norm_y") is not None else 0.35)
            px_x = int(round(canvas_w * norm_x - fx_size / 2))
            px_x = max(0, min(canvas_w - fx_size, px_x))
            px_y = int(round(canvas_h * norm_y - fx_size / 2))
            px_y = max(0, min(canvas_h - fx_size, px_y))

            fx_start = max(0.0, float(fx_info.get("start") if fx_info.get("start") is not None else 0.5))
            requested_end = fx_info.get("end")
            natural_duration = 3.0
            try:
                info = media_probe.get(fx_info["path"])
                natural_duration = float(info.get("duration") or 3.0)
            except Exception:
                pass
            window = (float(requested_end) - fx_start) if (requested_end is not None and float(requested_end) > fx_start) else natural_duration
            # The editor preview loops effect media for the whole start..end
            # window (effectPlayback.js wrapEffectTime), so a window longer
            # than the file loops here too instead of stopping at the file's
            # own length. `-t` bounds the looped input to the window so the
            # infinite loop never outlives the effect.
            fx_duration = max(0.1, window)
            fx_end = fx_start + fx_duration

            e_input_idx = audio_input_idx + 1 + len(foreground_inputs) + len(effective_stickers) + e_idx
            loop_args = ["-stream_loop", "-1"] if fx_duration > natural_duration + 1e-3 else []
            cmd_inputs.extend([
                *loop_args,
                "-itsoffset", f"{fx_start:.3f}",
                "-t", f"{fx_duration:.3f}",
                "-i", str(fx_info["path"].resolve()),
            ])

            split_a, split_b = f"[fx_base_a_{e_idx}]", f"[fx_base_b_{e_idx}]"
            bg_node = f"[fx_bg_{e_idx}]"
            fx_scaled_node = f"[fx_scaled_{e_idx}]"
            fx_blended_node = f"[fx_blended_{e_idx}]"
            out_label = f"[v_fx_{e_idx}]"
            enable_expr = f"between(t,{fx_start:.2f},{fx_end:.2f})"

            filter_complex.append(
                f"{current_v}split=2{split_a}{split_b};"
                f"{split_a}crop={fx_size}:{fx_size}:{px_x}:{px_y}{bg_node};"
            )
            fx_source = f"[{e_input_idx}:v]"
            recolor_node = f"[effect_recolored_{e_idx}]"
            recolor = resolve_overlay_recolor(
                fx_info,
                accent_palette,
                kind="effect",
                asset_id=fx_info.get("asset_id"),
            )
            if recolor:
                recolor_filter = build_overlay_hue_filter(
                    fx_source,
                    recolor_node,
                    fx_info,
                    accent_palette,
                    kind="effect",
                    asset_id=fx_info.get("asset_id"),
                )
                filter_complex.append(recolor_filter)
                fx_source = recolor_node
            # Alpha-only entrance/exit (overlay_anim_filters, no scale: the
            # effect clip animates itself). Fading the multiplied crop over
            # the untouched frame == Canvas multiply at globalAlpha; the
            # resting alpha stays 255 so the resting frame is unchanged.
            fx_anim = overlay_anim_filters(
                fx_start,
                float(requested_end) if (requested_end is not None and float(requested_end) > fx_start) else None,
            )
            fx_overlay_node = fx_blended_node
            fx_anim_filter = ""
            if fx_anim:
                fx_overlay_node = f"[fx_anim_{e_idx}]"
                fx_anim_filter = f"{fx_blended_node}format=yuva420p,{fx_anim}{fx_overlay_node};"
            filter_complex.append(
                f"{fx_source}scale={fx_size}:{fx_size}{fx_scaled_node};"
                f"{bg_node}{fx_scaled_node}blend=all_mode=multiply:shortest=1{fx_blended_node};"
                f"{fx_anim_filter}"
                f"{split_b}{fx_overlay_node}overlay=x={px_x}:y={px_y}:enable='{enable_expr}':eof_action=pass{out_label};"
            )
            current_v = out_label

        # Optional gradient backdrop behind the hook banner -- dark at the
        # top of the frame, fading to transparent by ~25% down, so the
        # banner's white/accent text stays readable over busy footage.
        # Synthesized as its own lavfi `color` source right inside the
        # filter graph (no extra -i input needed, unlike the sticker above).
        # One span per overlay that asks for a scrim, so the wash is visible
        # only while that overlay is, fading out over 0.3s alongside its own
        # exit rather than cutting. It used to be a second reading of
        # hook_duration, which is why the wash could only ever start at zero
        # and why a re-roll that lost the banner's scalars rendered the
        # banner with no backdrop at all.
        for span_start, span_end in (scrim_spans or []):
            if span_end <= span_start:
                continue
            grad_h = int(round(VIDEO_HEIGHT * 0.25))
            grad_h = grad_h if grad_h % 2 == 0 else grad_h + 1
            fade_tail = 0.3
            # geq needs cb/cr pinned to 128 (neutral chroma) alongside
            # lum=0 -- leaving them undefined does NOT default to black, it
            # decodes as an off colour (verified: came out visibly green).
            scrim_alpha = 255 * OVERLAY_SCRIM_OPACITY
            alpha_expr = (
                f"{scrim_alpha:g}*(1-Y/H)*(if(lt(T\\,{span_start})\\,0\\,"
                f"if(lt(T\\,{span_end})\\,1\\,"
                f"max(0\\,1-(T-{span_end})/{fade_tail}))))"
            )
            src = f"grad_src_{len(filter_complex)}"
            alpha = f"grad_alpha_{len(filter_complex)}"
            out = f"[v_gradient_{len(filter_complex)}]"
            filter_complex.append(
                f"color=c=black:s={VIDEO_WIDTH}x{grad_h}:d={total_duration + 0.5}[{src}];"
                f"[{src}]format=yuva420p,geq=lum='0':cb='128':cr='128':a='{alpha_expr}'[{alpha}];"
                f"{current_v}[{alpha}]overlay=x=0:y=0:format=auto{out};"
            )
            current_v = out

        # A ready isolation sequence exposes the Subject separately so the
        # Hook can be burned onto the mood background first, then covered by
        # the product. Captions and all other ASS events remain foreground.
        foreground_ass_path = Path(ass_subtitle_path).resolve()
        fonts_dir_str = str(FONTS_DIR.resolve()).replace('\\', '/').replace(':', '\\:')
        if isolated_subject_nodes:
            hook_ass_path, foreground_ass_path = _write_subject_ass_layers(ass_subtitle_path)
            hook_ass_path_str = str(hook_ass_path).replace('\\', '/').replace(':', '\\:')
            hook_out = "[v_hook_subbed]"
            filter_complex.append(
                f"{current_v}subtitles='{hook_ass_path_str}':fontsdir='{fonts_dir_str}'{hook_out};"
            )
            current_v = hook_out
            for clip_idx, subject_node in isolated_subject_nodes:
                start = clip_starts[clip_idx] if clip_idx < len(clip_starts) else 0.0
                shifted = f"[bg_subject_at_{clip_idx}]"
                subject_out = f"[v_subject_{clip_idx}]"
                filter_complex.append(
                    f"{subject_node}setpts=PTS-STARTPTS+{max(0.0, start):.6f}/TB{shifted};"
                    f"{current_v}{shifted}overlay=x=0:y=0:eof_action=pass:repeatlast=0:format=auto{subject_out};"
                )
                current_v = subject_out

        # Escape path for subtitles filter in FFmpeg Windows
        ass_path_str = str(foreground_ass_path).replace('\\', '/').replace(':', '\\:')
        
        # Draft renders answer "did my cut work" in less wall clock; they are
        # not for posting. Subtitles still burn at full resolution -- the .ass
        # coordinates assume it -- and the frame is scaled down afterwards, so
        # the only difference is the encode.
        profile = EXPORT_PRESETS.get(export_preset, EXPORT_PRESETS["post"])
        scaling_down = profile["width"] != VIDEO_WIDTH
        subs_out = "[v_subbed]" if scaling_down else "[v_final]"
        filter_complex.append(
            f"{current_v}subtitles='{ass_path_str}':fontsdir='{fonts_dir_str}'{subs_out}"
        )
        if scaling_down:
            filter_complex.append(
                f";[v_subbed]scale={profile['width']}:{profile['height']}:flags=bilinear[v_final]"
            )

        # Mix raw audio with the main voice/BGM audio if any raw clip volume is active
        if raw_audio_nodes:
            # Each clip's own audio has to be delayed to where that clip sits on
            # the timeline. These used to be concatenated instead, which laid
            # them end-to-end from zero: since clip volume defaults to 0, the
            # common case -- raising the volume on one clip in the middle --
            # played that clip's sound at the very start of the video, and any
            # transition overlap shifted the rest out of sync as well.
            delayed = []
            for node, _dur, clip_idx in raw_audio_nodes:
                start = clip_starts[clip_idx] if clip_idx < len(clip_starts) else 0.0
                delay_ms = int(round(max(0.0, start) * 1000))
                if delay_ms > 0:
                    filter_complex.append(f";[{node}]adelay={delay_ms}|{delay_ms}[{node}_at]")
                    delayed.append(f"[{node}_at]")
                else:
                    delayed.append(f"[{node}]")
            if len(delayed) > 1:
                filter_complex.append(
                    f";{''.join(delayed)}amix=inputs={len(delayed)}:duration=longest:normalize=0[raw_a_mix]"
                )
                raw_a_target = "[raw_a_mix]"
            else:
                raw_a_target = delayed[0]
            filter_complex.append(
                f";{raw_a_target}[{audio_input_idx}:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:attack=5:release=50:level=false[a_final]"
            )
            final_audio_map = "[a_final]"
        else:
            final_audio_map = f"{audio_input_idx}:a"

        full_filter = "".join(filter_complex)

        cmd = [
            "ffmpeg", "-y",
            "-threads", "0",
            # Complex filter graphs (scale/crop/transitions/ASS/overlays) are
            # still CPU work even when AMF encodes on the GPU. Let FFmpeg size
            # that graph's worker pool to the machine instead of serialising it.
            "-filter_complex_threads", "0",
            *cmd_inputs,
            "-filter_complex", full_filter,
            "-map", "[v_final]",
            "-map", final_audio_map,
            *encoder_args(profile),
            "-r", str(target_fps),
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-t", str(total_duration),
            str(out_file)
        ]

        # A long timeline makes this graph (and so the command line) grow with
        # the clip count; Windows rejects a command line over 32,767 chars
        # before ffmpeg even starts. Above the threshold the unchanged graph is
        # handed over through a temp file instead (below it, cmd is untouched).
        # The finally blocks of the two run paths below delete the file.
        cmd, graph_script_file = externalize_filter_graph(cmd, full_filter)

        if progress_callback:
            cmd.insert(1, "pipe:1")
            cmd.insert(1, "-progress")
            cmd.insert(1, "-nostats")
            print(f"Executing video render with real-time progress to: {out_file}...")
            import time
            popen_kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            if os.name == "nt":
                # Isolates ffmpeg into its own process group so it can be
                # signalled/killed independently of this process -- part of
                # the orphan-prevention cleanup below.
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                proc = subprocess.Popen(cmd, **popen_kwargs)
            except BaseException:
                # The try/finally below only starts once ffmpeg has spawned.
                cleanup_graph_file(graph_script_file)
                raise
            _register_ffmpeg_proc(proc)

            render_succeeded = False
            # Defined before the try body so the finally block can always
            # reference it, even if something raises before the watchdog
            # thread itself gets set up below.
            stop_watchdog = threading.Event()
            try:
                stderr_chunks = []
                def _drain_stderr():
                    try:
                        for s_line in iter(proc.stderr.readline, ''):
                            if not s_line:
                                break
                            stderr_chunks.append(s_line)
                            if len(stderr_chunks) > 100:
                                stderr_chunks.pop(0)
                    except Exception:
                        pass

                stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
                stderr_thread.start()

                # `proc.stdout.readline()` below blocks with no timeout of
                # its own, and the cancel check only runs BETWEEN lines -- so
                # an ffmpeg that stops producing progress output (a genuine
                # hang, not just a slow encode segment) would block this loop
                # forever with no way to notice a cancel request either. This
                # watchdog runs on the side: it kills the process once no
                # line has arrived for STALL_TIMEOUT seconds, which unblocks
                # readline() with EOF (closing stdout) so the loop notices
                # promptly instead of hanging indefinitely. 300s matches the
                # timeout this same function already uses for proc.wait()
                # below and for the non-progress render path -- ffmpeg's
                # `-progress` stream normally writes many lines per second,
                # so 5 minutes of total silence is unambiguously a stall,
                # not a slow encode.
                STALL_TIMEOUT = 300
                last_activity = {"t": time.time()}
                stalled = {"v": False}

                def _watch_for_stall():
                    while not stop_watchdog.is_set():
                        if proc.poll() is not None:
                            return
                        if time.time() - last_activity["t"] > STALL_TIMEOUT:
                            stalled["v"] = True
                            try:
                                proc.kill()
                            except Exception:
                                pass
                            return
                        stop_watchdog.wait(2.0)

                stall_thread = threading.Thread(target=_watch_for_stall, daemon=True)
                stall_thread.start()

                last_reported = 0
                cancelled = False
                while True:
                    # Checked every iteration of this loop -- ffmpeg's own
                    # `-progress pipe:1` line cadence (well under a second
                    # per line during a real encode) is what makes this a
                    # timely poll rather than a wait for the next 0.4s report.
                    if cancel_event is not None and cancel_event.is_set():
                        cancelled = True
                        break
                    line = proc.stdout.readline()
                    if not line:
                        break
                    last_activity["t"] = time.time()
                    line = line.strip()
                    if line.startswith("out_time_us="):
                        try:
                            us = float(line.split("=")[1])
                            curr_sec = us / 1_000_000.0
                            now = time.time()
                            if now - last_reported >= 0.4:
                                progress_callback(curr_sec, float(total_duration))
                                last_reported = now
                        except Exception:
                            pass
                    elif line.startswith("out_time_ms="):
                        try:
                            ms = float(line.split("=")[1])
                            curr_sec = ms / 1_000_000.0
                            now = time.time()
                            if now - last_reported >= 0.4:
                                progress_callback(curr_sec, float(total_duration))
                                last_reported = now
                        except Exception:
                            pass

                stop_watchdog.set()
                if stalled["v"]:
                    # The watchdog already killed the process; render_succeeded
                    # stays False so the finally block below still runs its
                    # normal terminate/kill + partial-file cleanup (a no-op on
                    # the terminate/kill since it's already dead) before this
                    # propagates.
                    raise TimeoutError(
                        f"FFmpeg render stalled (no progress output for over {STALL_TIMEOUT}s): {out_file.name}"
                    )

                if cancelled:
                    # render_succeeded stays False, so the finally block below
                    # runs the exact same terminate/kill + partial-file cleanup
                    # as the timeout path, then this raises instead of the
                    # generic RuntimeError/TimeoutExpired other failures raise.
                    raise RenderCancelled("Render cancelled by user request")

                proc.wait(timeout=300)
                stderr_thread.join(timeout=1.0)
                if proc.returncode != 0:
                    err = "".join(stderr_chunks)
                    print("FFmpeg Error details:", err[-500:])
                    raise RuntimeError(f"FFmpeg render failed:\n{err[-500:]}")
                render_succeeded = True
            finally:
                # ffmpeg parsed the graph file at start-up; safe to drop it
                # whether the render succeeded or not.
                cleanup_graph_file(graph_script_file)
                stop_watchdog.set()
                _unregister_ffmpeg_proc(proc)
                if not render_succeeded:
                    # Whatever went wrong -- timeout, KeyboardInterrupt, a
                    # bad returncode raised above, anything unforeseen -- the
                    # ffmpeg child must not be left running. It was writing
                    # only to `out_file` (this call's own -y output target),
                    # so terminating it and removing that one path can never
                    # touch a different, unrelated render.
                    if proc.poll() is None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=5)
                    # Drop the partial file this invocation was writing so a
                    # retry doesn't inherit a half-encoded .mp4. `out_file` is
                    # this call's own -y target -- never touched unless this
                    # specific render failed, so a good file at that path
                    # from a *previous successful* render of the same output
                    # name would already have been truncated by ffmpeg's own
                    # -y the moment this run started writing; nothing here
                    # deletes a file this invocation didn't just corrupt.
                    try:
                        if out_file.exists():
                            out_file.unlink()
                    except OSError:
                        pass
        else:
            print(f"Executing video render to: {out_file}...")
            run_kwargs = dict(capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300)
            if os.name == "nt":
                run_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            render_succeeded = False
            try:
                res = subprocess.run(cmd, **run_kwargs)
                if res.returncode != 0:
                    print("FFmpeg Error details:", res.stderr[-500:])
                    raise RuntimeError(f"FFmpeg render failed:\n{res.stderr[-500:]}")
                render_succeeded = True
            except subprocess.TimeoutExpired:
                raise TimeoutError(f"FFmpeg render timed out after 300 seconds for: {out_file.name}")
            finally:
                cleanup_graph_file(graph_script_file)
                if not render_succeeded:
                    # Mirrors the progress-callback path's cleanup above: a
                    # failed render here (bad returncode or a timeout, which
                    # subprocess.run already kills the child for) must not
                    # leave a half-encoded .mp4 at `out_file` for the next
                    # attempt to trip over.
                    try:
                        if out_file.exists():
                            out_file.unlink()
                    except OSError:
                        pass

        # Automatically generate ultra-lightweight WebP poster thumbnail for instant 0.05s gallery display
        cls.generate_poster_thumbnail(out_file)

        print(f"Render completed successfully: {out_file}")
        return str(out_file)

    @classmethod
    def generate_poster_thumbnail(cls, video_path: Path, poster_path: Optional[Path] = None) -> Optional[Path]:
        """Generates a high-quality, lightweight WebP poster thumbnail (540x960, ~20KB) from the video."""
        video_p = Path(video_path).resolve()
        if not video_p.exists():
            return None
        out_poster = poster_path or video_p.with_suffix(".webp")
        try:
            cmd = [
                "ffmpeg", "-y",
                "-ss", "00:00:01.000",
                "-i", str(video_p),
                "-vframes", "1",
                "-vf", "scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libwebp",
                "-q:v", "80",
                str(out_poster)
            ]
            subprocess.run(cmd, capture_output=True, timeout=15)
            if out_poster.exists() and out_poster.stat().st_size > 0:
                return out_poster
        except Exception as e:
            print(f"Notice: Failed to generate webp poster: {e}")
        return None

if __name__ == "__main__":
    # Quick self-test if test audio exists
    print("VideoEditor ready.")

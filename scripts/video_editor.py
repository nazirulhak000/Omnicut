import subprocess
import json
import math
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass
from typing import Any, List, Dict, Tuple, Callable, Optional
from scripts.config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS, MIN_SHOT_DURATION, MAX_SHOT_DURATION, FONTS_DIR

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


# Per-clip colour ranges. Wider than this and a review clip stops looking like
# the product; ffmpeg's eq would happily accept anything.
EQ_LIMITS = {
    "brightness": (-0.3, 0.3, 0.0),
    "contrast": (0.5, 2.0, 1.0),
    "saturation": (0.0, 3.0, 1.0),
}


def build_eq_filter(clip: Dict[str, Any]) -> str:
    """`eq=...,` for one clip, or "" when every value is still the default."""
    parts = []
    for key, (low, high, default) in EQ_LIMITS.items():
        raw = clip.get(key)
        if raw is None:
            continue
        try:
            value = min(high, max(low, float(raw)))
        except (TypeError, ValueError):
            continue
        if abs(value - default) > 1e-3:
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
STICKER_BASE_WIDTH = 380


def sticker_geometry(position: str, scale: float):
    """(width, x expression, y expression) for the badge overlay."""
    try:
        factor = min(2.0, max(0.4, float(scale or 1.0)))
    except (TypeError, ValueError):
        factor = 1.0
    width = int(round(STICKER_BASE_WIDTH * factor))
    width = width if width % 2 == 0 else width + 1
    x, y = STICKER_POSITIONS.get(position, STICKER_POSITIONS["top_right"])
    return width, x, y

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


def interpolate_keyframes(keyframes: Any, time: float, fallback: float) -> float:
    """Deterministically resolve a numeric keyframe track at local time."""
    points = []
    for point in keyframes if isinstance(keyframes, list) else []:
        try:
            points.append((float(point["time"]), float(point["value"])))
        except (KeyError, TypeError, ValueError):
            continue
    points.sort(key=lambda item: item[0])
    if not points:
        return fallback
    if time <= points[0][0]:
        return points[0][1]
    if time >= points[-1][0]:
        return points[-1][1]
    for (left_t, left_v), (right_t, right_v) in zip(points, points[1:]):
        if time <= right_t:
            ratio = (time - left_t) / (right_t - left_t) if right_t > left_t else 1.0
            return left_v + (right_v - left_v) * ratio
    return points[-1][1]


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
        out.append({"type": kind, "duration": dur})
    return out


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
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        try:
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
        scrim_spans: list = None,
        auto_blur_landscape: bool = True,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> str:
        """
        Takes raw footage, creates fast-paced punch-in cuts synced to audio duration and Gemini Vision scenes,
        burns ASS subtitles, overlays promotional stickers/badges, muxes mixed audio, and renders final MP4.

        `clip_list` (Manual Editor path) switches from "one source video, virtual
        cut points re-cropped from it" (the 1-Click Studio default below) to "N
        real source files concatenated in the given order". Each entry is
        `{"source_path": str, "trim_start": float = 0.0, "trim_end": float | None,
        "speed": float = 1.0, "mirror": bool = False}` (`trim_end` omitted/None
        trims to that source's own end; `speed` is clamped to 0.25-4x and
        shortens/lengthens the clip's slot on the timeline accordingly;
        `mirror` flips it horizontally). Omitting `clip_list` entirely keeps
        every existing caller's behavior unchanged.

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
        shot_scales = shot_scales or [1.25, 1.0, 1.35, 1.05, 1.3, 1.0]

        # Keep the final delivery cadence at the project standard (30 FPS).
        # Source clips may be 60 FPS, but the filter graph already normalizes
        # every input to FPS before transitions and composition. Re-promoting
        # the output to 60 FPS only duplicates frames and makes platform
        # transcoding less predictable without adding detail.
        target_fps = FPS

        filter_complex = []
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
        used_clip_list = bool(clip_list)

        if clip_list:
            # Manual Editor: one real ffmpeg input per clip, each independently
            # scaled/cropped/trimmed to its own in/out point, then concatenated
            # in the given order. (An empty list is falsy, so it never reaches
            # this branch -- it falls through to the legacy path below, same
            # as omitting clip_list entirely.)
            for idx, clip in enumerate(clip_list):
                source_path = Path(clip["source_path"]).resolve()
                video_input_paths.append(str(source_path))

                media_info = cls.get_media_info(str(source_path))
                trim_start = float(clip.get("trim_start", 0.0))
                trim_end = clip.get("trim_end")
                if trim_end is None:
                    trim_end = media_info["duration"]
                source_span = max(0.2, float(trim_end) - trim_start)
                input_seeks.append((trim_start, source_span))

                # Per-clip speed: setpts stretches/squashes presentation time,
                # so the clip's contribution to the sequence is span/speed.
                # clip_durations MUST carry the post-speed value or every
                # xfade offset after this clip lands in the wrong place.
                speed = float(clip.get("speed") or 1.0)
                speed = min(4.0, max(0.25, speed))
                duration = max(0.2, source_span / speed)

                # Freeze tail: hold the clip's last frame for N more seconds.
                # It has to be added to `duration` as well, or every xfade
                # offset after this clip lands in the wrong place -- the same
                # trap speed had.
                try:
                    freeze_tail = min(10.0, max(0.0, float(clip.get("freeze_tail") or 0.0)))
                except (TypeError, ValueError):
                    freeze_tail = 0.0
                freeze_filter = (
                    f"tpad=stop_mode=clone:stop_duration={freeze_tail},"
                    if freeze_tail > 0.01 else ""
                )
                duration += freeze_tail
                speed_filter = "" if abs(speed - 1.0) < 1e-3 else f"setpts=PTS/{speed},"

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
                    clip, shot_scales[idx % len(shot_scales)]
                )
                # Record what was actually used. Leaving the fallback implicit
                # is what made the preview disagree with the render: the clip
                # said nothing about zoom, so the preview drew 1.0 while this
                # punched in to 1.35. Writing it back makes the decision
                # visible in the editor and editable next time.
                clip["zoom"] = round(scale, 3)
                clip.setdefault("pan_x", 0.0)
                clip.setdefault("pan_y", 0.0)

                node_name = f"clip_{idx}"
                use_bg_blur = bool(clip.get("bg_blur")) or (clip.get("fit_mode") == "blur")
                if use_bg_blur:
                    pre_node = f"c_{idx}_pre"
                    bg_node = f"c_{idx}_bg"
                    fg_node = f"c_{idx}_fg"
                    base_node = f"c_{idx}_base"
                    filter_complex.append(
                        f"[{idx}:v]trim=duration={source_span},setpts=PTS-STARTPTS,"
                        f"{speed_filter}{rot_filter}{mirror_filter}{eq_filter}{freeze_filter}setsar=1,fps={FPS}[{pre_node}];"
                        f"[{pre_node}]split=2[{bg_node}][{fg_node}];"
                        f"[{bg_node}]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},boxblur=25:5[{bg_node}2];"
                        f"[{fg_node}]scale={VIDEO_WIDTH}:-1:force_original_aspect_ratio=decrease[{fg_node}2];"
                        f"[{bg_node}2][{fg_node}2]overlay=(W-w)/2:(H-h)/2,setsar=1[{base_node}];"
                        f"[{base_node}]scale={scaled_w}:{scaled_h}:flags=lanczos,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{crop_x}:{crop_y},setsar=1[{node_name}];"
                    )
                else:
                    # Mirror/rotate change which source pixels end up where, so
                    # the composed window is only safe on the plain path.
                    one_pass = None
                    if not rot_filter and not mirror_filter:
                        one_pass = framing_filters(media_info, scaled_w, scaled_h, crop_x, crop_y)
                    if one_pass:
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
            info = cls.get_media_info(raw_path)
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
                    f"[raw_bg]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},boxblur=25:5[raw_bg_blur];"
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
                    fade_dur = min(boundary["duration"], max(0.05, min(acc_dur, next_dur) - 0.05))
                    offset = max(0.0, acc_dur - fade_dur)
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
                        f"[{acc_node}][{next_node}]xfade=transition={boundary['type']}:duration={fade_dur}:offset={offset},setsar=1,fps={FPS}[{out_node}];"
                    )
                    clip_starts.append(offset)
                    acc_dur = acc_dur + next_dur - fade_dur
                else:
                    filter_complex.append(
                        f"[{acc_node}][{next_node}]concat=n=2:v=1:a=0,setsar=1,fps={FPS}[{out_node}];"
                    )
                    clip_starts.append(acc_dur)
                    acc_dur = acc_dur + next_dur

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

        current_v = "[v_concat]"

        # The render is cut to the voiceover (-t total_duration). When the
        # clips are shorter than that, the file used to end up with audio over
        # no picture at all -- measured once as a 13.6s video stream inside a
        # 28.3s file. Hold the last frame instead, before the grade/sticker/
        # subtitle passes so those still draw over the held tail.
        video_span = sum(clip_durations) if clip_durations else 0.0
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

        # Optional 3D LUT color grade -- applied before the sticker overlay and
        # subtitle burn so a brand-colored badge and caption colors are never
        # re-graded along with the footage.
        if lut_path and Path(lut_path).exists():
            lut_path_str = str(Path(lut_path).resolve()).replace('\\', '/').replace(':', '\\:')
            strength = min(1.0, max(0.0, float(lut_intensity if lut_intensity is not None else 1.0)))
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

        # Optional Promotional Sticker Overlay (Top-Right Badge with entry animation)
        if sticker_path and Path(sticker_path).exists():
            badge_w, badge_x, badge_y = sticker_geometry(sticker_position, sticker_scale)
            # The sticker is appended right after the mixed audio, so it is the
            # input following audio_input_idx. Counting `cmd_inputs` instead
            # assumed every input spends exactly two slots ("-i", path), which
            # a clip_list render breaks: each trimmed clip spends six
            # ("-ss", val, "-t", val, "-i", path), inflating the index to
            # 3N+1 instead of N+1 and pointing the overlay at no such stream.
            st_idx = audio_input_idx + 1
            cmd_inputs.extend(["-i", str(Path(sticker_path).resolve())])
            # Scale badge nicely (width ~ 380px) and place in top right or center top
            filter_complex.append(
                f"[{st_idx}:v]scale={badge_w}:-1[sticker_scaled];"
                f"{current_v}[sticker_scaled]overlay=x={badge_x}:y={badge_y}:enable='gte(t,0.5)':format=auto[v_stickered];"
            )
            current_v = "[v_stickered]"

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
            alpha_expr = (
                f"255*(1-Y/H)*(if(lt(T\\,{span_start})\\,0\\,"
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

        # Escape path for subtitles filter in FFmpeg Windows
        ass_path_str = str(Path(ass_subtitle_path).resolve()).replace('\\', '/').replace(':', '\\:')
        fonts_dir_str = str(FONTS_DIR.resolve()).replace('\\', '/').replace(':', '\\:')
        
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

        if progress_callback:
            cmd.insert(1, "pipe:1")
            cmd.insert(1, "-progress")
            cmd.insert(1, "-nostats")
            print(f"Executing video render with real-time progress to: {out_file}...")
            import time
            import threading
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            render_succeeded = False
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

                last_reported = 0
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
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
                proc.wait(timeout=300)
                stderr_thread.join(timeout=1.0)
                if proc.returncode != 0:
                    err = "".join(stderr_chunks)
                    print("FFmpeg Error details:", err[-500:])
                    raise RuntimeError(f"FFmpeg render failed:\n{err[-500:]}")
                render_succeeded = True
            finally:
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
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300)
                if res.returncode != 0:
                    print("FFmpeg Error details:", res.stderr[-500:])
                    raise RuntimeError(f"FFmpeg render failed:\n{res.stderr[-500:]}")
            except subprocess.TimeoutExpired:
                raise TimeoutError(f"FFmpeg render timed out after 300 seconds for: {out_file.name}")

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

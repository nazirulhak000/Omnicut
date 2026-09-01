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
from typing import Any, List, Dict, Tuple
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
            duration = float(data.get("format", {}).get("duration", 0.0))
            width = int(video_stream.get("width", 1080))
            height = int(video_stream.get("height", 1920))
            
            # Check rotation tag
            rotation = 0
            for side in video_stream.get("side_data_list", []):
                if "rotation" in side:
                    rotation = int(side["rotation"])
            
            # If rotated 90 or -90, swap width and height
            if abs(rotation) in (90, 270):
                width, height = height, width

            return {
                "duration": duration,
                "width": width,
                "height": height,
                "rotation": rotation
            }
        except Exception as e:
            return {"duration": 60.0, "width": 1080, "height": 1920, "rotation": 0}

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
        transitions: List[str] = None
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

        filter_complex = []
        concat_inputs = []
        video_input_paths: List[str] = []
        clip_durations: List[float] = []
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

                trim_start = float(clip.get("trim_start", 0.0))
                trim_end = clip.get("trim_end")
                if trim_end is None:
                    trim_end = cls.get_media_info(source_path)["duration"]
                source_span = max(0.2, float(trim_end) - trim_start)

                # Per-clip speed: setpts stretches/squashes presentation time,
                # so the clip's contribution to the sequence is span/speed.
                # clip_durations MUST carry the post-speed value or every
                # xfade offset after this clip lands in the wrong place.
                speed = float(clip.get("speed") or 1.0)
                speed = min(4.0, max(0.25, speed))
                duration = max(0.2, source_span / speed)
                speed_filter = "" if abs(speed - 1.0) < 1e-3 else f"setpts=PTS/{speed},"

                # Mirror is a plain horizontal flip, applied before the
                # scale/crop chain so the punch-zoom framing is unaffected.
                mirror_filter = "hflip," if clip.get("mirror") else ""

                scale = shot_scales[idx % len(shot_scales)]
                scaled_w = int(VIDEO_WIDTH * scale)
                scaled_h = int(VIDEO_HEIGHT * scale)
                scaled_w = scaled_w if scaled_w % 2 == 0 else scaled_w + 1
                scaled_h = scaled_h if scaled_h % 2 == 0 else scaled_h + 1
                crop_x = int((scaled_w - VIDEO_WIDTH) / 2)
                crop_y = int((scaled_h - VIDEO_HEIGHT) / 2)

                node_name = f"clip_{idx}"
                filter_complex.append(
                    f"[{idx}:v]trim=start={trim_start}:duration={source_span},setpts=PTS-STARTPTS,"
                    f"{speed_filter}{mirror_filter}"
                    f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                    f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps={FPS},"
                    f"scale={scaled_w}:{scaled_h}:flags=lanczos,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{crop_x}:{crop_y}[{node_name}];"
                )
                concat_inputs.append(f"[{node_name}]")
                clip_durations.append(duration)
        else:
            # 1-Click Studio path (unchanged): single source video, virtual cut
            # points computed from cues/AI-matched shots (or a fixed rhythm if
            # neither is given), all re-cropped from the same base stream.
            if not raw_video_paths:
                raise ValueError("No raw video files provided.")

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
        has_transition = used_clip_list and any(b["type"] != "cut" for b in boundaries)

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
                    filter_complex.append(
                        f"[{acc_node}][{next_node}]xfade=transition={boundary['type']}:duration={fade_dur}:offset={offset}[{out_node}];"
                    )
                    acc_dur = acc_dur + next_dur - fade_dur
                else:
                    filter_complex.append(
                        f"[{acc_node}][{next_node}]concat=n=2:v=1:a=0[{out_node}];"
                    )
                    acc_dur = acc_dur + next_dur

                acc_node = out_node
        else:
            filter_complex.append(
                f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[v_concat];"
            )

        current_v = "[v_concat]"
        # Index of the mixed-audio input once every video input is counted --
        # 1 for the legacy single-source path (unchanged from before), N for
        # a clip_list of N real source files.
        audio_input_idx = len(video_input_paths)
        cmd_inputs = []
        for video_path in video_input_paths:
            cmd_inputs.extend(["-i", video_path])
        cmd_inputs.extend(["-i", str(Path(mixed_audio_path).resolve())])

        # Optional 3D LUT color grade -- applied before the sticker overlay and
        # subtitle burn so a brand-colored badge and caption colors are never
        # re-graded along with the footage.
        if lut_path and Path(lut_path).exists():
            lut_path_str = str(Path(lut_path).resolve()).replace('\\', '/').replace(':', '\\:')
            filter_complex.append(f"{current_v}lut3d='{lut_path_str}'[v_graded];")
            current_v = "[v_graded]"

        # Optional Promotional Sticker Overlay (Top-Right Badge with entry animation)
        if sticker_path and Path(sticker_path).exists():
            st_idx = len(cmd_inputs) // 2
            cmd_inputs.extend(["-i", str(Path(sticker_path).resolve())])
            # Scale badge nicely (width ~ 380px) and place in top right or center top
            filter_complex.append(
                f"[{st_idx}:v]scale=380:-1[sticker_scaled];"
                f"{current_v}[sticker_scaled]overlay=x=(W-w-40):y=140:enable='gte(t,0.5)':format=auto[v_stickered];"
            )
            current_v = "[v_stickered]"

        # Escape path for subtitles filter in FFmpeg Windows
        ass_path_str = str(Path(ass_subtitle_path).resolve()).replace('\\', '/').replace(':', '\\:')
        fonts_dir_str = str(FONTS_DIR.resolve()).replace('\\', '/').replace(':', '\\:')
        
        filter_complex.append(
            f"{current_v}subtitles='{ass_path_str}':fontsdir='{fonts_dir_str}'[v_final]"
        )

        full_filter = "".join(filter_complex)

        cmd = [
            "ffmpeg", "-y",
            *cmd_inputs,
            "-filter_complex", full_filter,
            "-map", "[v_final]",
            "-map", f"{audio_input_idx}:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(total_duration),
            str(out_file)
        ]

        print(f"Executing video render to: {out_file}...")
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            print("FFmpeg Error details:", res.stderr[-500:])
            # If subtitles filter failed due to path syntax on Windows, fallback without quotes
            raise RuntimeError(f"FFmpeg render failed:\n{res.stderr[-500:]}")

        print(f"Render completed successfully: {out_file}")
        return str(out_file)

if __name__ == "__main__":
    # Quick self-test if test audio exists
    print("VideoEditor ready.")

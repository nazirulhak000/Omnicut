"""
Image Motion Engine for OmniCut Pro Studio.
Converts product still images into dynamic, smooth Ken-Burns 9:16 vertical video clips
synced with narration cues when no raw video footage is available.
"""

import os
import sys
import subprocess
import json
import math
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS, PROJECTS_DIR

class ImageMotionEngine:
    """Creates rhythmic, vertical 9:16 motion slideshows from product photos."""

    @staticmethod
    def _valid_images(image_paths: List[str]) -> List[str]:
        return [str(Path(path).resolve()) for path in image_paths if Path(path).exists()]

    @classmethod
    def _artifact_fingerprint(
        cls, image_paths: List[str], cues: List[Dict], total_duration: float
    ) -> str:
        """Only visual inputs and timing affect a reusable motion artifact."""
        images = []
        for value in cls._valid_images(image_paths):
            path = Path(value)
            stat = path.stat()
            images.append({"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
        cue_timing = [
            {"start": float(cue.get("start", 0.0)), "end": float(cue.get("end", 0.0))}
            for cue in (cues or [])
        ]
        payload = {
            "schema_version": 1,
            "images": images,
            "cue_timing": cue_timing,
            "total_duration": float(total_duration),
            "fps": FPS,
            "canvas": [VIDEO_WIDTH, VIDEO_HEIGHT],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def ensure_motion_video_from_images(
        cls,
        image_paths: List[str],
        cues: List[Dict],
        total_duration: float,
        output_video_path: str,
        project_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> str:
        """Return a current motion artifact, rendering only when visual inputs changed."""
        out_file = Path(output_video_path).resolve()
        metadata_path = out_file.with_suffix(out_file.suffix + ".motion.json")
        fingerprint = cls._artifact_fingerprint(image_paths, cues, total_duration)
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
            if out_file.exists() and out_file.stat().st_size > 0 and metadata.get("fingerprint") == fingerprint:
                print(f"[ImageMotionEngine] Reusing motion video: {out_file}")
                return str(out_file)
        except (OSError, json.JSONDecodeError):
            pass

        result = cls.generate_motion_video_from_images(
            image_paths=image_paths,
            cues=cues,
            total_duration=total_duration,
            output_video_path=str(out_file),
            project_dir=project_dir,
            progress_callback=progress_callback,
        )
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
        temp_path.write_text(json.dumps({"schema_version": 1, "fingerprint": fingerprint}), encoding="utf-8")
        temp_path.replace(metadata_path)
        return result

    @classmethod
    def generate_motion_video_from_images(
        cls,
        image_paths: List[str],
        cues: List[Dict],
        total_duration: float,
        output_video_path: str,
        project_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> str:
        out_file = Path(output_video_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if not image_paths:
            raise ValueError("No images provided for motion video generation.")

        # Clean existing valid image paths
        valid_images = cls._valid_images(image_paths)
        if not valid_images:
            raise FileNotFoundError(f"None of the provided image paths exist: {image_paths}")

        temp_dir = project_dir or (out_file.parent / "motion_temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # If cues are provided, segment duration per cue; otherwise divide equally
        segments = []
        if cues and len(cues) > 0:
            for idx, c in enumerate(cues):
                dur = max(1.5, float(c.get("end", 0.0)) - float(c.get("start", 0.0)))
                segments.append(dur)
        else:
            n = max(1, len(valid_images))
            seg_dur = max(2.0, total_duration / n)
            segments = [seg_dur] * n

        segment_files = []
        total_segments = len(segments)
        for idx, dur in enumerate(segments):
            if progress_callback:
                try:
                    progress_callback(idx + 1, total_segments, f"ช็อตที่ {idx + 1}/{total_segments}")
                except Exception:
                    pass

            img_path = valid_images[idx % len(valid_images)]
            seg_out = temp_dir / f"seg_{idx:03d}.mp4"

            # Check if segment file already exists from previous run (incremental resume)
            if seg_out.exists() and seg_out.stat().st_size > 10240:
                segment_files.append(seg_out)
                continue

            # Alternate Zoom In vs Zoom Out for dynamic feel
            zoom_in = (idx % 2 == 0)
            frames = int(math.ceil(dur * FPS))

            # Dynamic Ken-Burns: smooth zoom rate scaled across the exact duration
            max_zoom = 1.15
            min_zoom = 1.00
            zoom_range = max_zoom - min_zoom
            step = zoom_range / max(1, frames)

            if zoom_in:
                zoom_expr = f"min(1.0+{step:.6f}*on,{max_zoom})"
            else:
                zoom_expr = f"max({max_zoom}-{step:.6f}*on,{min_zoom})"

            # FFmpeg filter:
            # 1. Background: scale image to fill 1080x1920 + boxblur
            # 2. Foreground: scale image to fit nicely within 9:16 + Ken-Burns zoompan
            # 3. Overlay foreground centered on blurred background
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                f"[0:v]scale=960:1280:force_original_aspect_ratio=decrease,"
                f"zoompan=z='{zoom_expr}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=960x1280:fps={FPS}[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v]"
            )

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-t", f"{dur:.2f}",
                "-i", img_path,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-r", str(FPS),
                str(seg_out)
            ]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            segment_files.append(seg_out)

        # Concat all segments
        concat_list_file = temp_dir / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for seg in segment_files:
                # Escape backslashes for FFmpeg
                clean_path = str(seg).replace('\\', '/')
                f.write(f"file '{clean_path}'\n")

        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(out_file)
        ]
        subprocess.run(concat_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f"[ImageMotionEngine] Generated motion video: {out_file} (Duration: ~{sum(segments):.2f}s)")
        return str(out_file)

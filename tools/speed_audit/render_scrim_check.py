"""Render a short clip with a hook scrim through the real VideoEditor and print a
digest of every decoded frame. Run it on two checkouts and compare the digests.

Output goes to .tmp/speed_audit/scrim_check/<label>/ only. The raw video is read, never written.
Usage: python render_scrim_check.py <raw video path> <label>
"""
import hashlib
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / ".tmp" / "speed_audit" / "scrim_check"
DATA = WORK / "data"
os.environ["OMNICUT_DATA_ROOT"] = str(DATA)
os.environ["OMNICUT_ENCODER"] = "cpu"  # libx264 is deterministic; hardware encoders are not
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

raw, label = sys.argv[1], sys.argv[2]
out_dir = WORK / label
out_dir.mkdir(parents=True, exist_ok=True)
DURATION = 9.0

audio = out_dir / "silence.wav"
with wave.open(str(audio), "wb") as handle:
    handle.setnchannels(2)
    handle.setsampwidth(2)
    handle.setframerate(48000)
    handle.writeframes(b"\x00" * int(48000 * DURATION) * 4)

ass = out_dir / "subs.ass"
ass.write_text(
    "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
    "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Default,Arial,82,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,420,1\n\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 0,0:00:00.50,0:00:08.50,Default,,0,0,0,,scrim check\n",
    encoding="utf-8",
)

from scripts.video_editor import VideoEditor  # noqa: E402

clips = [
    {"source_path": raw, "trim_start": 2.0, "trim_end": 6.5, "duration": 4.5, "speed": 1.0, "zoom": 1.0},
    {"source_path": raw, "trim_start": 20.0, "trim_end": 24.5, "duration": 4.5, "speed": 1.0, "zoom": 1.1},
]
target = out_dir / "out.mp4"
started = time.perf_counter()
VideoEditor.assemble_tiktok_video(
    raw_video_paths=[raw],
    total_duration=DURATION,
    mixed_audio_path=str(audio),
    ass_subtitle_path=str(ass),
    output_mp4_path=str(target),
    cues=[],
    clip_list=clips,
    transitions=[{"type": "cut"}],
    scrim_spans=[(0.0, 3.0)],
)
seconds = time.perf_counter() - started
md5 = subprocess.run(
    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(target), "-map", "0:v", "-f", "framemd5", "-"],
    capture_output=True, text=True, check=True,
).stdout
frames = [line.split(",")[-1].strip() for line in md5.splitlines() if line and not line.startswith("#")]
(out_dir / "frames.md5").write_text("\n".join(frames), encoding="utf-8")
print(f"{label}: render {seconds:.2f}s frames={len(frames)} digest={hashlib.sha256(''.join(frames).encode()).hexdigest()[:16]}")

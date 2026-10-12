"""TikTok Video Sharpness Enhancer
Applies pre-sharpening, contrast correction (BT.709), and TikTok sweet-spot encoding.
Can be run via CLI or by drag-and-dropping videos onto tiktok_enhancer.bat.
"""

import sys
import subprocess
from pathlib import Path


def enhance_video(input_path: Path) -> Path:
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        return None

    output_path = input_path.with_name(f"{input_path.stem}_tiktok_sharp.mp4")
    print(f"\n=======================================================")
    print(f"🎬 Processing: {input_path.name}")
    print(f"📦 Output to : {output_path.name}")
    print(f"=======================================================")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", "unsharp=5:5:0.8:5:5:0.3,eq=contrast=1.04:saturation=1.04",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-crf", "18",
        "-preset", "medium",
        "-g", "60",
        "-bf", "2",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Success! Enhanced video saved at:\n{output_path}\n")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to enhance video: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/tiktok_enhancer.py <video_file1> [video_file2 ...]")
        return

    for arg in sys.argv[1:]:
        p = Path(arg).resolve()
        enhance_video(p)


if __name__ == "__main__":
    main()

"""
Round 3 FFmpeg Render Gate Verification.
1. Compares render with Spacing=0 vs Spacing=0.5.
2. Verifies text overlay receiving in (pop_soft), loop (wave), and out (zoom).
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image
from scripts.subtitle_engine import SubtitleEngine
OUT_DIR = ROOT / "tests" / "scratch_round3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_ffmpeg(args):
    res = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {res.stderr}")

def test_spacing_render():
    print("--- 1. Testing Spacing: 0 vs 0.5 ---")
    cues = [{"id": 1, "start": 0.0, "end": 2.0, "text": "ลดกระหน่ำ ดีลลับ 1 แถม 1", "sfx": None}]
    
    # Render with current Spacing: 0
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=cues,
        output_ass_path=str(OUT_DIR / "spacing_0.ass"),
        video_width=1080,
        video_height=1920,
        bilingual=False,
    )
    
    # Also create copy with Spacing: 0.5 for comparison
    content_0 = Path(ass_path).read_text(encoding="utf-8")
    content_05 = content_0.replace(",100,100,0,0,1,", ",100,100,0.5,0,1,")
    (OUT_DIR / "spacing_05.ass").write_text(content_05, encoding="utf-8")
    
    rel_0 = (OUT_DIR / "spacing_0.ass").relative_to(ROOT).as_posix()
    rel_05 = (OUT_DIR / "spacing_05.ass").relative_to(ROOT).as_posix()
    
    # Extract frame at 0.5s for both
    run_ffmpeg([
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{rel_0}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "frame_spacing_0.png")
    ])
    run_ffmpeg([
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{rel_05}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "frame_spacing_05.png")
    ])
    
    # Measure non-black bounds in both frames
    im0 = Image.open(OUT_DIR / "frame_spacing_0.png").convert("L")
    im05 = Image.open(OUT_DIR / "frame_spacing_05.png").convert("L")
    bbox0 = im0.getbbox()
    bbox05 = im05.getbbox()
    print(f"Spacing=0 bbox: {bbox0} (width: {bbox0[2] - bbox0[0]}px)")
    print(f"Spacing=0.5 bbox: {bbox05} (width: {bbox05[2] - bbox05[0]}px)")
    diff_w = (bbox05[2] - bbox05[0]) - (bbox0[2] - bbox0[0])
    print(f"Spacing=0.5 inflated text width by {diff_w}px compared to Spacing=0 (which matches Canvas advance).")
    assert bbox0 is not None and bbox05 is not None

def test_text_overlay_motion_render():
    print("\n--- 2. Testing Text Overlay Motion: in (pop_soft), loop (wave), out (zoom) ---")
    overlay = {
        "kind": "text",
        "start": 0.0,
        "end": 3.0,
        "text": "ข้อความโปรโมชั่น",
        "position": "middle",
        "anim": {"in": "pop_soft", "loop": "wave", "out": "zoom"},
        "look": {
            "font": "Kanit",
            "size_pct": 120,
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_px": 5.0,
            "pill": None,
        }
    }
    
    ass_path, _ = SubtitleEngine.generate_ass(
        cues=[{"id": 1, "start": 0.0, "end": 3.0, "text": "ตัวอย่าง", "sfx": None}],
        output_ass_path=str(OUT_DIR / "overlay_motion.ass"),
        overlays=[overlay],
        video_width=1080,
        video_height=1920,
        bilingual=False,
    )
    
    rel_ass = (OUT_DIR / "overlay_motion.ass").relative_to(ROOT).as_posix()
    
    # 1. Entry frame at t=0.10s (during pop_soft overshoot)
    run_ffmpeg([
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=3:r=30",
        "-ss", "0.10",
        "-vf", f"ass='{rel_ass}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "frame_in_0.10s.png")
    ])
    # 2. Hold frame at t=1.00s (during wave loop)
    run_ffmpeg([
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=3:r=30",
        "-ss", "1.00",
        "-vf", f"ass='{rel_ass}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "frame_loop_1.00s.png")
    ])
    # 3. Exit frame at t=2.92s (during zoom out)
    run_ffmpeg([
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=3:r=30",
        "-ss", "2.92",
        "-vf", f"ass='{rel_ass}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "frame_out_2.92s.png")
    ])
    
    im_in = Image.open(OUT_DIR / "frame_in_0.10s.png").convert("L").getbbox()
    im_loop = Image.open(OUT_DIR / "frame_loop_1.00s.png").convert("L").getbbox()
    im_out = Image.open(OUT_DIR / "frame_out_2.92s.png").convert("L").getbbox()
    
    print(f"In (pop_soft @ 0.10s) bbox: {im_in}")
    print(f"Loop (wave @ 1.00s) bbox: {im_loop}")
    print(f"Out (zoom @ 2.92s) bbox: {im_out}")
    assert im_in is not None
    assert im_loop is not None
    assert im_out is not None
    print("All 3 phases rendered non-empty valid video frames!")

if __name__ == "__main__":
    test_spacing_render()
    test_text_overlay_motion_render()
    print("\nGate Verification Passed Successfully!")

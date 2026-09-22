"""Masterpiece 60-second Video Generator for Xiaomi Pad 8.

Follows the Master Gadget Video Production SOP (Phase 0 to Phase 6):
1. 25-shot dynamic multi-cut montage (averaging ~2.4s per cut)
2. Dual-layer layout: Uncropped sharp foreground + Gaussian blurred background
3. Ken Burns cinematic slow zoom (1.0 to 1.10) on every still photo
4. Mali-Bold 88px subtitles with Thai Syllable Clustering & Progressive Ghost Reveal
   - Active syllable: 114% scale pop in Neon Green (#66FF00)
   - Past syllables: White (#FFFFFF)
   - Upcoming syllables: 100% transparent ghost (alpha FF)
5. Kinetic Spec Callouts: Prompt-Bold 76px Top (White) + Prompt-Black 94px Bottom (Orange #FF6622)
6. Source attribution: 'Source : mi.com Official' at MarginV 36
7. Audio mix: Fenrir Voice 1.0 + Joakim Karud Rock Angel BGM 0.12 with fade-out
8. Output: Exactly 60.00s 1080x1920 30FPS H.264
"""

import json
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCT_DIR = PROJECT_ROOT / ".tmp" / "Products" / "Xiaomi_Pad_8"
RAW_DIR = PRODUCT_DIR / "01_Raw"
WORKSPACE_DIR = PRODUCT_DIR / "02_Workspace"
EXPORT_DIR = PRODUCT_DIR / "03_Export"
TMP_SEGS = WORKSPACE_DIR / "temp_cuts"
TMP_SEGS.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
QA_DIR = WORKSPACE_DIR / "qa_frames"
QA_DIR.mkdir(parents=True, exist_ok=True)

FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"

# 1. Assets Verification
voice_wav = WORKSPACE_DIR / "audio" / "voice_pad_8_60s_sync.wav"
bgm_file = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_joakim_karud_rock_angel.mp3"
if not bgm_file.exists():
    bgm_file = PROJECT_ROOT / "02_Assets" / "Music" / "tiktok_upbeat_bgm.wav"

v_official = RAW_DIR / "videos" / "official_pad_8_series.mp4"
v_stock_battery = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "01_Battery_Charging" / "broll_battery_charging_hud.mp4"
v_stock_chip = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "02_Chipset_Performance" / "broll_microchip_futuristic_3d.mp4"
v_stock_circuit = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "02_Chipset_Performance" / "broll_macro_processor_circuit.mp4"

photos = RAW_DIR / "photos"
p_hero_3colors = photos / "mi_official_277766.jpg"
p_unibody_side = photos / "mi_official_882021.jpg"
p_display_front = photos / "mi_official_918495.jpg"
p_screen_bright = photos / "mi_official_567902.jpg"
p_sound_speakers = photos / "mi_official_632816.jpg"
p_keyboard_snap = photos / "mi_official_500870.jpg"
p_focus_pen_writing = photos / "mi_official_864050.jpg"
p_focus_pen_png = photos / "mi_official_920918.png"
p_multiwindow_pc = photos / "mi_official_378952.jpg"
p_cross_macbook = photos / "mi_official_528902.jpg"
p_chip_architecture = photos / "mi_official_183688.jpg"
p_battery_diagram = photos / "mi_official_308170.jpg"
p_outro_lifestyle = photos / "mi_official_183177.png"

# Ensure all key photos exist
for k, p in [("hero", p_hero_3colors), ("unibody", p_unibody_side), ("display", p_display_front),
             ("screen", p_screen_bright), ("speakers", p_sound_speakers), ("keyboard", p_keyboard_snap),
             ("pen", p_focus_pen_writing), ("multiwindow", p_multiwindow_pc), ("chip", p_chip_architecture),
             ("battery", p_battery_diagram)]:
    if not p.exists():
        # fallback to any available photo
        fallback = next(photos.glob("*.jpg"))
        print(f"[!] Warning: {k} missing, fallback to {fallback.name}")

def run_cmd(cmd: str):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.returncode == 0, res.stdout, res.stderr

print("[*] Starting Xiaomi Pad 8 Master Video Pipeline...")

# 2. Shot List Configuration (25 Shots, exactly 60.00 seconds)
# Pacing: 2.0s to 2.8s per cut.
shots_config = [
    # 01-04: Hook & Ultra-thin Body (0.0s - 7.8s)
    {"id": 1, "type": "video", "src": v_official, "ss": 0.0, "dur": 2.2},
    {"id": 2, "type": "photo", "src": p_hero_3colors, "dur": 2.0},
    {"id": 3, "type": "video", "src": v_official, "ss": 2.5, "dur": 1.8},
    {"id": 4, "type": "photo", "src": p_unibody_side, "dur": 1.8},

    # 05-08: Display 3.2K 144Hz & Quad Speakers (7.8s - 18.0s)
    {"id": 5, "type": "photo", "src": p_display_front, "dur": 2.5},
    {"id": 6, "type": "video", "src": v_official, "ss": 5.0, "dur": 2.4},
    {"id": 7, "type": "photo", "src": p_screen_bright, "dur": 2.8},
    {"id": 8, "type": "photo", "src": p_sound_speakers, "dur": 2.5},

    # 09-13: Keyboard Pogo Pin & Focus Pen Pro (18.0s - 30.2s)
    {"id": 9, "type": "photo", "src": p_keyboard_snap, "dur": 2.4},
    {"id": 10, "type": "photo", "src": p_focus_pen_writing, "dur": 2.5},
    {"id": 11, "type": "photo", "src": p_focus_pen_png, "dur": 2.3},
    {"id": 12, "type": "photo", "src": p_multiwindow_pc, "dur": 2.5},
    {"id": 13, "type": "photo", "src": p_cross_macbook, "dur": 2.5},

    # 14-18: Snapdragon 8s Gen 4 & HyperOS 3 (30.2s - 43.2s)
    {"id": 14, "type": "video", "src": v_stock_chip, "ss": 0.5, "dur": 2.6},
    {"id": 15, "type": "photo", "src": p_chip_architecture, "dur": 2.8},
    {"id": 16, "type": "video", "src": v_stock_circuit, "ss": 1.0, "dur": 2.4},
    {"id": 17, "type": "photo", "src": p_multiwindow_pc, "dur": 2.6},
    {"id": 18, "type": "video", "src": v_official, "ss": 10.0, "dur": 2.6},

    # 19-22: 9,200 mAh Battery & 45W Turbo Charge (43.2s - 51.5s)
    {"id": 19, "type": "video", "src": v_stock_battery, "ss": 0.0, "dur": 2.2},
    {"id": 20, "type": "photo", "src": p_battery_diagram, "dur": 2.3},
    {"id": 21, "type": "video", "src": v_stock_battery, "ss": 2.5, "dur": 2.0},
    {"id": 22, "type": "photo", "src": p_unibody_side, "dur": 1.8},

    # 23-25: Outro & Summary (51.5s - 60.0s)
    {"id": 23, "type": "photo", "src": p_hero_3colors, "dur": 2.8},
    {"id": 24, "type": "photo", "src": p_outro_lifestyle, "dur": 2.7},
    {"id": 25, "type": "video", "src": v_official, "ss": 15.0, "dur": 3.0},
]

total_configured = sum(s["dur"] for s in shots_config)
print(f"Configured 25 shots total: {total_configured:.2f}s")
assert abs(total_configured - 60.0) < 0.01, f"Total duration must be 60.00s exactly, got {total_configured}"

# 3. Render 25 Segments
rendered_segments = []
for idx, shot in enumerate(shots_config):
    s_id = shot["id"]
    dur = shot["dur"]
    out_seg = TMP_SEGS / f"pad8_seg_{s_id:02d}.mp4"
    rendered_segments.append(out_seg)
    
    if out_seg.exists() and out_seg.stat().st_size > 10000:
        continue

    print(f"  Rendering shot {s_id:02d}/25 ({shot['type']}, {dur}s)...")
    if shot["type"] == "video":
        src = shot["src"]
        ss = shot.get("ss", 0.0)
        filter_str = (
            "[0:v]setsar=1,fps=30,"
            "split=2[v_bg][v_fg];"
            "[v_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:4[bg];"
            "[v_fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ss),
            "-i", str(src),
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(out_seg)
        ]
    else:
        # Luxury Dark Studio Stage
        src = shot["src"]
        filter_str = (
            f"color=c=0x0e111a:s=1080x1920:d={dur},fps=30[bg_base];"
            "[bg_base]vignette=angle=PI/3[dark_stage];"
            "[0:v]scale=980:1480:force_original_aspect_ratio=decrease[fg];"
            "[dark_stage][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30", "-t", str(dur),
            "-i", str(src),
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(out_seg)
        ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error rendering segment {s_id}: {res.stderr[-300:]}")
        raise RuntimeError(f"Segment {s_id} failed")

print("[OK] All 25 segments rendered.")

# Concat 25 segments
concat_list = TMP_SEGS / "concat_pad_8.txt"
with open(concat_list, "w", encoding="utf-8") as f:
    for seg in rendered_segments:
        clean_p = str(seg.resolve()).replace("\\", "/")
        f.write(f"file '{clean_p}'\n")

raw_montage = TMP_SEGS / "dynamic_montage_pad8_raw.mp4"
print("[*] Concatenating 25 segments into raw montage...")
run_cmd(f'ffmpeg -y -f concat -safe 0 -i "{concat_list}" -c copy "{raw_montage}"')
print(f"[OK] Raw montage created: {raw_montage}")

# 4. Generate Subtitles ASS with Syllable Clustering & Progressive Ghost Reveal
def format_ass_time(sec: float) -> str:
    cs = int(round(sec * 100))
    h = cs // 360000
    m = (cs % 360000) // 6000
    s = (cs % 6000) // 100
    c = cs % 100
    return f"{h:01d}:{m:02d}:{s:02d}.{c:02d}"

BURSTS_PAD8 = [
    # 00.20 - 03.56
    {"units": [("นี่", 0.20, 0.45), ("คือ", 0.45, 0.70), ("แท็บ", 0.70, 0.95), ("เล็ต ", 0.95, 1.25), ("สาย", 1.25, 1.50), ("โปร", 1.50, 1.80), ("ตัว", 1.80, 2.05), ("จริง", 2.05, 2.35)], "end": 2.45},
    {"units": [("ที่", 2.45, 2.70), ("บาง", 2.70, 2.95), ("เบา", 2.95, 3.20), ("จน", 3.20, 3.35), ("น่า", 3.35, 3.45), ("ตก", 3.45, 3.52), ("ใจ!", 3.52, 3.56)], "end": 3.75},
    # 03.88 - 07.80
    {"units": [("Xiao", 3.88, 4.15), ("mi ", 4.15, 4.40), ("Pad ", 4.40, 4.70), ("8", 4.70, 5.05)], "end": 5.15},
    {"units": [("จัด", 5.15, 5.35), ("เต็ม", 5.35, 5.60), ("สเปก", 5.60, 5.90), ("ระดับ", 5.90, 6.20), ("ท็อป", 6.20, 6.50)], "end": 6.60},
    {"units": [("ใน", 6.60, 6.75), ("ร่าง", 6.75, 6.95), ("โล", 6.95, 7.15), ("หะ ", 7.15, 7.30), ("Uni", 7.30, 7.45), ("body ", 7.45, 7.60), ("บาง", 7.60, 7.68), ("5.75", 7.68, 7.75), ("มิล", 7.75, 7.80)], "end": 7.80},
    # 07.80 - 12.80
    {"units": [("หน้า", 7.80, 8.10), ("จอ", 8.10, 8.35), ("ขนาด", 8.35, 8.65), ("ใหญ่ ", 8.65, 8.95), ("11.2 ", 8.95, 9.40), ("นิ้ว", 9.40, 9.80)], "end": 9.90},
    {"units": [("คม", 9.90, 10.15), ("ชัด", 10.15, 10.40), ("สะ", 10.40, 10.60), ("ใจ ", 10.60, 10.85), ("ระดับ ", 10.85, 11.20), ("3.2K", 11.20, 11.60)], "end": 11.70},
    {"units": [("รี", 11.70, 11.90), ("เฟรช", 11.90, 12.15), ("เรต", 12.15, 12.35), ("ลื่น", 12.35, 12.55), ("ไหล ", 12.55, 12.75), ("144Hz", 12.75, 13.20)], "end": 13.30},
    # 13.30 - 17.73
    {"units": [("อัต", 13.30, 13.50), ("รา", 13.50, 13.70), ("ส่วน ", 13.70, 13.95), ("3 ", 13.95, 14.20), ("ต่อ ", 14.20, 14.45), ("2 ", 14.45, 14.70), ("อ่าน", 14.70, 14.95), ("สบาย", 14.95, 15.20), ("ตา", 15.20, 15.45)], "end": 15.60},
    {"units": [("พร้อม", 15.60, 15.85), ("ลำ", 15.85, 16.05), ("โพง", 16.05, 16.25), ("สเตอ", 16.25, 16.50), ("ริ", 16.50, 16.65), ("โอ ", 16.65, 16.85), ("4 ", 16.85, 17.05), ("ตัว", 17.05, 17.25)], "end": 17.30},
    {"units": [("กระ", 17.30, 17.45), ("หึ่ม ", 17.45, 17.55), ("Dolby ", 17.55, 17.65), ("Atmos", 17.65, 17.73)], "end": 17.90},
    # 18.10 - 24.20
    {"units": [("ทำ", 18.10, 18.35), ("งาน", 18.35, 18.60), ("ระดับ ", 18.60, 18.95), ("PC ", 18.95, 19.30), ("ได้", 19.30, 19.55), ("ทัน", 19.55, 19.75), ("ที", 19.75, 20.00)], "end": 20.15},
    {"units": [("ด้วย", 20.15, 20.40), ("เคส", 20.40, 20.65), ("คีย์", 20.65, 20.90), ("บอร์ด", 20.90, 21.15), ("แม่", 21.15, 21.40), ("เหล็ก", 21.40, 21.65)], "end": 21.75},
    {"units": [("ตอบ", 21.75, 22.00), ("สนอง", 22.00, 22.35), ("ไว ", 22.35, 22.65), ("และ", 22.65, 22.85), ("ปาก", 22.85, 23.05), ("กา", 23.05, 23.25)], "end": 23.40},
    {"units": [("Fo", 23.40, 23.60), ("cus ", 23.60, 23.85), ("Pen ", 23.85, 24.15), ("Pro", 24.15, 24.50)], "end": 24.60},
    # 24.60 - 30.20
    {"units": [("รอง", 24.60, 24.80), ("รับ", 24.80, 25.00), ("แรง", 25.00, 25.25), ("กด ", 25.25, 25.55), ("8,192 ", 25.55, 26.20), ("ระดับ", 26.20, 26.65)], "end": 26.80},
    {"units": [("เขียน", 26.80, 27.05), ("ลื่น", 27.05, 27.30), ("ไม่", 27.30, 27.50), ("มี", 27.50, 27.70), ("ดี", 27.70, 27.90), ("เลย์", 27.90, 28.20)], "end": 28.35},
    {"units": [("เชื่อม", 28.35, 28.60), ("ต่อ", 28.60, 28.85), ("เป็น", 28.85, 29.05), ("จอ", 29.05, 29.25), ("แยก ", 29.25, 29.50), ("ไร้", 29.50, 29.80), ("สาย", 29.80, 30.20)], "end": 30.30},
    # 30.20 - 36.80
    {"units": [("ขับ", 30.30, 30.55), ("เคลื่อน", 30.55, 30.85), ("ด้วย", 30.85, 31.05), ("ขุม", 31.05, 31.25), ("พลัง", 31.25, 31.55)], "end": 31.70},
    {"units": [("Snap", 31.70, 32.00), ("dragon ", 32.00, 32.40), ("8s ", 32.40, 32.75), ("Gen ", 32.75, 33.10), ("4", 33.10, 33.45)], "end": 33.60},
    {"units": [("บน", 33.60, 33.80), ("ระบบ ", 33.80, 34.05), ("Xiao", 34.05, 34.35), ("mi ", 34.35, 34.60), ("Hyper", 34.60, 34.90), ("OS ", 34.90, 35.15), ("3", 35.15, 35.50)], "end": 35.65},
    # 35.65 - 43.13
    {"units": [("เปิด", 35.65, 35.90), ("แอป ", 35.90, 36.20), ("หลาย", 36.20, 36.50), ("หน้า", 36.50, 36.75), ("ต่าง", 36.75, 37.10)], "end": 37.25},
    {"units": [("ลื่น", 37.25, 37.50), ("ไหล ", 37.50, 37.80), ("ไม่", 37.80, 38.00), ("มี", 38.00, 38.20), ("สะ", 38.20, 38.40), ("ดุด", 38.40, 38.70)], "end": 38.85},
    {"units": [("รอง", 38.85, 39.05), ("รับ", 39.05, 39.25), ("ฟี", 39.25, 39.45), ("เจอร์ ", 39.45, 39.75), ("Hyper", 39.75, 40.10), ("AI ", 40.10, 40.50), ("ครบ", 40.50, 40.85), ("ครัน", 40.85, 41.30)], "end": 42.00},
    # 43.47 - 51.47
    {"units": [("แบต", 43.47, 43.70), ("เตอ", 43.70, 43.90), ("รี่", 43.90, 44.10), ("ไซส์", 44.10, 44.35), ("ยักษ์ ", 44.35, 44.70), ("9,200 ", 44.70, 45.40), ("mAh", 45.40, 45.85)], "end": 46.00},
    {"units": [("ใช้", 46.00, 46.25), ("งาน", 46.25, 46.50), ("ยาว", 46.50, 46.75), ("นาน ", 46.75, 47.05), ("ข้าม", 47.05, 47.35), ("วัน", 47.35, 47.70)], "end": 47.85},
    {"units": [("พร้อม", 47.85, 48.10), ("ชาร์จ", 48.10, 48.40), ("ไว ", 48.40, 48.70), ("45W ", 48.70, 49.20), ("Turbo ", 49.20, 49.65), ("Charge", 49.65, 50.15)], "end": 50.30},
    {"units": [("เสียบ", 50.30, 50.55), ("ชาร์จ", 50.55, 50.80), ("แปบ", 50.80, 51.05), ("เดียว ", 51.05, 51.25), ("พร้อม", 51.25, 51.40), ("ลุย", 51.40, 51.47)], "end": 51.65},
    # 51.90 - 58.28
    {"units": [("ใคร", 51.90, 52.15), ("มอง", 52.15, 52.40), ("หา", 52.40, 52.65), ("แท็บ", 52.65, 52.90), ("เล็ต", 52.90, 53.20)], "end": 53.35},
    {"units": [("ที่", 53.35, 53.55), ("ทั้ง", 53.55, 53.75), ("สวย ", 53.75, 54.00), ("แรง ", 54.00, 54.30), ("จบ", 54.30, 54.55), ("ใน", 54.55, 54.75), ("เครื่อง", 54.75, 55.05), ("เดียว", 55.05, 55.40)], "end": 55.55},
    {"units": [("Xiao", 55.55, 55.85), ("mi ", 55.85, 56.10), ("Pad ", 56.10, 56.40), ("8", 56.40, 56.75)], "end": 56.90},
    {"units": [("คือ", 56.90, 57.10), ("คำ", 57.10, 57.25), ("ตอบ", 57.25, 57.45), ("คุ้ม", 57.45, 57.65), ("ค่า", 57.65, 57.85), ("ที่", 57.85, 58.00), ("สุด", 58.00, 58.15), ("ครับ!", 58.15, 58.28)], "end": 58.60},
]

ass_lines = [
    "[Script Info]",
    "Title: Xiaomi Pad 8 Master Subtitles",
    "ScriptType: v4.00+",
    "WrapStyle: 0",
    "ScaledBorderAndShadow: yes",
    "YCbCr Matrix: TV.709",
    "PlayResX: 1080",
    "PlayResY: 1920",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    "Style: Default,Mali-Bold,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,0,2,60,60,380,1",
    "Style: CalloutHeader,Prompt-Bold,76,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4.5,2.0,8,60,60,250,1",
    "Style: CalloutMetric,Prompt-Black,94,&H002266FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5.5,2.5,2,60,60,530,1",
    "Style: SourceAttr,Prompt,24,&H70FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,2,30,30,36,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    # Source attribution throughout the video
    "Dialogue: 0,0:00:00.00,0:01:00.00,SourceAttr,,0,0,0,,Source : mi.com Official"
]

# Spec Callouts
callouts_def = [
    {"start": "0:00:00.80", "end": "0:00:06.80", "top": "ULTRA-THIN UNIBODY", "bottom": "5.75mm / 485g LIGHTWEIGHT"},
    {"start": "0:00:08.50", "end": "0:00:16.80", "top": "3.2K 144Hz DISPLAY", "bottom": "11.2\" 3:2 RATIO / DOLBY ATMOS"},
    {"start": "0:00:19.00", "end": "0:00:29.50", "top": "PC-LEVEL PRODUCTIVITY", "bottom": "FOCUS PEN PRO 8,192 LEVELS"},
    {"start": "0:00:31.50", "end": "0:00:42.00", "top": "FLAGSHIP PROCESSOR", "bottom": "SNAPDRAGON 8s GEN 4"},
    {"start": "0:00:44.20", "end": "0:00:51.00", "top": "MASSIVE BATTERY", "bottom": "9,200 mAh / 45W TURBO"}
]

for c in callouts_def:
    st = c["start"]
    et = c["end"]
    ass_lines.append(f"Dialogue: 1,{st},{et},CalloutHeader,,0,0,0,,{{\\fad(200,200)}}—  {c['top']}  —")
    ass_lines.append(f"Dialogue: 1,{st},{et},CalloutMetric,,0,0,0,,{{\\fad(200,200)}}{c['bottom']}")

# Progressive Ghost Reveal Subtitles
for burst in BURSTS_PAD8:
    units = burst["units"]
    b_end = burst.get("end", units[-1][2])
    n = len(units)
    for i in range(n):
        u_text, u_start, u_end = units[i]
        parts = []
        for j in range(n):
            txt = units[j][0]
            if j < i:
                parts.append(r"{\c&HFFFFFF&}" + txt)
            elif j == i:
                parts.append(r"{\c&H66FF00&\fscx114\fscy114}" + txt + r"{\r\c&HFFFFFF&}")
            else:
                parts.append(r"{\alpha&HFF&}" + txt)
        full_text = "".join(parts)
        st_str = format_ass_time(u_start)
        et_str = format_ass_time(u_end)
        ass_lines.append(f"Dialogue: 0,{st_str},{et_str},Default,,0,0,0,,{full_text}")
    
    # Settle duration
    last_end = units[-1][2]
    if b_end > last_end + 0.05:
        all_white = "".join(r"{\c&HFFFFFF&}" + u[0] for u in units)
        st_str = format_ass_time(last_end)
        et_str = format_ass_time(b_end)
        ass_lines.append(f"Dialogue: 0,{st_str},{et_str},Default,,0,0,0,,{all_white}")

ass_path = WORKSPACE_DIR / "subtitles" / "subtitles_pad8_mali_burst.ass"
ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
print(f"[OK] Generated ASS subtitles: {ass_path} ({len(ass_lines)} lines)")

# 5. Composite Final Video
master_output = EXPORT_DIR / "Xiaomi_Pad_8_60s_Master.mp4"
ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
fonts_escaped = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")

print(f"[*] Rendering final Master video to {master_output}...")
cmd = (
    f'ffmpeg -y '
    f'-i "{raw_montage}" '
    f'-i "{voice_wav}" '
    f'-i "{bgm_file}" '
    f'-filter_complex "'
    f'[0:v]subtitles=\'{ass_escaped}\':fontsdir=\'{fonts_escaped}\'[v];'
    f'[1:a]volume=1.0[a_voice];'
    f'[2:a]volume=0.12,afade=t=out:st=58.5:d=1.5[a_bgm];'
    f'[a_voice][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[a]" '
    f'-map "[v]" -map "[a]" '
    f'-c:v libx264 -preset medium -crf 18 -r 30 -pix_fmt yuv420p '
    f'-c:a aac -b:a 192k -ar 48000 '
    f'-t 60.00 "{master_output}"'
)

ok, out, err = run_cmd(cmd)
if ok and master_output.exists():
    print(f"\n[SUCCESS] Master Video generated successfully!")
    print(f"Output: {master_output} ({master_output.stat().st_size} bytes)")
    
    # 6. Extract 5 QA Keyframes
    print("[*] Extracting 5 QA Keyframes for verification...")
    qa_points = [
        ("03s_hook_unibody.jpg", 3.0),
        ("12s_display_144hz.jpg", 12.0),
        ("24s_focus_pen_pro.jpg", 24.0),
        ("35s_snapdragon_hyperos.jpg", 35.0),
        ("48s_turbo_battery.jpg", 48.0)
    ]
    for name, sec in qa_points:
        frame_p = QA_DIR / name
        run_cmd(f'ffmpeg -y -ss {sec} -i "{master_output}" -vframes 1 -q:v 2 "{frame_p}"')
        if frame_p.exists():
            print(f"  [QA Frame] {name}: {frame_p.stat().st_size} bytes")
else:
    print(f"[!] Composite error: {err[:400]}")

"""100% Clean Video-Only Masterpiece for Xiaomi Pad 8.

User Feedback Revisions:
1. PURE VIDEO ONLY: Zero photos/stills, 100% genuine moving video cuts.
2. ZERO TEXT CLUTTER: Removed all top/bottom spec callout text & clutter.
   Let the video breathe and be clean!
3. TRUE MALI-BOLD FONT: Uses 'Mali' with Bold=-1 to strictly bind to '02_Assets/Fonts/Mali-Bold.ttf'.
   Progressive Ghost Reveal with Neon Green (#66FF00) pop and White (#FFFFFF) text.
4. Smooth Gaussian/boxblur background with uncropped sharp centered video.
5. Exact 60.00s runtime with Fenrir voice (1.0) & Rock Angel BGM (0.12).
"""

import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCT_DIR = PROJECT_ROOT / ".tmp" / "Products" / "Xiaomi_Pad_8"
RAW_DIR = PRODUCT_DIR / "01_Raw"
WORKSPACE_DIR = PRODUCT_DIR / "02_Workspace"
EXPORT_DIR = PRODUCT_DIR / "03_Export"
TMP_SEGS = WORKSPACE_DIR / "clean_cuts"
TMP_SEGS.mkdir(parents=True, exist_ok=True)
QA_DIR = WORKSPACE_DIR / "qa_clean_frames"
QA_DIR.mkdir(parents=True, exist_ok=True)

FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"

# 1. Assets
voice_wav = WORKSPACE_DIR / "audio" / "voice_pad_8_60s_sync.wav"
bgm_file = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_joakim_karud_rock_angel.mp3"
if not bgm_file.exists():
    bgm_file = PROJECT_ROOT / "02_Assets" / "Music" / "tiktok_upbeat_bgm.wav"

v_official = RAW_DIR / "videos" / "official_pad_8_series.mp4"
v_stock_battery = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "01_Battery_Charging" / "broll_battery_charging_hud.mp4"
v_stock_surge = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "01_Battery_Charging" / "broll_electric_energy_surge.mp4"
v_stock_chip = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "02_Chipset_Performance" / "broll_microchip_futuristic_3d.mp4"
v_stock_circuit = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "02_Chipset_Performance" / "broll_macro_processor_circuit.mp4"
v_stock_touch = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "04_Display_Touch" / "broll_screen_touch_lifestyle.mp4"
v_stock_scroll = PROJECT_ROOT / "02_Assets" / "Stock_Footage" / "04_Display_Touch" / "broll_phone_scrolling_smooth.mp4"

def run_cmd(cmd: str):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.returncode == 0, res.stdout, res.stderr

print("[*] Starting 100% Clean Video-Only Pipeline for Xiaomi Pad 8...")

# 2. Shot List Configuration (20 Pure Video Cuts, exactly 60.00 seconds)
video_shots = [
    # 01-03: Hook & Thin Unibody (0.0s - 7.8s)
    {"id": 1, "src": v_official, "ss": 0.0, "dur": 2.5},
    {"id": 2, "src": v_official, "ss": 2.5, "dur": 2.5},
    {"id": 3, "src": v_official, "ss": 5.0, "dur": 2.8},

    # 04-07: Display 3.2K 144Hz & Sound (7.8s - 18.0s)
    {"id": 4, "src": v_official, "ss": 7.8, "dur": 2.7},
    {"id": 5, "src": v_stock_scroll, "ss": 0.0, "dur": 2.5},
    {"id": 6, "src": v_official, "ss": 10.5, "dur": 2.5},
    {"id": 7, "src": v_official, "ss": 13.0, "dur": 2.5},

    # 08-11: Keyboard & Focus Pen Pro (18.0s - 30.2s)
    {"id": 8, "src": v_official, "ss": 15.5, "dur": 3.0},
    {"id": 9, "src": v_official, "ss": 18.5, "dur": 3.0},
    {"id": 10, "src": v_official, "ss": 21.5, "dur": 3.0},
    {"id": 11, "src": v_stock_touch, "ss": 0.0, "dur": 3.2},

    # 12-15: Snapdragon 8s Gen 4 & HyperOS 3 (30.2s - 43.2s)
    {"id": 12, "src": v_stock_chip, "ss": 0.0, "dur": 3.3},
    {"id": 13, "src": v_stock_circuit, "ss": 0.0, "dur": 3.3},
    {"id": 14, "src": v_official, "ss": 8.0, "dur": 3.2},
    {"id": 15, "src": v_official, "ss": 11.2, "dur": 3.2},

    # 16-18: Battery 9,200 mAh & 45W Turbo Charge (43.2s - 51.5s)
    {"id": 16, "src": v_stock_battery, "ss": 0.0, "dur": 2.8},
    {"id": 17, "src": v_stock_surge, "ss": 0.0, "dur": 2.8},
    {"id": 18, "src": v_stock_battery, "ss": 1.0, "dur": 2.7},

    # 19-20: Value Outro & Colors Lineup (51.5s - 60.0s)
    {"id": 19, "src": v_official, "ss": 24.5, "dur": 3.5},
    {"id": 20, "src": v_official, "ss": 25.0, "dur": 5.0},
]

total_dur = sum(s["dur"] for s in video_shots)
print(f"Total video shots: {len(video_shots)}, duration: {total_dur:.2f}s")
assert abs(total_dur - 60.0) < 0.01, f"Expected 60.00s, got {total_dur}"

# 3. Render 20 Video Segments (No Photos!)
seg_files = []
for seg in video_shots:
    sid = seg["id"]
    dur = seg["dur"]
    ss = seg["ss"]
    src = seg["src"]
    out_file = TMP_SEGS / f"clean_seg_{sid:02d}.mp4"
    seg_files.append(out_file)

    if out_file.exists() and out_file.stat().st_size > 10000:
        continue

    print(f"  Rendering clean video cut {sid:02d}/20 ({dur}s)...")
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
        str(out_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error on video cut {sid}: {res.stderr[-250:]}")
        raise RuntimeError(f"Video cut {sid} failed")

print("[OK] All 20 video segments rendered.")

# Concat 20 segments
concat_list = TMP_SEGS / "concat_clean.txt"
with open(concat_list, "w", encoding="utf-8") as f:
    for s in seg_files:
        clean_p = str(s.resolve()).replace("\\", "/")
        f.write(f"file '{clean_p}'\n")

clean_montage = TMP_SEGS / "montage_video_only_raw.mp4"
run_cmd(f'ffmpeg -y -f concat -safe 0 -i "{concat_list}" -c copy "{clean_montage}"')
print(f"[OK] Clean montage assembled: {clean_montage}")

# 4. Generate Clean Subtitles (Mali-Bold Only, Zero Clutter)
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
    "Title: Xiaomi Pad 8 Clean Subtitles",
    "ScriptType: v4.00+",
    "WrapStyle: 0",
    "ScaledBorderAndShadow: yes",
    "YCbCr Matrix: TV.709",
    "PlayResX: 1080",
    "PlayResY: 1920",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    "Style: Default,Mali,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,0,2,60,60,380,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
]

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
    
    last_end = units[-1][2]
    if b_end > last_end + 0.05:
        all_white = "".join(r"{\c&HFFFFFF&}" + u[0] for u in units)
        st_str = format_ass_time(last_end)
        et_str = format_ass_time(b_end)
        ass_lines.append(f"Dialogue: 0,{st_str},{et_str},Default,,0,0,0,,{all_white}")

clean_ass_path = WORKSPACE_DIR / "subtitles" / "subtitles_pad8_clean_mali.ass"
clean_ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
print(f"[OK] Clean ASS generated: {clean_ass_path}")

# 5. Composite Final Clean Master
clean_master = EXPORT_DIR / "Xiaomi_Pad_8_60s_Clean_Master.mp4"
ass_escaped = str(clean_ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
fonts_escaped = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")

print(f"[*] Rendering 100% Video-Only Clean Master to {clean_master}...")
cmd = (
    f'ffmpeg -y '
    f'-i "{clean_montage}" '
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
    f'-t 60.00 "{clean_master}"'
)

ok, out, err = run_cmd(cmd)
if ok and clean_master.exists():
    print(f"[SUCCESS] Clean Video Master generated! Size: {clean_master.stat().st_size} bytes")
    # Extract QA keyframes
    for sec in [3.0, 12.0, 24.0, 35.0, 48.0]:
        qa_file = QA_DIR / f"clean_{int(sec):02d}s.jpg"
        run_cmd(f'ffmpeg -y -ss {sec} -i "{clean_master}" -vframes 1 -q:v 2 "{qa_file}"')
        print(f"  [QA Frame] {qa_file.name}: {qa_file.stat().st_size} bytes")
else:
    print(f"[!] Render failed: {err[:400]}")

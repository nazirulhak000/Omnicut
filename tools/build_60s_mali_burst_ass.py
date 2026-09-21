"""Generate 60-second Mali Masterpiece with Curated Syllable Units & Progressive Ghost Reveal.

Matches the proven aesthetics of `demo_xiaomi_mix_flip_character_bounce.mp4`:
- Curated clean script with correct brand names (Xiaomi MIX Flip, Leica, Snapdragon 8 Gen 3, etc.)
- Thai Syllable Clustering: vowel/tone marks strictly attached to consonants, no broken marks
- Natural spacing between sense groups
- Progressive Ghost Reveal: upcoming words are transparent ({\\alpha&HFF&}), appearing one by one without jumping
- Active syllable pops in Neon Green ({\\c&H66FF00&\\fscx114\\fscy114})
- Past syllables remain in crisp White ({\\c&HFFFFFF&})
- Settle duration after the last word until burst end so viewer reads full line comfortably
"""

import json
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(r"d:\Winona\Programmer\Capcut")
PRODUCT_DIR = PROJECT_ROOT / ".tmp" / "Products" / "Xiaomi_MIX_Flip"
TMP_WORKSPACE = PRODUCT_DIR / "02_Workspace"
TMP_EXPORT = PRODUCT_DIR / "03_Export"
TMP_SEGS = PROJECT_ROOT / ".tmp" / "04_Sandbox" / "pro_segs"
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"
ART_DIR = Path(r"C:\Users\Winon\.gemini\antigravity-ide\brain\17ebf3bb-f0a4-4947-8ff4-4269406b9ba0")

BURSTS_60S = [
    # Seg 00 (00.20 - 01.92): นี่คือ Xiaomi MIX Flip
    {
        "units": [
            ("นี่", 0.20, 0.45),
            ("คือ ", 0.45, 0.75),
            ("Xiao", 0.75, 1.10),
            ("mi ", 1.10, 1.40),
            ("MIX ", 1.40, 1.65),
            ("Flip", 1.65, 1.92)
        ],
        "end": 2.10
    },
    # Seg 01 (02.18 - 04.64): สมาร์ทโฟน จอพับรุ่นแรก จากทาง Xiaomi
    {
        "units": [
            ("ส", 2.18, 2.35),
            ("มาร์ท", 2.35, 2.58),
            ("โฟน ", 2.58, 2.85),
            ("จอ", 2.90, 3.15),
            ("พับ", 3.15, 3.38),
            ("รุ่น", 3.38, 3.58),
            ("แรก ", 3.58, 3.75),
            ("จาก", 3.75, 3.98),
            ("ทาง ", 3.98, 4.20),
            ("Xiao", 4.20, 4.42),
            ("mi", 4.42, 4.64)
        ],
        "end": 4.64
    },
    # Seg 02 (04.64 - 06.48): ที่พัฒนาขึ้น อย่างประณีต
    {
        "units": [
            ("ที่", 4.64, 4.90),
            ("พัฒ", 4.90, 5.15),
            ("นา", 5.15, 5.40),
            ("ขึ้น ", 5.40, 5.70),
            ("อย่าง", 5.70, 6.05),
            ("ประ", 6.05, 6.25),
            ("ณีต", 6.25, 6.48)
        ],
        "end": 6.70
    },
    # Seg 03 (06.74 - 09.34): โดดเด่นด้วย จอด้านนอก ขนาด 4.01 นิ้ว
    {
        "units": [
            ("โดด", 6.74, 6.95),
            ("เด่น", 6.95, 7.15),
            ("ด้วย ", 7.15, 7.35),
            ("จอ", 7.35, 7.58),
            ("ด้าน", 7.58, 7.82),
            ("นอก ", 7.82, 8.10),
            ("ข", 8.10, 8.30),
            ("นาด ", 8.30, 8.55),
            ("4", 8.55, 8.75),
            (".", 8.75, 8.85),
            ("0", 8.85, 8.98),
            ("1 ", 8.98, 9.15),
            ("นิ้ว", 9.15, 9.34)
        ],
        "end": 9.45
    },
    # Seg 04 (09.54 - 11.20): คมชัดระดับ 1.5K
    {
        "units": [
            ("คม", 9.54, 9.75),
            ("ชัด", 9.75, 9.98),
            ("ระ", 9.98, 10.18),
            ("ดับ ", 10.18, 10.40),
            ("1", 10.40, 10.60),
            (".", 10.60, 10.70),
            ("5", 10.70, 10.90),
            ("K", 10.90, 11.20)
        ],
        "end": 11.35
    },
    # Seg 05 (11.46 - 13.74): พร้อมรีเฟรชเรท 120Hz
    {
        "units": [
            ("พร้อม", 11.46, 11.80),
            ("รี", 11.80, 12.05),
            ("เฟรช", 12.05, 12.35),
            ("เรท ", 12.35, 12.65),
            ("1", 12.65, 12.90),
            ("2", 12.90, 13.15),
            ("0", 13.15, 13.40),
            ("Hz", 13.40, 13.74)
        ],
        "end": 13.90
    },
    # Seg 06 (14.06 - 16.36): ออกแบบให้ ใช้งานแอปพลิเคชัน ได้ครบถ้วน
    {
        "units": [
            ("ออก", 14.06, 14.25),
            ("แบบ", 14.25, 14.45),
            ("ให้ ", 14.45, 14.65),
            ("ใช้", 14.65, 14.85),
            ("งาน", 14.85, 15.05),
            ("แอป", 15.05, 15.28),
            ("พลิ", 15.28, 15.48),
            ("เค", 15.48, 15.65),
            ("ชัน ", 15.65, 15.85),
            ("ได้", 15.85, 16.05),
            ("ครบ", 16.05, 16.20),
            ("ถ้วน", 16.20, 16.36)
        ],
        "end": 16.36
    },
    # Seg 07 (16.36 - 17.64): โดยไม่ต้อง กางเครื่อง
    {
        "units": [
            ("โดย", 16.36, 16.62),
            ("ไม่", 16.62, 16.85),
            ("ต้อง ", 16.85, 17.10),
            ("กาง", 17.10, 17.35),
            ("เครื่อง", 17.35, 17.64)
        ],
        "end": 18.00
    },
    # Seg 08 (18.14 - 20.70): เมื่อกางออก จะพบกับหน้าจอหลัก OLED
    {
        "units": [
            ("เมื่อ", 18.14, 18.40),
            ("กาง", 18.40, 18.65),
            ("ออก ", 18.65, 18.90),
            ("จะ", 18.90, 19.10),
            ("พบ", 19.10, 19.30),
            ("กับ", 19.30, 19.50),
            ("หน้า", 19.50, 19.72),
            ("จอ", 19.72, 19.92),
            ("หลัก ", 19.92, 20.15),
            ("O", 20.15, 20.35),
            ("LED", 20.35, 20.70)
        ],
        "end": 20.90
    },
    # Seg 09 (21.06 - 22.62): ขนาด 6.86 นิ้ว
    {
        "units": [
            ("ข", 21.06, 21.25),
            ("นาด ", 21.25, 21.48),
            ("6", 21.48, 21.72),
            (".", 21.72, 21.82),
            ("8", 21.82, 22.05),
            ("6 ", 22.05, 22.30),
            ("นิ้ว", 22.30, 22.62)
        ],
        "end": 22.75
    },
    # Seg 10 (22.86 - 24.68): สว่างสูงสุดถึง 3,000 nits
    {
        "units": [
            ("สว่าง", 22.86, 23.15),
            ("สูง", 23.15, 23.38),
            ("สุด", 23.38, 23.58),
            ("ถึง ", 23.58, 23.80),
            ("3", 23.80, 24.00),
            (",", 24.00, 24.05),
            ("000 ", 24.05, 24.32),
            ("nits", 24.32, 24.68)
        ],
        "end": 24.80
    },
    # Seg 11 (24.92 - 26.72): มอบภาพที่คมชัด และสบายตา
    {
        "units": [
            ("มอบ", 24.92, 25.18),
            ("ภาพ", 25.18, 25.42),
            ("ที่", 25.42, 25.62),
            ("คม", 25.62, 25.85),
            ("ชัด ", 25.85, 26.10),
            ("และ", 26.10, 26.30),
            ("ส", 26.30, 26.45),
            ("บาย", 26.45, 26.58),
            ("ตา", 26.58, 26.72)
        ],
        "end": 26.72
    },
    # Seg 12 (26.72 - 27.80): ในทุกสภาพแสง
    {
        "units": [
            ("ใน", 26.72, 26.95),
            ("ทุก", 26.95, 27.20),
            ("ส", 27.20, 27.35),
            ("ภาพ", 27.35, 27.55),
            ("แสง", 27.55, 27.80)
        ],
        "end": 28.15
    },
    # Seg 13 (28.28 - 29.36): ด้านการถ่ายภาพ
    {
        "units": [
            ("ด้าน", 28.28, 28.55),
            ("การ", 28.55, 28.80),
            ("ถ่าย", 28.80, 29.08),
            ("ภาพ", 29.08, 29.36)
        ],
        "end": 29.36
    },
    # Seg 14 (29.36 - 30.82): ผสานพลัง กล้องคู่ระดับโปร
    {
        "units": [
            ("ผ", 29.36, 29.55),
            ("สาน", 29.55, 29.75),
            ("พ", 29.75, 29.90),
            ("ลัง ", 29.90, 30.05),
            ("กล้อง", 30.05, 30.25),
            ("คู่", 30.25, 30.45),
            ("ระ", 30.45, 30.60),
            ("ดับ", 30.60, 30.72),
            ("โปร", 30.72, 30.82)
        ],
        "end": 30.82
    },
    # Seg 15 (30.82 - 32.10): 50 ล้านพิกเซล
    {
        "units": [
            ("5", 30.82, 31.05),
            ("0 ", 31.05, 31.28),
            ("ล้าน", 31.28, 31.55),
            ("พิก", 31.55, 31.80),
            ("เซล", 31.80, 32.10)
        ],
        "end": 32.10
    },
    # Seg 16 (32.10 - 33.68): ที่พัฒนาร่วมกับ Leica
    {
        "units": [
            ("ที่", 32.10, 32.32),
            ("พัฒ", 32.32, 32.55),
            ("นา", 32.55, 32.78),
            ("ร่วม", 32.78, 33.02),
            ("กับ ", 33.02, 33.22),
            ("Lei", 33.22, 33.45),
            ("ca", 33.45, 33.68)
        ],
        "end": 33.80
    },
    # Seg 17 (33.90 - 35.08): พร้อมเลนส์ Summilux
    {
        "units": [
            ("พร้อม", 33.90, 34.20),
            ("เลนส์ ", 34.20, 34.45),
            ("Sum", 34.45, 34.72),
            ("mi", 34.72, 34.90),
            ("lux", 34.90, 35.08)
        ],
        "end": 35.08
    },
    # Seg 18 (35.08 - 36.80): ให้โทนภาพ และมิติแสงเงา
    {
        "units": [
            ("ให้", 35.08, 35.30),
            ("โทน", 35.30, 35.55),
            ("ภาพ ", 35.55, 35.80),
            ("และ", 35.80, 36.02),
            ("มิ", 36.02, 36.22),
            ("ติ", 36.22, 36.38),
            ("แสง", 36.38, 36.58),
            ("เงา", 36.58, 36.80)
        ],
        "end": 36.80
    },
    # Seg 19 (36.80 - 38.44): ที่คมชัด เป็นธรรมชาติ
    {
        "units": [
            ("ที่", 36.80, 37.05),
            ("คม", 37.05, 37.30),
            ("ชัด ", 37.30, 37.55),
            ("เป็น", 37.55, 37.80),
            ("ธรรม", 37.80, 38.05),
            ("ชา", 38.05, 38.22),
            ("ติ", 38.22, 38.44)
        ],
        "end": 38.65
    },
    # Seg 20 (38.78 - 40.18): ขับเคลื่อนด้วย ขุมพลังเรือธง
    {
        "units": [
            ("ขับ", 38.78, 39.02),
            ("เคลื่อน", 39.02, 39.28),
            ("ด้วย ", 39.28, 39.50),
            ("ขุม", 39.50, 39.70),
            ("พ", 39.70, 39.82),
            ("ลัง", 39.82, 39.95),
            ("เรือ", 39.95, 40.08),
            ("ธง", 40.08, 40.18)
        ],
        "end": 40.18
    },
    # Seg 21 (40.18 - 42.44): Snapdragon 8 Gen 3
    {
        "units": [
            ("Snap", 40.18, 40.55),
            ("dra", 40.55, 40.85),
            ("gon ", 40.85, 41.15),
            ("8 ", 41.15, 41.50),
            ("Gen ", 41.50, 41.95),
            ("3", 41.95, 42.44)
        ],
        "end": 42.44
    },
    # Seg 22a (42.44 - 43.80): เสริมด้วยระบบระบายความร้อน
    {
        "units": [
            ("เสริม", 42.44, 42.68),
            ("ด้วย ", 42.68, 42.90),
            ("ระ", 42.90, 43.08),
            ("บบ", 43.08, 43.24),
            ("ระ", 43.24, 43.38),
            ("บาย", 43.38, 43.52),
            ("ความ", 43.52, 43.68),
            ("ร้อน", 43.68, 43.80)
        ],
        "end": 43.80
    },
    # Seg 22b (43.80 - 45.24): 3D Dual-Vapor Chamber
    {
        "units": [
            ("3D ", 43.80, 44.15),
            ("Dual-", 44.15, 44.45),
            ("Vapor ", 44.45, 44.80),
            ("Chamber", 44.80, 45.24)
        ],
        "end": 45.24
    },
    # Seg 23 (45.24 - 46.54): มอบความลื่นไหล
    {
        "units": [
            ("มอบ", 45.24, 45.55),
            ("ความ", 45.55, 45.85),
            ("ลื่น", 45.85, 46.18),
            ("ไหล", 46.18, 46.54)
        ],
        "end": 46.54
    },
    # Seg 24 (46.54 - 47.48): และประสิทธิภาพสูงสุด
    {
        "units": [
            ("และ", 46.54, 46.72),
            ("ประ", 46.72, 46.90),
            ("สิทธิ", 46.90, 47.12),
            ("ภาพ", 47.12, 47.30),
            ("สูง", 47.30, 47.40),
            ("สุด", 47.40, 47.48)
        ],
        "end": 47.48
    },
    # Seg 25 (47.48 - 48.64): ในทุกการประมวลผล
    {
        "units": [
            ("ใน", 47.48, 47.70),
            ("ทุก", 47.70, 47.95),
            ("การ", 47.95, 48.18),
            ("ประ", 48.18, 48.35),
            ("มวล", 48.35, 48.50),
            ("ผล", 48.50, 48.64)
        ],
        "end": 48.64
    },
    # Seg 26 (48.64 - 50.42): และอัดแน่นด้วย แบตเตอรี่ความจุใหญ่
    {
        "units": [
            ("และ", 48.64, 48.88),
            ("อัด", 48.88, 49.10),
            ("แน่น", 49.10, 49.32),
            ("ด้วย ", 49.32, 49.55),
            ("แบต", 49.55, 49.78),
            ("เตอ", 49.78, 49.95),
            ("รี่", 49.95, 50.12),
            ("ความ", 50.12, 50.28),
            ("จุ", 50.28, 50.35),
            ("ใหญ่", 50.35, 50.42)
        ],
        "end": 50.42
    },
    # Seg 27 (50.42 - 52.60): 4,780 mAh
    {
        "units": [
            ("4", 50.42, 50.72),
            (",", 50.72, 50.78),
            ("7", 50.78, 51.05),
            ("8", 51.05, 51.35),
            ("0 ", 51.35, 51.70),
            ("m", 51.70, 52.00),
            ("A", 52.00, 52.30),
            ("h", 52.30, 52.60)
        ],
        "end": 52.75
    },
    # Seg 28 (52.82 - 54.50): รองรับชาร์จไว 67W
    {
        "units": [
            ("รอง", 52.82, 53.08),
            ("รับ", 53.08, 53.30),
            ("ชาร์จ", 53.30, 53.60),
            ("ไว ", 53.60, 53.85),
            ("6", 53.85, 54.10),
            ("7", 54.10, 54.30),
            ("W", 54.30, 54.50)
        ],
        "end": 54.65
    },
    # Seg 29 (54.76 - 56.22): ตอบโจทย์ การใช้งานระดับโปร
    {
        "units": [
            ("ตอบ", 54.76, 55.05),
            ("โจทย์ ", 55.05, 55.30),
            ("การ", 55.30, 55.50),
            ("ใช้", 55.50, 55.70),
            ("งาน", 55.70, 55.88),
            ("ระ", 55.88, 56.00),
            ("ดับ", 56.00, 56.12),
            ("โปร", 56.12, 56.22)
        ],
        "end": 56.22
    },
    # Seg 30 (56.22 - 57.92): ได้อย่างมั่นใจ ตลอดทั้งวันครับ
    {
        "units": [
            ("ได้", 56.22, 56.45),
            ("อย่าง", 56.45, 56.68),
            ("มั่น", 56.68, 56.90),
            ("ใจ ", 56.90, 57.10),
            ("ต", 57.10, 57.22),
            ("ลอด", 57.22, 57.42),
            ("ทั้ง", 57.42, 57.60),
            ("วัน", 57.60, 57.75),
            ("ครับ", 57.75, 57.92)
        ],
        "end": 59.00
    }
]

def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"

ass_lines = [
    "[Script Info]",
    "ScriptType: v4.00+",
    "PlayResX: 1080",
    "PlayResY: 1920",
    "ScaledBorderAndShadow: yes",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    # Subtitle font: Mali, size 88, White primary, Black outline 5.2, MarginV 380
    "Style: Default,Mali,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,0,2,20,20,380,1",
    # Callouts: Prompt Top White + Prompt-Black Vibrant Orange
    "Style: CalloutTop,Prompt,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,8,40,40,250,1",
    "Style: CalloutBottom,Prompt-Black,94,&H002266FF,&H002266FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5.5,2.5,2,40,40,530,1",
    # Watermark
    "Style: Watermark,Prompt,24,&H70FFFFFF,&H70FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,2.0,0,2,20,20,36,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
]

# A. Watermark
ass_lines.append("Dialogue: 0,0:00:00.00,0:01:00.00,Watermark,,0,0,0,,Source : mi.com Official")

# B. Callouts
callouts_def = [
    {
        "start": "0:00:06.74", "end": "0:00:15.00",
        "top": "OUTER DISPLAY",
        "bottom": "4.01\" 1.5K 120Hz"
    },
    {
        "start": "0:00:18.14", "end": "0:00:26.50",
        "top": "INNER LTPO OLED",
        "bottom": "6.86\" 3,000 NITS"
    },
    {
        "start": "0:00:28.28", "end": "0:00:36.50",
        "top": "LEICA DUAL OPTICS",
        "bottom": "50MP SUMMILUX"
    },
    {
        "start": "0:00:38.78", "end": "0:00:46.50",
        "top": "SNAPDRAGON 8 GEN 3",
        "bottom": "3D DUAL-VC COOLING"
    },
    {
        "start": "0:00:48.64", "end": "0:00:55.00",
        "top": "SURGE BATTERY",
        "bottom": "4,780 mAh / 67W"
    }
]

for c in callouts_def:
    st = c["start"]
    et = c["end"]
    top_t = c["top"]
    bot_t = c["bottom"]
    ass_lines.append(f"Dialogue: 1,{st},{et},CalloutTop,,0,0,0,,{{\\fad(200,200)}}{top_t}")
    ass_lines.append(f"Dialogue: 1,{st},{et},CalloutBottom,,0,0,0,,{{\\fad(200,200)}}{bot_t}")

# C. Build Progressive Ghost Reveal Subtitles
for b_idx, burst in enumerate(BURSTS_60S):
    units = burst["units"]
    b_end = burst.get("end", units[-1][2])
    n = len(units)
    
    for i in range(n):
        u_text, u_start, u_end = units[i]
        
        parts = []
        for j in range(n):
            txt = units[j][0]
            if j < i:
                # Past words: pure white
                parts.append(r"{\c&HFFFFFF&}" + txt)
            elif j == i:
                # Active word: Neon green #66FF00 with 114% scale pop
                parts.append(r"{\c&H66FF00&\fscx114\fscy114}" + txt + r"{\r\c&HFFFFFF&}")
            else:
                # Upcoming words: 100% transparent ghost (alpha FF)
                parts.append(r"{\alpha&HFF&}" + txt)
                
        full_text = "".join(parts)
        st_str = format_ass_time(u_start)
        et_str = format_ass_time(u_end)
        ass_lines.append(f"Dialogue: 0,{st_str},{et_str},Default,,0,0,0,,{full_text}")
        
    # Settle duration: once whole burst is spoken, keep full white line until burst end
    last_u_end = units[-1][2]
    if b_end > last_u_end + 0.05:
        all_white = "".join(r"{\c&HFFFFFF&}" + u[0] for u in units)
        st_str = format_ass_time(last_u_end)
        et_str = format_ass_time(b_end)
        ass_lines.append(f"Dialogue: 0,{st_str},{et_str},Default,,0,0,0,,{all_white}")

ass_path = TMP_WORKSPACE / "subtitles" / "subtitles_60s_mali_burst.ass"
ass_path.parent.mkdir(parents=True, exist_ok=True)
ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
print(f"Generated 60s Mali burst ASS with {len(ass_lines)} lines: {ass_path}")

# Composite final video
raw_montage = TMP_SEGS / "pro_montage_15shots_raw.mp4"
voice_wav = TMP_WORKSPACE / "audio" / "voice_mix_flip_60s_sync.wav"
bgm_wav = PROJECT_ROOT / "02_Assets" / "Music" / "tiktok_upbeat_bgm.wav"
master_output = TMP_EXPORT / "Xiaomi_MIX_Flip_60s_Master.mp4"

ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
fonts_escaped = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")

print("Rendering Master Video with Curated Syllable Mali Subtitles & Upbeat BGM...")
final_cmd = (
    f'ffmpeg -y '
    f'-i "{raw_montage}" '
    f'-i "{voice_wav}" '
    f'-i "{bgm_wav}" '
    f'-filter_complex "'
    f'[0:v]subtitles=\'{ass_escaped}\':fontsdir=\'{fonts_escaped}\'[v];'
    f'[1:a]volume=1.0[v_voice];'
    f'[2:a]volume=0.14,aloop=loop=-1:size=2e+09[v_bgm];'
    f'[v_voice][v_bgm]amix=inputs=2:duration=first:dropout_transition=2[a]" '
    f'-map "[v]" -map "[a]" -t 60.0 '
    f'-c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p '
    f'-c:a aac -b:a 192k "{master_output}"'
)

subprocess.run(final_cmd, shell=True, check=True)
print(f"Master Video rendered: {master_output} ({master_output.stat().st_size / 1024 / 1024:.2f} MB)")

# Copy to artifact dir
dst_video = ART_DIR / "demo_xiaomi_mix_flip_cinematic_60s.mp4"
shutil.copy2(master_output, dst_video)
print(f"Copied to Artifact dir: {dst_video}")

# Extract verification keyframes
keyframe_points = [
    ("00:00:01.200", "01s_intro_xiaomi_mix_flip.jpg"),
    ("00:00:03.500", "03s_smartphone_jopup.jpg"),
    ("00:00:08.500", "08s_outer_display_401inch.jpg"),
    ("00:00:10.500", "10s_komchad_15k.jpg"),
    ("00:00:23.500", "23s_3000nits_bright.jpg"),
    ("00:00:32.800", "32s_leica_dual_optics.jpg"),
    ("00:00:41.200", "41s_snapdragon_8gen3.jpg"),
    ("00:00:44.200", "44s_3d_vapor_chamber.jpg")
]

for ts, name in keyframe_points:
    out_f = ART_DIR / name
    cmd_frame = f'ffmpeg -y -ss {ts} -i "{master_output}" -vframes 1 -q:v 2 "{out_f}"'
    subprocess.run(cmd_frame, shell=True, check=True)
    print(f"Extracted {name}")

print("ALL DONE SUCCESSFULLY!")

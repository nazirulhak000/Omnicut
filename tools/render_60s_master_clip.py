"""
OmniCut Pro Studio: 60-Second Full Gadget Review
Product: Xiaomi MIX Flip
- Clean 1080p Video + High-Res Official Photo Cuts
- Gemini Flash TTS (Fenrir, commercial_premium) - 58.12s
- Character-by-Character (ทีละตัว) Karaoke Bounce in Mali-Bold
- Zero-Jitter Ghost Layout
- Feature Spec Callouts (TECHMX style: Top White / Bottom Vibrant Orange, NO AI box)
- Uncropped with aesthetic Gaussian Blur Top/Bottom letterbox
- Lo-fi BGM (8% volume) with smooth outro fade to exactly 60.00 seconds!
"""

import os
import sys
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "gadget_demo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load 60s whisper transcript tokens
with open(OUTPUT_DIR / "whisper_60s.json", "r", encoding="utf-8") as f:
    whisper_data = json.load(f)

# Script phrases and character timing breakdown
# Mapped to exact timestamps from whisper_60s.json
SCRIPT_PHRASES_60S = [
    # 1. Intro & Hook (0.00 - 6.48)
    {
        "units": [
            ("นี่", 0.00, 0.40),
            ("คือ ", 0.40, 0.75),
            ("Xiaomi ", 0.75, 1.30),
            ("MIX ", 1.30, 1.60),
            ("Flip", 1.60, 1.95)
        ]
    },
    {
        "units": [
            ("สมาร์ท", 2.18, 2.70),
            ("โฟน", 2.70, 3.10),
            ("จอ", 3.10, 3.35),
            ("พับ", 3.35, 3.65),
            ("รุ่น", 3.65, 3.85),
            ("แรก ", 3.85, 4.10),
            ("จาก", 4.10, 4.30),
            ("ทาง ", 4.30, 4.45),
            ("Xiaomi", 4.45, 4.65)
        ]
    },
    {
        "units": [
            ("ที่", 4.65, 4.90),
            ("พัฒ", 4.90, 5.15),
            ("นา", 5.15, 5.40),
            ("ขึ้น ", 5.40, 5.70),
            ("อย่าง", 5.70, 6.05),
            ("ประ", 6.05, 6.25),
            ("ณีต", 6.25, 6.48)
        ]
    },
    # 2. Outer Display (6.74 - 17.64)
    {
        "units": [
            ("โดด", 6.74, 6.95),
            ("เด่น", 6.95, 7.20),
            ("ด้วย ", 7.20, 7.45),
            ("จอ", 7.45, 7.70),
            ("ด้าน", 7.70, 8.00),
            ("นอก ", 8.00, 8.35),
            ("ขนาด ", 8.35, 8.65),
            ("4.01 ", 8.65, 9.05),
            ("นิ้ว", 9.05, 9.34)
        ]
    },
    {
        "units": [
            ("คม", 9.54, 9.80),
            ("ชัด ", 9.80, 10.05),
            ("ระ", 10.05, 10.25),
            ("ดับ ", 10.25, 10.50),
            ("1.5K", 10.50, 11.20)
        ]
    },
    {
        "units": [
            ("พร้อม", 11.46, 11.80),
            ("รีเฟรช", 11.80, 12.30),
            ("เรท ", 12.30, 12.60),
            ("120Hz", 12.60, 13.74)
        ]
    },
    {
        "units": [
            ("ออก", 14.06, 14.35),
            ("แบบ", 14.35, 14.60),
            ("ให้ ", 14.60, 14.80),
            ("ใช้", 14.80, 15.00),
            ("งาน ", 15.00, 15.20),
            ("แอปพลิเคชัน ", 15.20, 15.80),
            ("ได้", 15.80, 16.05),
            ("ครบ", 16.05, 16.20),
            ("ถ้วน", 16.20, 16.36)
        ]
    },
    {
        "units": [
            ("โดย", 16.36, 16.60),
            ("ไม่", 16.60, 16.80),
            ("ต้อง", 16.80, 17.05),
            ("กาง", 17.05, 17.35),
            ("เครื่อง", 17.35, 17.64)
        ]
    },
    # 3. Inner Main Display (18.14 - 27.80)
    {
        "units": [
            ("เมื่อ", 18.14, 18.40),
            ("กาง", 18.40, 18.65),
            ("ออก ", 18.65, 18.90),
            ("จะ", 18.90, 19.10),
            ("พบ", 19.10, 19.35),
            ("กับ ", 19.35, 19.55),
            ("หน้า", 19.55, 19.80),
            ("จอ", 19.80, 20.00),
            ("หลัก ", 20.00, 20.25),
            ("OLED", 20.25, 20.70)
        ]
    },
    {
        "units": [
            ("ขนาด ", 21.06, 21.50),
            ("6.86 ", 21.50, 22.10),
            ("นิ้ว", 22.10, 22.62)
        ]
    },
    {
        "units": [
            ("สว่าง", 22.86, 23.25),
            ("สูง", 23.25, 23.55),
            ("สุด ", 23.55, 23.85),
            ("ถึง ", 23.85, 24.10),
            ("3,000 ", 24.10, 24.40),
            ("nits", 24.40, 24.68)
        ]
    },
    {
        "units": [
            ("มอบ", 24.92, 25.15),
            ("ภาพ", 25.15, 25.35),
            ("ที่", 25.35, 25.55),
            ("คม", 25.55, 25.75),
            ("ชัด ", 25.75, 25.95),
            ("และ", 25.95, 26.15),
            ("สบาย", 26.15, 26.45),
            ("ตา", 26.45, 26.72)
        ]
    },
    {
        "units": [
            ("ใน", 26.72, 26.95),
            ("ทุก", 26.95, 27.20),
            ("สภาพ", 27.20, 27.50),
            ("แสง", 27.50, 27.80)
        ]
    },
    # 4. Leica Camera Optics (28.28 - 38.44)
    {
        "units": [
            ("ด้าน", 28.28, 28.55),
            ("การ", 28.55, 28.80),
            ("ถ่าย", 28.80, 29.10),
            ("ภาพ", 29.10, 29.36)
        ]
    },
    {
        "units": [
            ("ผสาน", 29.36, 29.70),
            ("พลัง", 29.70, 30.05),
            ("กล้อง", 30.05, 30.35),
            ("คู่ ", 30.35, 30.55),
            ("ระดับ", 30.55, 30.82)
        ]
    },
    {
        "units": [
            ("โปร ", 30.82, 31.10),
            ("50 ", 31.10, 31.40),
            ("ล้าน", 31.40, 31.70),
            ("พิก", 31.70, 31.90),
            ("เซล", 31.90, 32.10)
        ]
    },
    {
        "units": [
            ("ที่", 32.10, 32.30),
            ("พัฒ", 32.30, 32.55),
            ("นา", 32.55, 32.75),
            ("ร่วม", 32.75, 33.00),
            ("กับ ", 33.00, 33.20),
            ("Leica", 33.20, 33.68)
        ]
    },
    {
        "units": [
            ("พร้อม", 33.90, 34.20),
            ("เลนส์ ", 34.20, 34.50),
            ("Summilux", 34.50, 35.08)
        ]
    },
    {
        "units": [
            ("ให้", 35.08, 35.30),
            ("โทน", 35.30, 35.55),
            ("ภาพ ", 35.55, 35.80),
            ("และ", 35.80, 36.05),
            ("มิติ", 36.05, 36.35),
            ("แสง", 36.35, 36.55),
            ("เงา", 36.55, 36.80)
        ]
    },
    {
        "units": [
            ("ที่", 36.80, 37.05),
            ("คม", 37.05, 37.30),
            ("ชัด ", 37.30, 37.55),
            ("เป็น", 37.55, 37.80),
            ("ธรรม", 37.80, 38.10),
            ("ชาติ", 38.10, 38.44)
        ]
    },
    # 5. Snapdragon 8 Gen 3 & Cooling (38.78 - 48.64)
    {
        "units": [
            ("ขับ", 38.78, 39.05),
            ("เคลื่อน", 39.05, 39.35),
            ("ด้วย ", 39.35, 39.55),
            ("ขุม", 39.55, 39.75),
            ("พลัง ", 39.75, 39.95),
            ("เรือ", 39.95, 40.18)
        ]
    },
    {
        "units": [
            ("ธง ", 40.18, 40.40),
            ("Snapdragon ", 40.40, 41.20),
            ("8 ", 41.20, 41.50),
            ("Gen ", 41.50, 41.80),
            ("3", 41.80, 42.44)
        ]
    },
    {
        "units": [
            ("เสริม", 42.44, 42.75),
            ("ด้วย ", 42.75, 42.95),
            ("ระบบ", 42.95, 43.30),
            ("ระบาย", 43.30, 43.70),
            ("ความ", 43.70, 43.95),
            ("ร้อน ", 43.95, 44.25),
            ("3D ", 44.25, 44.55),
            ("Dual-VC", 44.55, 45.24)
        ]
    },
    {
        "units": [
            ("มอบ", 45.24, 45.50),
            ("ความ", 45.50, 45.75),
            ("ลื่น", 45.75, 46.05),
            ("ไหล ", 46.05, 46.30),
            ("และ", 46.30, 46.54)
        ]
    },
    {
        "units": [
            ("ประสิทธิ", 46.54, 46.90),
            ("ภาพ ", 46.90, 47.15),
            ("สูง", 47.15, 47.30),
            ("สุด", 47.30, 47.48)
        ]
    },
    {
        "units": [
            ("ใน", 47.48, 47.70),
            ("ทุก", 47.70, 47.95),
            ("การ", 47.95, 48.20),
            ("ประ", 48.20, 48.40),
            ("มวล", 48.40, 48.55),
            ("ผล", 48.55, 48.64)
        ]
    },
    # 6. Battery & Fast Charge (48.64 - 58.12)
    {
        "units": [
            ("และ", 48.64, 48.85),
            ("อัด", 48.85, 49.05),
            ("แน่น", 49.05, 49.30),
            ("ด้วย ", 49.30, 49.50),
            ("แบตเตอรี่ ", 49.50, 50.00),
            ("ความ", 50.00, 50.20),
            ("จุ", 50.20, 50.42)
        ]
    },
    {
        "units": [
            ("ใหญ่ ", 50.42, 50.75),
            ("4,780 ", 50.75, 51.55),
            ("mAh", 51.55, 52.60)
        ]
    },
    {
        "units": [
            ("รอง", 52.82, 53.05),
            ("รับ ", 53.05, 53.25),
            ("ชาร์จ", 53.25, 53.60),
            ("ไว ", 53.60, 53.85),
            ("67W", 53.85, 54.50)
        ]
    },
    {
        "units": [
            ("ตอบ", 54.76, 55.05),
            ("โจทย์ ", 55.05, 55.25),
            ("การ", 55.25, 55.45),
            ("ใช้", 55.45, 55.65),
            ("งาน ", 55.65, 55.85),
            ("ระดับ", 55.85, 56.05),
            ("โปร", 56.05, 56.22)
        ]
    },
    {
        "units": [
            ("ได้", 56.22, 56.45),
            ("อย่าง", 56.45, 56.70),
            ("มั่น", 56.70, 56.95),
            ("ใจ ", 56.95, 57.15),
            ("ตลอด", 57.15, 57.45),
            ("ทั้ง", 57.45, 57.65),
            ("วัน", 57.65, 57.85),
            ("ครับ", 57.85, 58.12)
        ]
    }
]

# Feature Spec Callouts (TECHMX style: Top Title in White / Bottom Stat in Orange #FF6622)
# NO clunky AI template box! Floating cleanly over the video!
SPEC_CALLOUTS_60S = [
    {
        "start": 7.50,
        "end": 13.80,
        "top": "OUTER DISPLAY",
        "bottom": "4.01\" 1.5K 120Hz"
    },
    {
        "start": 19.50,
        "end": 26.50,
        "top": "INNER LTPO OLED",
        "bottom": "6.86\" 3,000 NITS"
    },
    {
        "start": 29.80,
        "end": 37.00,
        "top": "LEICA DUAL OPTICS",
        "bottom": "50MP SUMMILUX"
    },
    {
        "start": 40.00,
        "end": 46.50,
        "top": "SNAPDRAGON 8 GEN 3",
        "bottom": "3D DUAL-VC COOLING"
    },
    {
        "start": 49.50,
        "end": 56.00,
        "top": "SURGE BATTERY",
        "bottom": "4,780 mAh / 67W"
    }
]


def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def generate_60s_ass(output_ass_path, total_duration):
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # Subtitle font: Mali, size 86, White primary, Black outline 5.2, MarginV 360
        "Style: Default,Mali,86,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,0,2,20,20,360,1",
        # Feature Spec Callout Top: Prompt-Black, size 82, White, Outline 6.5, MarginV 1280 (above device)
        "Style: SpecTop,Prompt,82,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6.5,0,2,20,20,1280,1",
        # Feature Spec Callout Bottom: Prompt-Black, size 96, Vibrant Orange (#FF6622 in BGR = &H002266FF&), Outline 7.0, MarginV 530 (below device)
        "Style: SpecBottom,Prompt,96,&H002266FF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,7.0,0,2,20,20,530,1",
        # Source credit font: Prompt-Bold, size 26, White, MarginV 32 (bottom center)
        "Style: SourceCredit,Prompt,26,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2.5,0,2,20,20,32,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    # Source credits (No TECH MX badge!)
    source_credits = [
        {"start": 0.0, "end": 28.0, "text": "Source : Weibo Xiaomi"},
        {"start": 28.0, "end": total_duration, "text": "Source : mi.com Official"}
    ]
    for sc in source_credits:
        start_str = format_ass_time(sc["start"])
        end_str = format_ass_time(sc["end"])
        ass_lines.append(f"Dialogue: 1,{start_str},{end_str},SourceCredit,,0,0,0,,{sc['text']}")

    # Feature Spec Callouts (Floating organic text callouts, smooth fade in/out)
    for callout in SPEC_CALLOUTS_60S:
        c_start = format_ass_time(callout["start"])
        c_end = format_ass_time(callout["end"])
        top_text = r"{\fad(150,150)}" + callout["top"]
        bottom_text = r"{\fad(150,150)}" + callout["bottom"]
        ass_lines.append(f"Dialogue: 2,{c_start},{c_end},SpecTop,,0,0,0,,{top_text}")
        ass_lines.append(f"Dialogue: 2,{c_start},{c_end},SpecBottom,,0,0,0,,{bottom_text}")

    # Subtitles: Character-by-character bounce with Zero-Jitter Ghost Layout
    for phrase in SCRIPT_PHRASES_60S:
        units = phrase["units"]
        n = len(units)
        for i in range(n):
            u_text, u_start, u_end = units[i]
            parts = []
            for j in range(n):
                txt = units[j][0]
                if j < i:
                    parts.append(r"{\c&HFFFFFF&}" + txt)
                elif j == i:
                    parts.append(r"{\c&H66FF00&\fscx115\fscy115}" + txt + r"{\r\c&HFFFFFF&}")
                else:
                    parts.append(r"{\alpha&HFF&}" + txt)
            full_line = "".join(parts)
            ass_lines.append(f"Dialogue: 0,{format_ass_time(u_start)},{format_ass_time(u_end)},Default,,0,0,0,,{full_line}")

    Path(output_ass_path).write_text("\n".join(ass_lines), encoding="utf-8")
    print(f"Generated 60s ASS to {output_ass_path}")


def main():
    print("[1/3] Generating 60s Character-by-Character & Feature Spec Callout ASS...")
    total_dur = 60.00
    ass_path = OUTPUT_DIR / "subtitles_60s_review.ass"
    generate_60s_ass(ass_path, total_dur)

    print("[2/3] Preparing visual assets: Video + High-Res Photo Cuts...")
    product_dir = PROJECT_ROOT / ".tmp" / "gadget_products" / "Xiaomi_xiaomi_mix_flip"
    src_video = product_dir / "video_clean_1080p.mp4"
    img_leica = product_dir / "photos" / "micom_leica_optics.png"
    img_screen = product_dir / "photos" / "poster_feature_banner_1.jpg"
    img_hero = product_dir / "photos" / "poster_official_hero.png"

    wav_path = OUTPUT_DIR / "voice_mix_flip_60s_sync.wav"
    bgm_music = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_lofi_daily.wav"
    out_video = OUTPUT_DIR / "demo_xiaomi_mix_flip_60s_review.mp4"

    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
    fonts_dir = str((PROJECT_ROOT / "02_Assets" / "Fonts").resolve()).replace("\\", "/").replace(":", "\\:")

    # Multi-source timeline (60 seconds):
    # Track 0: src_video (0s to 18s) -> Xiaomi MIX Flip fold & outer screen
    # Track 3: img_screen (18s to 28s) -> Inner OLED Screen high-res
    # Track 4: img_leica (28s to 38s) -> Leica Dual Optics 50MP
    # Track 0: src_video (38s to 48s) -> Snapdragon 8 Gen 3 & Cooling
    # Track 5: img_hero (48s to 60s) -> Battery, 67W & Hero hold
    #
    # All visual clips are processed through uncropped 16:9 + Gaussian Blur Top/Bottom letterbox!
    print("[3/3] Compositing 60s video with FFmpeg...")
    ff_cmd = (
        f'ffmpeg -y '
        f'-stream_loop -1 -i "{src_video}" '           # Input 0: video
        f'-i "{wav_path}" '                            # Input 1: voice (58.12s)
        f'-stream_loop -1 -i "{bgm_music}" '           # Input 2: lo-fi bgm
        f'-loop 1 -t 10 -i "{img_screen}" '            # Input 3: screen photo (10s)
        f'-loop 1 -t 10 -i "{img_leica}" '             # Input 4: leica photo (10s)
        f'-loop 1 -t 12 -i "{img_hero}" '              # Input 5: hero photo (12s)
        f'-filter_complex "'
        # Segment 1: Video 0s-18s
        f'[0:v]trim=0:18,setpts=PTS-STARTPTS,split=2[v1_bg_raw][v1_fg_raw];'
        f'[v1_bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[v1_bg];'
        f'[v1_fg_raw]scale=1080:-2[v1_fg];'
        f'[v1_bg][v1_fg]overlay=0:(H-h)/2[seg1];'
        # Segment 2: Photo Screen 18s-28s (10s)
        f'[3:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[s2_bg];'
        f'[3:v]scale=1080:-2[s2_fg];'
        f'[s2_bg][s2_fg]overlay=0:(H-h)/2,trim=0:10,setpts=PTS-STARTPTS[seg2];'
        # Segment 3: Photo Leica 28s-38s (10s)
        f'[4:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[s3_bg];'
        f'[4:v]scale=1080:-2[s3_fg];'
        f'[s3_bg][s3_fg]overlay=0:(H-h)/2,trim=0:10,setpts=PTS-STARTPTS[seg3];'
        # Segment 4: Video 20s-30s (10s for Snapdragon)
        f'[0:v]trim=20:30,setpts=PTS-STARTPTS,split=2[v4_bg_raw][v4_fg_raw];'
        f'[v4_bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[v4_bg];'
        f'[v4_fg_raw]scale=1080:-2[v4_fg];'
        f'[v4_bg][v4_fg]overlay=0:(H-h)/2[seg4];'
        # Segment 5: Photo Hero 48s-60s (12s)
        f'[5:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[s5_bg];'
        f'[5:v]scale=1080:-2[s5_fg];'
        f'[s5_bg][s5_fg]overlay=0:(H-h)/2,trim=0:12,setpts=PTS-STARTPTS[seg5];'
        # Concatenate all 5 segments into full 60s timeline
        f'[seg1][seg2][seg3][seg4][seg5]concat=n=5:v=1:a=0[v_base];'
        # Burn in ASS subtitles (Character bounce + Spec Callouts)
        f'[v_base]ass=\'{ass_filter_path}\':fontsdir=\'{fonts_dir}\'[v];'
        # Audio Mix: Voice (1.0) + Lo-fi BGM (0.08) with fade out at 58.5s-60.0s
        f'[1:a]apad=pad_dur=2.0[voice_padded];'
        f'[2:a]volume=0.08,afade=t=out:st=58.0:d=2.0[bgm_faded];'
        f'[voice_padded][bgm_faded]amix=inputs=2:duration=first:dropout_transition=2[a]" '
        f'-map "[v]" -map "[a]" -t {total_dur:.2f} -c:v libx264 -preset fast -crf 20 -c:a aac -b:a 192k "{out_video}"'
    )

    res = subprocess.run(ff_cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-800:])
        return False

    print(f"Successfully rendered 60-second review clip: {out_video} ({out_video.stat().st_size} bytes)")

    # Extract 5 preview frames showcasing each feature callout & photo cuts
    art_dir = Path(r"C:\Users\Winon\.gemini\antigravity-ide\brain\17ebf3bb-f0a4-4947-8ff4-4269406b9ba0")
    callout_moments = [
        (9.5, "preview_60s_callout_outer_display.jpg"),
        (22.0, "preview_60s_callout_inner_oled.jpg"),
        (32.5, "preview_60s_callout_leica_optics.jpg"),
        (42.5, "preview_60s_callout_snapdragon.jpg"),
        (51.5, "preview_60s_callout_battery.jpg")
    ]
    for sec, fname in callout_moments:
        dst = art_dir / fname
        cmd = f'ffmpeg -y -ss {sec} -i "{out_video}" -vframes 1 -q:v 2 "{dst}"'
        subprocess.run(cmd, shell=True, check=True)
        print(f"  Extracted {fname} at {sec}s")

    return True


if __name__ == "__main__":
    main()

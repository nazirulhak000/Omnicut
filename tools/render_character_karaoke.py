"""
Render sample clip with Character-by-Character (ทีละตัว / per-syllable cluster)
Karaoke Bounce:
- Each character/syllable bounces into Neon Green (#00FF66) with scale pop
- Then settles into pure White (#FFFFFF) as the next character pops
- Exact Whisper millisecond synchronization
- NO "TECH MX" watermark badge (removed as requested)
- Mali-Bold font + black outline
- Uncropped 16:9 with blurred background
"""

import os
import sys
import json
import wave
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gemini_tts_engine import GeminiFlashTTSEngine
from scripts.hyperframes_engine import HyperFramesEngine

OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "gadget_demo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Character-by-character / syllable cluster timeline
CHARACTER_BURSTS = [
    {
        # Phrase 1: นี่คือ Xiaomi MIX Flip (0.26 - 2.32)
        "units": [
            ("นี่", 0.26, 0.65),
            ("คือ ", 0.65, 1.10),
            ("Xiao", 1.10, 1.45),
            ("mi ", 1.45, 1.78),
            ("MIX ", 1.78, 2.05),
            ("Flip", 2.05, 2.32)
        ]
    },
    {
        # Phrase 2: สมาร์ทโฟน จอพับรุ่นแรก จากทาง Xiaomi (2.78 - 5.22)
        "units": [
            ("ส", 2.78, 2.95),
            ("มาร์ท", 2.95, 3.18),
            ("โฟน ", 3.18, 3.45),
            ("จอ", 3.52, 3.75),
            ("พับ", 3.75, 3.98),
            ("รุ่น", 3.98, 4.15),
            ("แรก ", 4.15, 4.30),
            ("จาก", 4.30, 4.52),
            ("ทาง ", 4.52, 4.75),
            ("Xiao", 4.75, 4.98),
            ("mi", 4.98, 5.22)
        ]
    },
    {
        # Phrase 3: ที่พัฒนาขึ้น อย่างประณีต (5.46 - 7.22)
        "units": [
            ("ที่", 5.46, 5.72),
            ("พัฒ", 5.72, 5.95),
            ("นา", 5.95, 6.18),
            ("ขึ้น ", 6.18, 6.45),
            ("อย่าง", 6.45, 6.75),
            ("ประ", 6.75, 6.98),
            ("ณีต", 6.98, 7.22)
        ]
    },
    {
        # Phrase 4: โดดเด่นด้วย จอด้านนอก (7.64 - 8.86)
        "units": [
            ("โดด", 7.64, 7.82),
            ("เด่น", 7.82, 8.00),
            ("ด้วย ", 8.00, 8.16),
            ("จอ", 8.16, 8.35),
            ("ด้าน", 8.35, 8.60),
            ("นอก", 8.60, 8.86)
        ]
    },
    {
        # Phrase 5: ขนาด 4.01 นิ้ว (8.86 - 10.32)
        "units": [
            ("ข", 8.86, 9.00),
            ("นาด ", 9.00, 9.15),
            ("4", 9.15, 9.42),
            (".", 9.42, 9.62),
            ("0", 9.62, 9.82),
            ("1 ", 9.82, 10.05),
            ("นิ้ว", 10.05, 10.32)
        ]
    },
    {
        # Phrase 6: ออกแบบให้ ใช้งานแอปพลิเคชัน ได้ครบถ้วน (10.64 - 13.14)
        "units": [
            ("ออก", 10.64, 10.88),
            ("แบบ", 10.88, 11.10),
            ("ให้ ", 11.10, 11.28),
            ("ใช้", 11.28, 11.48),
            ("งาน", 11.48, 11.64),
            ("แอป", 11.64, 11.88),
            ("พลิ", 11.88, 12.10),
            ("เค", 12.10, 12.24),
            ("ชัน ", 12.24, 12.38),
            ("ได้", 12.38, 12.60),
            ("ครบ", 12.60, 12.85),
            ("ถ้วน", 12.85, 13.14)
        ]
    },
    {
        # Phrase 7: ผสานระบบ กล้องคู่ระดับโปร (13.42 - 15.14)
        "units": [
            ("ผ", 13.42, 13.62),
            ("สาน", 13.62, 13.92),
            ("ระ", 13.92, 14.10),
            ("บบ ", 14.10, 14.24),
            ("กล้อง", 14.24, 14.48),
            ("คู่", 14.48, 14.68),
            ("ระ", 14.68, 14.85),
            ("ดับ", 14.85, 15.02),
            ("โปร", 15.02, 15.14)
        ]
    },
    {
        # Phrase 8: ที่พัฒนาร่วมกับ Leica (15.14 - 16.78)
        "units": [
            ("ที่", 15.14, 15.38),
            ("พัฒ", 15.38, 15.60),
            ("นา", 15.60, 15.82),
            ("ร่วม", 15.82, 16.05),
            ("กับ ", 16.05, 16.24),
            ("Lei", 16.24, 16.50),
            ("ca", 16.50, 16.78)
        ]
    },
    {
        # Phrase 9: เพื่อมิติภาพ ที่คมชัด เป็นธรรมชาติ (17.10 - 19.82)
        "units": [
            ("เพื่อ", 17.10, 17.38),
            ("มิ", 17.38, 17.62),
            ("ติ", 17.62, 17.80),
            ("ภาพ ", 17.80, 17.95),
            ("ที่", 17.95, 18.20),
            ("คม", 18.20, 18.45),
            ("ชัด ", 18.45, 18.70),
            ("เป็น", 18.98, 19.22),
            ("ธรรม", 19.22, 19.48),
            ("ชา", 19.48, 19.65),
            ("ติ", 19.65, 19.82)
        ]
    },
    {
        # Phrase 10: และขับเคลื่อน ด้วยขุมพลัง Snapdragon (20.22 - 22.28)
        "units": [
            ("และ", 20.22, 20.46),
            ("ขับ", 20.46, 20.65),
            ("เคลื่อน ", 20.65, 20.82),
            ("ด้วย", 20.82, 21.05),
            ("ขุม", 21.05, 21.25),
            ("พ", 21.25, 21.38),
            ("ลัง ", 21.38, 21.52),
            ("Snap", 21.52, 21.85),
            ("dra", 21.85, 22.05),
            ("gon", 22.05, 22.28)
        ]
    },
    {
        # Phrase 11: 8 Gen 3 มอบประสบการณ์ ที่ราบรื่น (22.28 - 25.20)
        "units": [
            ("8 ", 22.28, 22.65),
            ("Gen ", 22.65, 23.00),
            ("3 ", 23.00, 23.50),
            ("มอบ", 23.50, 23.75),
            ("ประ", 23.75, 24.00),
            ("สบ", 24.00, 24.15),
            ("การณ์ ", 24.15, 24.30),
            ("ที่", 24.30, 24.55),
            ("ราบ", 24.55, 24.85),
            ("รื่น", 24.85, 25.20)
        ]
    },
    {
        # Phrase 12: และนิ่งสงบ ในทุกมิติ การใช้งานครับ (25.34 - 27.70)
        "units": [
            ("และ", 25.34, 25.50),
            ("นิ่ง", 25.50, 25.70),
            ("ส", 25.70, 25.82),
            ("งบ ", 25.82, 25.92),
            ("ใน", 25.92, 26.20),
            ("ทุก", 26.20, 26.50),
            ("มิ", 26.50, 26.70),
            ("ติ ", 26.70, 26.84),
            ("การ", 26.84, 27.05),
            ("ใช้", 27.05, 27.25),
            ("งาน", 27.25, 27.45),
            ("ครับ", 27.45, 27.70)
        ]
    }
]


def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def build_character_karaoke_ass(output_ass_path, total_duration, source_credits):
    """
    Builds ASS subtitle where:
    - NO "TECH MX" watermark badge
    - The whole phrase is pre-anchored on screen (zero horizontal jitter)
    - As the voice speaks, the active character/syllable BOUNCES into Neon Green ({\\c&H66FF00&\\fscx115\\fscy115})
    - Other characters remain pure White ({\\c&HFFFFFF&})
    - Exact character/syllable pacing (150-300ms) for high-energy modern TikTok/IG reel feel!
    """
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # Subtitle font: Mali, size 88, White primary, Black outline 5.2, subtle shadow
        "Style: Default,Mali,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,0,2,20,20,380,1",
        # Source credit font: Prompt-Bold, size 26, White, MarginV 32 (bottom center)
        "Style: SourceCredit,Prompt,26,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2.5,0,2,20,20,32,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    # Source credits (NO TECH MX badge!)
    for sc in source_credits:
        start_str = format_ass_time(sc["start"])
        end_str = format_ass_time(sc["end"])
        ass_lines.append(f"Dialogue: 1,{start_str},{end_str},SourceCredit,,0,0,0,,{sc['text']}")

    # Character-by-character bounce events
    for burst in CHARACTER_BURSTS:
        units = burst["units"]
        n = len(units)
        for i in range(n):
            u_text, u_start, u_end = units[i]
            
            # Construct line:
            # - Units 0..i-1: White
            # - Unit i: Neon Green + pop scale 115% (\c&H66FF00&\fscx115\fscy115)
            # - Units i+1..n-1: White (or invisible ghost)
            # Let's show: the active character pops in Green, upcoming characters are invisible (\alpha&HFF&)
            # so each letter appears and bounces into view one by one!
            parts = []
            for j in range(n):
                txt = units[j][0]
                if j < i:
                    parts.append(r"{\c&HFFFFFF&}" + txt)
                elif j == i:
                    parts.append(r"{\c&H66FF00&\fscx115\fscy115}" + txt + r"{\r\c&HFFFFFF&}")
                else:
                    parts.append(r"{\alpha&HFF&}" + txt)
            
            full_text = "".join(parts)
            ass_lines.append(f"Dialogue: 0,{format_ass_time(u_start)},{format_ass_time(u_end)},Default,,0,0,0,,{full_text}")

    Path(output_ass_path).write_text("\n".join(ass_lines), encoding="utf-8")
    print(f"Generated character-by-character ASS to {output_ass_path}")


def main(art_dir=None):
    if art_dir is None:
        art_dir = PROJECT_ROOT / ".tmp" / "artifacts"
    art_dir = Path(art_dir)
    art_dir.mkdir(parents=True, exist_ok=True)

    print("[1/4] Generating precision Character-by-Character ASS subtitles (NO TECH MX badge)...")

    wav_path = OUTPUT_DIR / "voice_mix_flip_gemini.wav"
    total_dur = 28.08
    ass_path = OUTPUT_DIR / "subtitles_character_bounce.ass"

    source_credits = [
        {"start": 0.0, "end": round(total_dur * 0.45, 2), "text": "Source : Weibo Xiaomi"},
        {"start": round(total_dur * 0.45, 2), "end": round(total_dur, 2), "text": "Source : mi.com Official"}
    ]

    build_character_karaoke_ass(
        output_ass_path=ass_path,
        total_duration=total_dur,
        source_credits=source_credits
    )

    print("[2/4] Compositing video with FFmpeg...")
    src_video = PROJECT_ROOT / ".tmp" / "gadget_products" / "Xiaomi_xiaomi_mix_flip" / "video_clean_1080p.mp4"
    bgm_music = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_lofi_daily.wav"
    spec_card_webm = OUTPUT_DIR / "hyperframes_spec_card.webm"
    out_video = OUTPUT_DIR / "demo_xiaomi_mix_flip_character_bounce.mp4"

    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
    fonts_dir = str((PROJECT_ROOT / "02_Assets" / "Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    card_start_time = 14.0

    ff_cmd = (
        f'ffmpeg -y -stream_loop -1 -i "{src_video}" -i "{wav_path}" -stream_loop -1 -i "{bgm_music}" '
        f'-itsoffset {card_start_time:.1f} -c:v libvpx-vp9 -i "{spec_card_webm}" '
        f'-filter_complex "'
        f'[0:v]split=2[bg_raw][fg_raw];'
        f'[bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[bg];'
        f'[fg_raw]scale=1080:-2[fg];'
        f'[bg][fg]overlay=0:(H-h)/2[base];'
        f'[base][3:v]overlay=0:0:eof_action=pass[with_card];'
        f'[with_card]ass=\'{ass_filter_path}\':fontsdir=\'{fonts_dir}\'[v];'
        f'[1:a]volume=1.0[voice];[2:a]volume=0.08[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]" '
        f'-map "[v]" -map "[a]" -t {total_dur:.2f} -c:v libx264 -preset fast -crf 20 -c:a aac -b:a 192k "{out_video}"'
    )

    res = subprocess.run(ff_cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-500:])
        return False

    print(f"[3/4] Successfully rendered: {out_video}")

    print("[4/4] Extracting character-level preview frames...")

    # Extract moments of character-by-character bounce:
    # 0.4s: "นี่" (green)
    # 0.9s: "นี่" (white), "คือ" (green)
    # 1.3s: "นี่คือ" (white), "Xiao" (green)
    # 1.6s: "นี่คือ Xiao" (white), "mi" (green)
    # 2.85s: "ส" (green)
    # 3.05s: "ส" (white), "มาร์ท" (green)
    # 3.3s: "สมาร์ท" (white), "โฟน" (green)
    moments = [
        (0.45, "preview_char_nee.jpg"),
        (0.90, "preview_char_kue.jpg"),
        (1.30, "preview_char_xiao.jpg"),
        (1.60, "preview_char_mi.jpg"),
        (2.85, "preview_char_sa.jpg"),
        (3.05, "preview_char_mart.jpg"),
        (3.30, "preview_char_phone.jpg"),
    ]

    for sec, fname in moments:
        dst = art_dir / fname
        cmd = f'ffmpeg -y -ss {sec} -i "{out_video}" -vframes 1 -q:v 2 "{dst}"'
        subprocess.run(cmd, shell=True, check=True)
        print(f"  Extracted {fname} at {sec}s")

    print("All done!")
    return True


if __name__ == "__main__":
    main()

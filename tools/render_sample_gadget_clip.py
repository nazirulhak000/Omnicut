"""Render a demonstration clip in TECHMX style using:

1. Gemini Flash TTS (Fenrir - ชายสตรอง คมเข้ม / โฆษณาพรีเมียม)
2. Exact Whisper-aligned timestamps for 100% audio-sync
3. Progressive Word-by-Word Karaoke (Mali-Bold font):
   - Current word: Neon Green (#00FF66) + pop scale (112%)
   - Previous words: Pure White (#FFFFFF)
   - Words appear one by one as spoken
4. Uncropped 1:1 original video with aesthetic blurred top/bottom background
5. HyperFrames Glassmorphism Tech Spec Card (Transparent WebM Overlay)
6. Dynamic Source Credit Overlay & Channel Badge
7. Ambient Lo-Fi BGM (8% volume)
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
from faster_whisper import WhisperModel
import scripts.config as cfg

OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "gadget_demo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VOICEOVER_TEXT = (
    "นี่คือ Xiaomi MIX Flip สมาร์ทโฟนจอพับรุ่นแรกจากทาง Xiaomi ที่พัฒนาขึ้นอย่างประณีต "
    "โดดเด่นด้วยจอด้านนอกขนาด 4.01 นิ้ว ออกแบบให้ใช้งานแอปพลิเคชันได้ครบถ้วน "
    "ผสานระบบกล้องคู่ระดับโปรที่พัฒนาร่วมกับ Leica เพื่อมิติภาพที่คมชัดเป็นธรรมชาติ "
    "และขับเคลื่อนด้วยขุมพลัง Snapdragon 8 Gen 3 มอบประสบการณ์ที่ราบรื่นและนิ่งสงบในทุกมิติการใช้งานครับ"
)


def get_wav_duration(wav_path):
    with wave.open(str(wav_path), "r") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / float(rate)


def format_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


# Exact millisecond-aligned bursts from Whisper transcription
PRECISE_BURSTS = [
    {
        "words": [
            ("นี่คือ", 0.26, 1.20),
            ("Xiaomi", 1.20, 1.78),
            ("MIX Flip", 1.78, 2.32)
        ]
    },
    {
        "words": [
            ("สมาร์ทโฟน", 2.78, 3.52),
            ("จอพับรุ่นแรก", 3.52, 4.28),
            ("จากทาง Xiaomi", 4.28, 5.22)
        ]
    },
    {
        "words": [
            ("ที่พัฒนาขึ้น", 5.46, 6.36),
            ("อย่างประณีต", 6.36, 7.22)
        ]
    },
    {
        "words": [
            ("โดดเด่นด้วย", 7.64, 8.16),
            ("จอด้านนอก", 8.16, 8.86),
            ("ขนาด 4.01 นิ้ว", 8.86, 10.32)
        ]
    },
    {
        "words": [
            ("ออกแบบให้", 10.64, 11.28),
            ("ใช้งานแอปพลิเคชัน", 11.28, 12.38),
            ("ได้ครบถ้วน", 12.38, 13.14)
        ]
    },
    {
        "words": [
            ("ผสานระบบ", 13.42, 14.24),
            ("กล้องคู่ระดับโปร", 14.24, 15.14)
        ]
    },
    {
        "words": [
            ("ที่พัฒนาร่วมกับ", 15.14, 16.24),
            ("Leica", 16.24, 16.78)
        ]
    },
    {
        "words": [
            ("เพื่อมิติภาพ", 17.10, 17.88),
            ("ที่คมชัด", 17.88, 18.70),
            ("เป็นธรรมชาติ", 18.70, 19.82)
        ]
    },
    {
        "words": [
            ("และขับเคลื่อน", 20.22, 20.82),
            ("ด้วยขุมพลัง", 20.82, 21.52),
            ("Snapdragon", 21.52, 22.28)
        ]
    },
    {
        "words": [
            ("8 Gen 3", 22.28, 23.50),
            ("มอบประสบการณ์", 23.50, 24.30),
            ("ที่ราบรื่น", 24.30, 25.20)
        ]
    },
    {
        "words": [
            ("และนิ่งสงบ", 25.34, 25.92),
            ("ในทุกมิติ", 25.92, 26.84),
            ("การใช้งานครับ", 26.84, 27.70)
        ]
    }
]


def generate_progressive_karaoke_ass(bursts, total_duration, output_ass_path, source_credits, channel_badge="TECH MX"):
    """
    Builds ASS subtitle with:
    - Font: Mali-Bold
    - Exact Whisper-aligned audio sync (no lagging or drifting)
    - Word-by-word reveal: active spoken word in Neon Green (&H66FF00&), previous words in White (&HFFFFFF&)
    - Zero-jitter invisible ghost placeholders ({\\alpha&HFF&}): prevents text from shifting/jumping horizontally
    - Safe zone: MarginV 380
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
        # Channel badge: Prompt-Bold, size 28, Neon Yellow, MarginV 55 (top right)
        "Style: ChannelBadge,Prompt,28,&H0000E6FF,&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,2.5,0,9,40,40,55,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    # Watermark / Badge
    if channel_badge:
        ass_lines.append(f"Dialogue: 1,0:00:00.00,{format_ass_time(total_duration)},ChannelBadge,,0,0,0,,{channel_badge}")

    # Source credits
    for sc in source_credits:
        start_str = format_ass_time(sc["start"])
        end_str = format_ass_time(sc["end"])
        ass_lines.append(f"Dialogue: 1,{start_str},{end_str},SourceCredit,,0,0,0,,{sc['text']}")

    # Progressive word-by-word karaoke lines with invisible ghost lock
    for burst in bursts:
        word_items = burst["words"]
        n = len(word_items)
        for i in range(n):
            w_text, w_start, w_end = word_items[i]
            
            parts = []
            for j in range(n):
                txt = word_items[j][0]
                if j < i:
                    parts.append(r"{\c&HFFFFFF&}" + txt)
                elif j == i:
                    parts.append(r"{\c&H66FF00&}" + txt + r"{\r\c&HFFFFFF&}")
                else:
                    parts.append(r"{\alpha&HFF&}" + txt)
            
            line_text = " ".join(parts)
            ass_lines.append(f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},Default,,0,0,0,,{line_text}")

    Path(output_ass_path).write_text("\n".join(ass_lines), encoding="utf-8")
    print(f"  -> Generated progressive zero-jitter karaoke ASS subtitles to {output_ass_path}")


def main():
    print("[1/5] Generating voiceover with Gemini Flash TTS (Fenrir - ชายสตรอง คมเข้ม / โฆษณาพรีเมียม)...")
    wav_path = OUTPUT_DIR / "voice_mix_flip_gemini.wav"
    
    if not wav_path.exists():
        GeminiFlashTTSEngine.generate_speech(
            text=VOICEOVER_TEXT,
            output_path=str(wav_path),
            voice_preset="gemini_fenrir_male_strong",
            ad_tone="commercial_premium",
            speed=1.0
        )
    
    total_dur = get_wav_duration(wav_path)
    print(f"  -> Audio Duration: {total_dur:.2f} seconds")

    print("[2/5] Preparing HyperFrames Glassmorphism Tech Spec Card (WebM Alpha)...")
    spec_card_webm = OUTPUT_DIR / "hyperframes_spec_card.webm"
    specs = {
        "processor": "Snapdragon 8 Gen 3",
        "camera": "50MP Leica Dual",
        "display": "4.01\" 1.5K AMOLED",
        "battery": "4,780 mAh (67W)"
    }
    card_dur = 6.0
    if not spec_card_webm.exists() or spec_card_webm.stat().st_size == 0:
        HyperFramesEngine.render_tech_spec_card(
            product_name="Xiaomi MIX Flip",
            specs=specs,
            output_webm_path=spec_card_webm,
            duration=card_dur,
            temp_dir=OUTPUT_DIR / "hf_card_build"
        )
    print("  -> Tech Spec Card ready.")

    print("[3/5] Applying precision Whisper timestamps & Generating Zero-Jitter Karaoke Subtitles with Mali-Bold...")
    ass_path = OUTPUT_DIR / "subtitles_mix_flip.ass"
    source_credits = [
        {"start": 0.0, "end": round(total_dur * 0.45, 2), "text": "Source : Weibo Xiaomi"},
        {"start": round(total_dur * 0.45, 2), "end": round(total_dur, 2), "text": "Source : mi.com Official"}
    ]

    generate_progressive_karaoke_ass(
        bursts=PRECISE_BURSTS,
        total_duration=total_dur,
        output_ass_path=ass_path,
        source_credits=source_credits,
        channel_badge="TECH MX"
    )

    print("[4/5] Compositing Hybrid Pipeline with FFmpeg (Uncropped + Blurred Top/Bottom + Mali Karaoke)...")
    src_video = PROJECT_ROOT / ".tmp" / "gadget_products" / "Xiaomi_xiaomi_mix_flip" / "video_clean_1080p.mp4"
    bgm_music = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_lofi_daily.wav"
    out_video = OUTPUT_DIR / "demo_xiaomi_mix_flip_techmx.mp4"

    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
    fonts_dir = str((PROJECT_ROOT / "02_Assets" / "Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    card_start_time = 14.0

    # FFmpeg filter:
    # 1. Base video split into bg and fg
    # 2. bg: scaled, cropped, gblurred
    # 3. fg: uncropped, scale 1080:-2, centered at (H-h)/2
    # 4. HyperFrames spec card overlay with -itsoffset
    # 5. ASS subtitles with Mali font from fontsdir
    # 6. Audio mix: Fenrir voice (1.0) + Lo-fi BGM (0.08)
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

    print(f"[5/5] Success! Rendered demo clip: {out_video} ({out_video.stat().st_size} bytes)")

    # Extract preview frames to verify
    print("Extracting preview frames...")
    subprocess.run(
        f'ffmpeg -y -ss 00:00:01.800 -i "{out_video}" -vframes 1 -q:v 2 "{OUTPUT_DIR}/preview_frame_karaoke1.jpg"',
        shell=True, capture_output=True
    )
    subprocess.run(
        f'ffmpeg -y -ss 00:00:04.200 -i "{out_video}" -vframes 1 -q:v 2 "{OUTPUT_DIR}/preview_frame_karaoke2.jpg"',
        shell=True, capture_output=True
    )
    subprocess.run(
        f'ffmpeg -y -ss 00:00:16.500 -i "{out_video}" -vframes 1 -q:v 2 "{OUTPUT_DIR}/preview_frame_speccard.jpg"',
        shell=True, capture_output=True
    )
    print("  -> Preview frames extracted.")
    return True


if __name__ == "__main__":
    main()

"""
Script to produce a TikTok Hands-on Review video in the exact style of @snap.it.review
Features:
- Authentic Hands-on video (Real person holding MIX Flip, petting 3D cat widget, opening apps)
- Top colorful hook badge sticker (Kanit-Bold)
- Soft blurred background matching original video colors
- Thai subtitles located cleanly in the bottom zone (underneath the video, never overlapping)
- Enthusiastic natural spoken Thai voiceover + upbeat BGM
- Bottom source credit
"""

import os
import sys
import asyncio
import subprocess
import json
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_VIDEO = PROJECT_ROOT / r".tmp\test_hands_on_pb.mp4.webm"
WORKSPACE = PROJECT_ROOT / r".tmp\Products\Xiaomi_MIX_Flip\02_Workspace"
EXPORT_DIR = PROJECT_ROOT / r".tmp\Products\Xiaomi_MIX_Flip\03_Export"
FONTS_DIR = PROJECT_ROOT / r"02_Assets\Fonts"
MUSIC_DIR = PROJECT_ROOT / r"02_Assets\Music"
BGM_PATH = MUSIC_DIR / "tiktok_upbeat_bgm.wav"

WORKSPACE.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Script Lines
SCRIPT = [
    {
        "text": "นี่คือ Xiaomi MIX Flip มือถือจอพับตัวตึงที่น่ารักที่สุดในตอนนี้ครับ",
        "pause_after": 0.35
    },
    {
        "text": "ดูจอนอก 4.01 นิ้วนี่สิ เลี้ยงน้องแมว 3D แตะเล่นได้ ขยับดุ๊กดิ๊กน่ารักมาก!",
        "pause_after": 0.35
    },
    {
        "text": "กางเครื่องออกมา หน้าจอด้านในเรียบเนียน รอยพับแทบมองไม่เห็นเลย",
        "pause_after": 0.35
    },
    {
        "text": "ปรับแต่งหน้าจอนอกได้เพียบ ทั้งวิดเจ็ตสัตว์เลี้ยง และธีมสุดเท่",
        "pause_after": 0.35
    },
    {
        "text": "ความเจ๋งคือ จอนอกเปิดแอปได้เต็มรูปแบบ ตอบแชท ไถฟีดได้ ไม่ต้องกางเครื่อง",
        "pause_after": 0.35
    },
    {
        "text": "กล้องคู่เลนส์ Leica 50 ล้านพิกเซล พับตั้งถ่ายเซลฟี่ด้วยจอนอกได้คมชัดสุดๆ",
        "pause_after": 0.35
    },
    {
        "text": "ชิปเรือธง Snapdragon 8 Gen 3 แบตเตอรี่ 4,780 mAh ตัวนี้คือตัวจบสายจอพับเลยครับ!",
        "pause_after": 0.50
    }
]

async def generate_tts_lines():
    import edge_tts
    temp_wavs = []
    cues = []
    current_time = 0.0

    print("--- [1/5] Generating Thai TTS Voiceover ---")
    for idx, item in enumerate(SCRIPT):
        text = item["text"]
        out_mp3 = WORKSPACE / f"tts_line_{idx}.mp3"
        out_wav = WORKSPACE / f"tts_line_{idx}.wav"

        comm = edge_tts.Communicate(text, voice="th-TH-NiwatNeural", rate="+12%")
        await comm.save(str(out_mp3))

        # Convert to standard wav 44100Hz stereo
        subprocess.run([
            "ffmpeg", "-i", str(out_mp3), "-ar", "44100", "-ac", "2", str(out_wav), "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Get duration
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(out_wav)
        ])
        dur = float(json.loads(probe)["format"]["duration"])

        start_t = current_time
        end_t = start_t + dur
        cues.append({
            "idx": idx,
            "text": text,
            "start": start_t,
            "end": end_t
        })
        current_time = end_t + item["pause_after"]
        temp_wavs.append((out_wav, item["pause_after"]))

    # Concat audio with silence
    total_audio_path = WORKSPACE / "narration_full.wav"
    concat_list = WORKSPACE / "audio_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for w_path, pause in temp_wavs:
            f.write(f"file '{w_path.name}'\n")
            if pause > 0:
                silence_wav = WORKSPACE / f"silence_{int(pause*1000)}.wav"
                if not silence_wav.exists():
                    subprocess.run([
                        "ffmpeg", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", "-t", str(pause), str(silence_wav), "-y"
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                f.write(f"file '{silence_wav.name}'\n")

    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(total_audio_path), "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print(f"Total narration duration: {current_time:.2f}s")
    return cues, current_time, total_audio_path

def create_top_badge():
    print("--- [2/5] Creating Top Hook Sticker Badge ---")
    img = Image.new("RGBA", (1080, 420), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path_bold = str(FONTS_DIR / "Kanit-Black.ttf")
    font_l1 = ImageFont.truetype(font_path_bold, 76)
    font_l2 = ImageFont.truetype(font_path_bold, 64)

    text_l1 = "รีวิวจริง Xiaomi MIX Flip"
    text_l2 = "จอพับตัวตึง จอนอกน่ารักสะใจ!"

    def draw_text_with_outline(draw, pos, text, font, fill_color, stroke_color, stroke_width, shadow_offset=(4, 6)):
        x, y = pos
        # Shadow
        if shadow_offset:
            sx, sy = shadow_offset
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    draw.text((x + sx + dx, y + sy + dy), text, font=font, fill=(0, 0, 0, 180))
        # Stroke
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx*dx + dy*dy <= stroke_width*stroke_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
        # Inner Fill
        draw.text((x, y), text, font=font, fill=fill_color)

    # Calculate center for Line 1
    bbox1 = font_l1.getbbox(text_l1)
    w1 = bbox1[2] - bbox1[0]
    x1 = (1080 - w1) // 2
    y1 = 120

    # Calculate center for Line 2
    bbox2 = font_l2.getbbox(text_l2)
    w2 = bbox2[2] - bbox2[0]
    x2 = (1080 - w2) // 2
    y2 = 230

    # Line 1: Vibrant Yellow #FFE600 with black outline 7px
    draw_text_with_outline(draw, (x1, y1), text_l1, font_l1, fill_color=(255, 230, 0, 255), stroke_color=(20, 20, 20, 255), stroke_width=8)

    # Line 2: Crisp White #FFFFFF with bold outline
    draw_text_with_outline(draw, (x2, y2), text_l2, font_l2, fill_color=(255, 255, 255, 255), stroke_color=(15, 15, 15, 255), stroke_width=7)

    badge_path = WORKSPACE / "top_hook_badge.png"
    img.save(str(badge_path))
    print(f"Top hook badge saved: {badge_path}")
    return badge_path

def generate_ass_subtitles(cues):
    print("--- [3/5] Generating Subtitles in Safe Bottom Zone ---")
    ass_path = WORKSPACE / "subtitles_bottom_zone.ass"
    font_name = "Mali-Bold"

    def format_ts(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        if cs >= 100:
            cs = 99
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    header = f"""[Script Info]
Title: MIX Flip Hands-on Bottom Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BottomClean,{font_name},76,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,1.2,2,60,60,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in cues:
        st = format_ts(c["start"])
        et = format_ts(c["end"])
        text = c["text"]
        events.append(f"Dialogue: 0,{st},{et},BottomClean,,0,0,0,,{text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    print(f"ASS Subtitle saved: {ass_path}")
    return ass_path

def render_master_video(badge_path, ass_path, narration_path, total_dur):
    print("--- [4/5] Rendering Master Video via FFmpeg ---")
    output_mp4 = EXPORT_DIR / "Xiaomi_MIX_Flip_SnapStyle_Master.mp4"

    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
    badge_filter_path = str(badge_path).replace("\\", "/").replace(":", "\\:")
    font_file_path = str(FONTS_DIR / "Kanit-Bold.ttf").replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg",
        "-i", str(INPUT_VIDEO),
        "-i", str(badge_path),
        "-i", str(narration_path),
        "-stream_loop", "-1", "-i", str(BGM_PATH),
        "-filter_complex",
        f"[0:v]split=2[v_bg_in][v_fg_in];"
        f"[v_bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.08[bg];"
        f"[v_fg_in]scale=1080:540[fg];"
        f"[bg][fg]overlay=0:690[v_composed];"
        f"[v_composed][1:v]overlay=0:50[v_badged];"
        f"[v_badged]ass='{ass_filter_path}',"
        f"drawtext=fontfile='{font_file_path}':text='เครดิต\\: Techdroider':fontsize=32:fontcolor=white@0.65:x=(w-text_w)/2:y=1860[v_out];"
        f"[2:a]volume=1.0[a_voice];"
        f"[3:a]volume=0.08[a_bgm];"
        f"[a_voice][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]",
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-t", f"{total_dur:.2f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_mp4),
        "-y"
    ]

    print("Running FFmpeg rendering command...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg Error:", res.stderr)
        raise RuntimeError("FFmpeg render failed")

    print(f"Master video generated successfully: {output_mp4}")
    return output_mp4

def extract_keyframes(output_mp4):
    print("--- [5/5] Extracting Verification Keyframes ---")
    timestamps = [5, 10, 22, 35, 46]
    for ts in timestamps:
        out_jpg = WORKSPACE / f"snap_verify_{ts}s.jpg"
        subprocess.run([
            "ffmpeg", "-ss", str(ts), "-i", str(output_mp4), "-vframes", "1", "-q:v", "2", str(out_jpg), "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Keyframe extracted at {ts}s: {out_jpg}")

async def main():
    cues, total_dur, narration_path = await generate_tts_lines()
    badge_path = create_top_badge()
    ass_path = generate_ass_subtitles(cues)
    output_mp4 = render_master_video(badge_path, ass_path, narration_path, total_dur)
    extract_keyframes(output_mp4)
    print("ALL DONE! SnapStyle Video Production Complete!")

if __name__ == "__main__":
    asyncio.run(main())

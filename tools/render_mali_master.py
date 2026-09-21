"""Render 60s Master Video with 100% MALI font subtitles.

Subtitle Style: Mali font, size 88, outline 5.2, Character Bounce with #00FF66 Neon Green.
"""

import json
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(r"d:\Winona\Programmer\Capcut")
TMP_OUTPUTS = PROJECT_ROOT / ".tmp" / "03_Outputs" / "Master_Clips_and_Previews"
TMP_SEGS = PROJECT_ROOT / ".tmp" / "04_Sandbox" / "pro_segs"
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"
ART_DIR = Path(r"C:\Users\Winon\.gemini\antigravity-ide\brain\17ebf3bb-f0a4-4947-8ff4-4269406b9ba0")

raw_montage = TMP_SEGS / "pro_montage_15shots_raw.mp4"
voice_wav = TMP_OUTPUTS / "voice_mix_flip_60s_sync.wav"
bgm_wav = PROJECT_ROOT / "02_Assets" / "Music" / "tiktok_upbeat_bgm.wav"
whisper_json = TMP_OUTPUTS / "whisper_60s.json"

assert raw_montage.exists(), f"Missing raw montage: {raw_montage}"
assert voice_wav.exists(), f"Missing voice: {voice_wav}"
assert bgm_wav.exists(), f"Missing BGM: {bgm_wav}"
assert whisper_json.exists(), f"Missing whisper: {whisper_json}"

with open(whisper_json, "r", encoding="utf-8") as f:
    whisper_data = json.load(f)

ass_file = TMP_OUTPUTS / "subtitles_60s_mali.ass"

ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Subtitle,Mali,88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5.2,0,2,54,54,380,1
Style: CalloutTop,Prompt,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,8,40,40,250,1
Style: CalloutBottom,Prompt-Black,94,&H002266FF,&H002266FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5.5,2.5,2,40,40,530,1
Style: Watermark,Prompt,24,&H70FFFFFF,&H70FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,2.0,0,2,20,20,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

events = []

# 1. Source Attribution Watermark
events.append("Dialogue: 0,0:00:00.00,0:01:00.00,Watermark,,0,0,0,,Source : mi.com Official")

# 2. Spec Callouts (Top White Prompt + Bottom Vibrant Orange Prompt-Black #FF6622)
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
    events.append(f"Dialogue: 1,{st},{et},CalloutTop,,0,0,0,,{{\\fad(200,200)}}{top_t}")
    events.append(f"Dialogue: 1,{st},{et},CalloutBottom,,0,0,0,,{{\\fad(200,200)}}{bot_t}")

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

# 3. Subtitles with Mali Character Bounce
for seg in whisper_data:
    words = seg.get("words", [])
    if not words:
        continue
    
    full_chars = "".join(w["word"] for w in words)
    if not full_chars.strip():
        continue
        
    char_timings = []
    for w in words:
        word_text = w["word"]
        w_start = w["start"]
        w_end = w["end"]
        n_chars = len(word_text)
        if n_chars == 0:
            continue
        c_dur = (w_end - w_start) / n_chars
        for i, ch in enumerate(word_text):
            c_st = w_start + i * c_dur
            c_et = c_st + c_dur
            char_timings.append((ch, c_st, c_et))
            
    for curr_idx, (curr_ch, c_st, c_et) in enumerate(char_timings):
        t_start_str = format_time(c_st)
        t_end_str = format_time(c_et)
        
        styled_parts = []
        for i, (ch, _, _) in enumerate(char_timings):
            if i < curr_idx:
                styled_parts.append(f"{{\\c&HFFFFFF&\\fscx100\\fscy100\\alpha&H00&}}{ch}")
            elif i == curr_idx:
                styled_parts.append(f"{{\\c&H00FF66&\\fscx114\\fscy114\\alpha&H00&}}{ch}")
            else:
                styled_parts.append(f"{{\\c&HFFFFFF&\\fscx100\\fscy100\\alpha&H85&}}{ch}")
                
        line_text = "".join(styled_parts)
        events.append(f"Dialogue: 2,{t_start_str},{t_end_str},Subtitle,,0,0,0,,{line_text}")

with open(ass_file, "w", encoding="utf-8") as f:
    f.write(ass_header + "\n".join(events) + "\n")

print(f"Mali ASS generated with {len(events)} events: {ass_file}")

# 4. Final Composite
master_output = TMP_OUTPUTS / "demo_xiaomi_mix_flip_cinematic_60s.mp4"
ass_escaped = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")
fonts_escaped = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")

print("Rendering Master Video with MALI font & Upbeat BGM...")
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

# 5. Copy to Artifact Directory
dst_video = ART_DIR / "demo_xiaomi_mix_flip_cinematic_60s.mp4"
shutil.copy2(master_output, dst_video)
print(f"Copied to Artifact dir: {dst_video}")

# 6. Extract keyframe at 8s and 44s
for ts, name in [("00:00:08.500", "08s_outer_display_mali.jpg"), ("00:00:44.000", "44s_3d_vc_mali.jpg")]:
    out_f = ART_DIR / name
    cmd_frame = f'ffmpeg -y -ss {ts} -i "{master_output}" -vframes 1 -q:v 2 "{out_f}"'
    subprocess.run(cmd_frame, shell=True, check=True)
    print(f"Extracted {name}")

print("ALL DONE!")

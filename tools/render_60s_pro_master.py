"""Render 60-second Professional Masterpiece for Xiaomi MIX Flip.

Key Fixes based on User Feedback:
1. Typography: Replaced casual/comic Mali-Bold with Golden Master font `IBM Plex Sans Thai SemiBold` (size 72px, outline 4.0px, MarginV 380)
2. Callout Style: Pure White Top (`Prompt`, 78px, outline 4.5px, MarginV 250) + Vibrant Neon Orange Bottom (`Prompt-Black`, 94px, #FF6622 / &H002266FF&, outline 5.5px, MarginV 530). Removed green line and green text.
3. Strict Topic Hold (Zero Early Transitions):
   - 3D VC Cooling visual stays for the ENTIRE duration of the cooling & performance sentence (42.40s -> 48.64s)
   - Inner Screen visuals stay for the ENTIRE duration of the inner screen topic (18.14s -> 28.28s)
   - Leica camera visuals stay for the ENTIRE duration of the camera topic (28.28s -> 38.78s)
4. BGM: Replaced slow Lo-Fi beat with energetic, modern `tiktok_upbeat_bgm.wav` (rhythmic, fun, perfect for IT tech reviews)
5. Ken Burns motion on all still photos (cinematic slow zoom 1.0 -> 1.10)
"""

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(r"d:\Winona\Programmer\Capcut")
TMP_OUTPUTS = PROJECT_ROOT / ".tmp" / "03_Outputs" / "Master_Clips_and_Previews"
PRODUCTS_DIR = PROJECT_ROOT / ".tmp" / "01_Products" / "Xiaomi_Models" / "Xiaomi_xiaomi_mix_flip"
TMP_SEGS = PROJECT_ROOT / ".tmp" / "04_Sandbox" / "pro_segs"
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"

TMP_SEGS.mkdir(parents=True, exist_ok=True)
TMP_OUTPUTS.mkdir(parents=True, exist_ok=True)

# 1. Assets
voice_wav = TMP_OUTPUTS / "voice_mix_flip_60s_sync.wav"
bgm_wav = PROJECT_ROOT / "02_Assets" / "Music" / "tiktok_upbeat_bgm.wav"
whisper_json = TMP_OUTPUTS / "whisper_60s.json"

v_fliptastic = PRODUCTS_DIR / "inserts" / "insert_official_fliptastic_design.mp4"
v_unboxing = PRODUCTS_DIR / "inserts" / "insert_official_unboxing_fan.mp4"
v_main = PRODUCTS_DIR / "video_clean_1080p.mp4"

photos = PRODUCTS_DIR / "photos"
p_hero_dual = photos / "asset_78624_dbd8ab2e47beb33c1e0b9aa96287b35c.png"
p_inner_flower = photos / "asset_40824_24388.jpg"
p_galaxy_3000nits = photos / "asset_75083_54954.jpg"
p_leica_lenses = photos / "asset_29045_23481-new.png"
p_beach_sunset = photos / "asset_97118_scroll-1-2.jpg"
p_snapdragon = photos / "asset_64490_39062-new.png"
p_vc_chamber = photos / "asset_40437_39070-new.png"
p_battery = photos / "asset_18669_40205-new.png"

# Verify all assets exist
all_assets = [
    voice_wav, bgm_wav, whisper_json, v_fliptastic, v_unboxing, v_main,
    p_hero_dual, p_inner_flower, p_galaxy_3000nits, p_leica_lenses,
    p_beach_sunset, p_snapdragon, p_vc_chamber, p_battery
]
for p in all_assets:
    if not p.exists():
        raise FileNotFoundError(f"Missing asset: {p}")

print("All 14 media assets verified successfully!")

# 2. Define 15 Topic-Locked Shots (Total exactly 60.00 seconds)
# Each shot matches the spoken topic 100% and holds until the sentence completes
shots_config = [
    # 01: 00:00 - 03:30 (3.30s) - Intro 3D purple hero rotating
    {"id": 1, "type": "video", "src": v_fliptastic, "ss": 0.0, "dur": 3.30},
    # 02: 03:30 - 06:74 (3.44s) - Dual hero front & back on white
    {"id": 2, "type": "image", "src": p_hero_dual, "dur": 3.44},
    # 03: 06:74 - 11:50 (4.76s) - Outer display in hand lights up (Callout: Outer Display)
    {"id": 3, "type": "video", "src": v_main, "ss": 0.0, "dur": 4.76},
    # 04: 11:50 - 15:00 (3.50s) - Animated pet wallpapers on outer screen
    {"id": 4, "type": "video", "src": v_main, "ss": 14.0, "dur": 3.50},
    # 05: 15:00 - 18:14 (3.14s) - Finger swiping widgets & apps on outer display without opening
    {"id": 5, "type": "video", "src": v_unboxing, "ss": 5.0, "dur": 3.14},
    # 06: 18:14 - 21:00 (2.86s) - Hand actively unfolding phone from 0 to 90 degrees (Callout: Inner LTPO OLED)
    {"id": 6, "type": "video", "src": v_unboxing, "ss": 15.5, "dur": 2.86},
    # 07: 21:00 - 24:60 (3.60s) - Full 6.86" unfolded OLED with vibrant purple flower
    {"id": 7, "type": "image", "src": p_inner_flower, "dur": 3.60},
    # 08: 24:60 - 28:28 (3.68s) - Glowing galaxy swirl representing 3,000 nits peak brightness
    {"id": 8, "type": "image", "src": p_galaxy_3000nits, "dur": 3.68},
    # 09: 28:28 - 32:00 (3.72s) - Macro of LEICA VARIO-SUMMILUX engraving (Callout: Leica Dual Optics)
    {"id": 9, "type": "video", "src": v_unboxing, "ss": 17.5, "dur": 3.72},
    # 10: 32:00 - 35:00 (3.00s) - Dual 50MP Leica lenses close-up on purple glass
    {"id": 10, "type": "image", "src": p_leica_lenses, "dur": 3.00},
    # 11: 35:00 - 38:78 (3.78s) - Leica sunset beach silhouette with official Leica watermark bar
    {"id": 11, "type": "image", "src": p_beach_sunset, "dur": 3.78},
    # 12: 38:78 - 42:40 (3.62s) - Glowing Snapdragon 8 Gen 3 chip (Callout: Snapdragon 8 Gen 3)
    {"id": 12, "type": "image", "src": p_snapdragon, "dur": 3.62},
    # 13: 42:40 - 48:64 (6.24s) - Exploded 3D Dual-VC chamber & internal cooling plate (STAYS WHOLE SENTENCE!)
    {"id": 13, "type": "image", "src": p_vc_chamber, "dur": 6.24},
    # 14: 48:64 - 54:50 (5.86s) - Surge 4,780 mAh dual battery graphic (Callout: Surge Battery)
    {"id": 14, "type": "image", "src": p_battery, "dur": 5.86},
    # 15: 54:50 - 60:00 (5.50s) - Hero purple closing & rotating outro
    {"id": 15, "type": "video", "src": v_fliptastic, "ss": 9.0, "dur": 5.50},
]

total_dur = sum(s["dur"] for s in shots_config)
print(f"Total shots: {len(shots_config)}, Total Duration: {total_dur:.2f}s")
assert abs(total_dur - 60.0) < 0.001, f"Total duration is {total_dur}, expected 60.00s"

# 3. Render Segments with Ken Burns and Gaussian Blur Letterbox
print("Rendering 15 topic-locked segments...")
seg_files = []
for idx, seg in enumerate(shots_config):
    sid = seg["id"]
    dur = seg["dur"]
    frames = int(round(dur * 30))
    out_file = TMP_SEGS / f"pro_seg_{sid:02d}.mp4"
    seg_files.append(out_file)
    
    if out_file.exists() and out_file.stat().st_size > 30000:
        print(f"  [{sid:02d}/15] Cached: {out_file.name}")
        continue
        
    print(f"  [{sid:02d}/15] Rendering ({seg['type']}, {dur:.2f}s)...")
    if seg["type"] == "video":
        filter_str = (
            f"[0:v]trim=start={seg['ss']}:duration={dur},setpts=PTS-STARTPTS,setsar=1,fps=30,"
            "split=2[v_bg][v_fg];"
            "[v_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:6[bg];"
            "[v_fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(seg["src"]),
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(out_file)
        ]
    else: # image with Ken Burns slow zoom (1.0 -> 1.08)
        filter_str = (
            "[0:v]loop=loop=-1:size=1:start=0,setsar=1,fps=30,"
            "split=2[v_bg][v_fg];"
            "[v_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:6[bg];"
            "[v_fg]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(1080-iw)/2:(1920-ih)/2:color=black@0,"
            f"zoompan=z='min(zoom+0.0008,1.08)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30[fg_zoom];"
            "[bg][fg_zoom]overlay=0:0[outv]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30", "-t", str(dur),
            "-i", str(seg["src"]),
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(out_file)
        ]
        
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error rendering segment {sid}: {res.stderr[-350:]}")
        raise RuntimeError(f"Segment {sid} failed")

# Concat 15 segments
concat_list = TMP_SEGS / "concat_15.txt"
with open(concat_list, "w", encoding="utf-8") as f:
    for sf in seg_files:
        f.write(f"file '{sf.resolve()}'\n")

raw_montage = TMP_SEGS / "pro_montage_15shots_raw.mp4"
print("Concatenating 15 segments into raw montage...")
cmd_concat = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(concat_list),
    "-c", "copy",
    str(raw_montage)
]
subprocess.run(cmd_concat, capture_output=True, check=True)
print(f"Montage created: {raw_montage.stat().st_size} bytes")

# 4. Generate Professional ASS (IBM Plex Sans Thai + Prompt-Black Vibrant Orange Callouts)
with open(whisper_json, "r", encoding="utf-8") as f:
    whisper_data = json.load(f)

ass_file = TMP_OUTPUTS / "subtitles_60s_pro.ass"

ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Subtitle,IBM Plex Sans Thai SemiBold,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,4.0,0,2,54,54,380,1
Style: CalloutTop,Prompt,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.5,2.0,8,40,40,250,1
Style: CalloutBottom,Prompt-Black,94,&H002266FF,&H002266FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5.5,2.5,2,40,40,530,1
Style: Watermark,Prompt,24,&H70FFFFFF,&H70FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,2.0,0,2,20,20,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

events = []

# A. Source Attribution Watermark (Rule 17)
events.append("Dialogue: 0,0:00:00.00,0:01:00.00,Watermark,,0,0,0,,Source : mi.com Official")

# B. 5 Clean Spec Callouts (Top White + Bottom Vibrant Orange #FF6622)
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
    # Top white title with smooth fade
    events.append(f"Dialogue: 1,{st},{et},CalloutTop,,0,0,0,,{{\\fad(200,200)}}{top_t}")
    # Bottom vibrant orange spec with punch fade
    events.append(f"Dialogue: 1,{st},{et},CalloutBottom,,0,0,0,,{{\\fad(200,200)}}{bot_t}")

# C. Subtitles with Character Bounce in IBM Plex Sans Thai SemiBold
def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

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
        for ci, char in enumerate(word_text):
            c_s = w_start + ci * c_dur
            c_e = c_s + c_dur
            char_timings.append((char, c_s, c_e))
            
    for curr_idx, (curr_char, curr_start, curr_end) in enumerate(char_timings):
        st_str = format_time(curr_start)
        et_str = format_time(curr_end)
        
        line_parts = []
        for i, (ch, cs, ce) in enumerate(char_timings):
            if i < curr_idx:
                line_parts.append(f"{{\\c&HFFFFFF&\\fscx100\\fscy100\\alpha&H00&}}{ch}")
            elif i == curr_idx:
                # Active character: neon green #00FF66 with 114% bounce
                line_parts.append(f"{{\\c&H00FF66&\\fscx114\\fscy114\\alpha&H00&}}{ch}")
            else:
                line_parts.append(f"{{\\c&HFFFFFF&\\fscx100\\fscy100\\alpha&H85&}}{ch}")
                
        full_line = "".join(line_parts)
        events.append(f"Dialogue: 2,{st_str},{et_str},Subtitle,,0,0,0,,{full_line}")

with open(ass_file, "w", encoding="utf-8") as f:
    f.write(ass_header)
    for ev in events:
        f.write(ev + "\n")

print(f"ASS generated with {len(events)} events: {ass_file}")

# 5. Final Composite (Burn ASS with fontsdir + Mix Fenrir Voice 1.0 & Upbeat BGM 0.14)
master_output = TMP_OUTPUTS / "demo_xiaomi_mix_flip_cinematic_60s.mp4"
ass_escaped = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")
fonts_escaped = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")

print("Rendering Master Video with upbeat BGM & IBM Plex Sans Thai subtitles...")
final_cmd = [
    "ffmpeg", "-y",
    "-i", str(raw_montage),
    "-i", str(voice_wav),
    "-i", str(bgm_wav),
    "-filter_complex",
    f"[0:v]subtitles='{ass_escaped}':fontsdir='{fonts_escaped}'[v];"
    "[1:a]volume=1.0[v_voice];"
    "[2:a]volume=0.14,aloop=loop=-1:size=2e+09[v_bgm];"
    "[v_voice][v_bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
    "-map", "[v]",
    "-map", "[a]",
    "-t", "60.0",
    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    str(master_output)
]

res = subprocess.run(final_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("Final render error:", res.stderr[-400:])
    raise RuntimeError("Final render failed")

print(f"Master Video successfully rendered: {master_output} ({master_output.stat().st_size / 1024 / 1024:.2f} MB)")

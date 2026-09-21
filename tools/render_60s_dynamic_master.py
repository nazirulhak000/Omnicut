"""Render 60-second Dynamic Masterpiece for Xiaomi MIX Flip.

Upgrades:
- 25-shot dynamic multi-cut montage (averaging ~2.4s per cut, eliminating static holds)
- 100% Visual-Audio alignment (inner unfolded screen at 18s-28s, outer widgets at 6s-18s, Leica macro & samples at 28s-38s, 3D VC teardown at 38s-48s, battery at 48s-54s, flex camcorder lifestyle at 54s-56s)
- Smooth Ken Burns motion (slow cinematic zoom 1.0 to 1.10) on every still photo
- Approved typography: Mali-Bold character bounce subtitles (#00FF66 neon green)
- Kinetic text callouts with spring-pop and expanding laser beam
- Gaussian blur top/bottom letterbox background for centered 100% uncropped footage
- Exactly 60.00 seconds runtime (1080x1920, 30 FPS)
"""

import json
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(r"d:\Winona\Programmer\Capcut")
TMP_OUTPUTS = PROJECT_ROOT / ".tmp" / "03_Outputs" / "Master_Clips_and_Previews"
PRODUCTS_DIR = PROJECT_ROOT / ".tmp" / "01_Products" / "Xiaomi_Models" / "Xiaomi_xiaomi_mix_flip"
TMP_SEGS = PROJECT_ROOT / ".tmp" / "04_Sandbox" / "dynamic_segs"
TMP_SEGS.mkdir(parents=True, exist_ok=True)
TMP_OUTPUTS.mkdir(parents=True, exist_ok=True)

# 1. Assets
voice_wav = TMP_OUTPUTS / "voice_mix_flip_60s_sync.wav"
bgm_mp3 = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_lofi_daily.wav"
whisper_json = TMP_OUTPUTS / "whisper_60s.json"

v_fliptastic = PRODUCTS_DIR / "inserts" / "insert_official_fliptastic_design.mp4"
v_unboxing = PRODUCTS_DIR / "inserts" / "insert_official_unboxing_fan.mp4"
v_main = PRODUCTS_DIR / "video_clean_1080p.mp4"

photos = PRODUCTS_DIR / "photos"
p_hero_dual = photos / "asset_78624_dbd8ab2e47beb33c1e0b9aa96287b35c.png"
p_pet_widgets = photos / "asset_30462_animate-bg-2.png"
p_hand_folded = photos / "asset_85174_s-1-new.jpg"
p_inner_flower = photos / "asset_40824_24388.jpg"
p_galaxy_3000nits = photos / "asset_75083_54954.jpg"
p_inner_ui = photos / "asset_63815_s-3-5.png"
p_leica_lenses = photos / "asset_29045_23481-new.png"
p_leica_optics = photos / "asset_12228_32787-new.png"
p_beach_sunset = photos / "asset_97118_scroll-1-2.jpg"
p_portrait_sample = photos / "asset_33795_scroll-1-1.png"
p_snapdragon = photos / "asset_64490_39062-new.png"
p_vc_chamber = photos / "asset_40437_39070-new.png"
p_hinge_angles = photos / "asset_84430_23191.jpg"
p_battery = photos / "asset_18669_40205-new.png"
p_puppy_flex = photos / "asset_40058_s-2-2.png"

# Verify all assets exist
all_assets = [
    voice_wav, bgm_mp3, whisper_json, v_fliptastic, v_unboxing, v_main,
    p_hero_dual, p_pet_widgets, p_hand_folded, p_inner_flower, p_galaxy_3000nits,
    p_inner_ui, p_leica_lenses, p_leica_optics, p_beach_sunset, p_portrait_sample,
    p_snapdragon, p_vc_chamber, p_hinge_angles, p_battery, p_puppy_flex
]
for p in all_assets:
    if not p.exists():
        raise FileNotFoundError(f"Missing asset: {p}")

print("All 21 media assets verified successfully!")

# 2. Define 25 Dynamic Shots (Total exactly 60.00 seconds)
# Pacing: 2.0s to 2.6s per cut. Outro 3.8s.
shots_config = [
    # 01: 00:00 - 02:40 (2.4s) - 3D purple hero rotating
    {"id": 1, "type": "video", "src": v_fliptastic, "ss": 0.0, "dur": 2.4},
    # 02: 02:40 - 04:80 (2.4s) - Dual hero front & back on white
    {"id": 2, "type": "image", "src": p_hero_dual, "dur": 2.4},
    # 03: 04:80 - 07:00 (2.2s) - Sleek hinge fold close-up
    {"id": 3, "type": "video", "src": v_fliptastic, "ss": 2.4, "dur": 2.2},
    # 04: 07:00 - 09:40 (2.4s) - Hand holding phone, outer display lights up (Callout: Outer Display)
    {"id": 4, "type": "video", "src": v_main, "ss": 0.0, "dur": 2.4},
    # 05: 09:40 - 11:80 (2.4s) - Animated pet wallpapers on outer screen
    {"id": 5, "type": "video", "src": v_main, "ss": 14.0, "dur": 2.4},
    # 06: 11:80 - 14:20 (2.4s) - Dynamic pet widgets row
    {"id": 6, "type": "image", "src": p_pet_widgets, "dur": 2.4},
    # 07: 14:20 - 16:20 (2.0s) - Finger swiping widgets & apps on outer screen
    {"id": 7, "type": "video", "src": v_unboxing, "ss": 5.0, "dur": 2.0},
    # 08: 16:20 - 18:20 (2.0s) - Hand holding compact folded phone
    {"id": 8, "type": "image", "src": p_hand_folded, "dur": 2.0},
    # 09: 18:20 - 20:60 (2.4s) - Hand unfolding phone from 0 to 90 degrees (Callout: Inner LTPO OLED)
    {"id": 9, "type": "video", "src": v_unboxing, "ss": 15.5, "dur": 2.4},
    # 10: 20:60 - 23:00 (2.4s) - Full 6.86" unfolded OLED with vibrant purple flower
    {"id": 10, "type": "image", "src": p_inner_flower, "dur": 2.4},
    # 11: 23:00 - 25:40 (2.4s) - Bright galaxy vortex (3,000 nits HDR representation)
    {"id": 11, "type": "image", "src": p_galaxy_3000nits, "dur": 2.4},
    # 12: 25:40 - 28:00 (2.6s) - Unfolded screen UI & smooth settings in hand
    {"id": 12, "type": "image", "src": p_inner_ui, "dur": 2.6},
    # 13: 28:00 - 30:20 (2.2s) - Macro of LEICA VARIO-SUMMILUX engraving (Callout: Leica Dual Optics)
    {"id": 13, "type": "video", "src": v_unboxing, "ss": 17.5, "dur": 2.2},
    # 14: 30:20 - 32:40 (2.2s) - Dual 50MP Leica lenses close-up
    {"id": 14, "type": "image", "src": p_leica_lenses, "dur": 2.2},
    # 15: 32:40 - 34:60 (2.2s) - Summilux optical ray tracing diagram
    {"id": 15, "type": "image", "src": p_leica_optics, "dur": 2.2},
    # 16: 34:60 - 36:60 (2.0s) - Leica sunset beach silhouette with official Leica watermark
    {"id": 16, "type": "image", "src": p_beach_sunset, "dur": 2.0},
    # 17: 36:60 - 38:80 (2.2s) - Leica sample photo portrait golden hour with official watermark
    {"id": 17, "type": "image", "src": p_portrait_sample, "dur": 2.2},
    # 18: 38:80 - 41:20 (2.4s) - Glowing Snapdragon 8 Gen 3 chip (Callout: Snapdragon 8 Gen 3)
    {"id": 18, "type": "image", "src": p_snapdragon, "dur": 2.4},
    # 19: 41:20 - 43:60 (2.4s) - Exploded 3D Dual-VC chamber & graphite sheet
    {"id": 19, "type": "image", "src": p_vc_chamber, "dur": 2.4},
    # 20: 43:60 - 46:00 (2.4s) - Ultra fluid 120Hz gesture navigation & speed
    {"id": 20, "type": "video", "src": v_main, "ss": 10.0, "dur": 2.4},
    # 21: 46:00 - 48:40 (2.4s) - Multi-angle 45°-120° hinge folding mechanism
    {"id": 21, "type": "image", "src": p_hinge_angles, "dur": 2.4},
    # 22: 48:40 - 51:00 (2.6s) - Surge 4,780 mAh dual battery graphic (Callout: Surge Battery)
    {"id": 22, "type": "image", "src": p_battery, "dur": 2.6},
    # 23: 51:00 - 53:60 (2.6s) - Flex tripod mode filming cute dog on floor
    {"id": 23, "type": "video", "src": v_main, "ss": 20.0, "dur": 2.6},
    # 24: 53:60 - 56:20 (2.6s) - Woman hugging puppy with flex MIX Flip taking photo
    {"id": 24, "type": "image", "src": p_puppy_flex, "dur": 2.6},
    # 25: 56:20 - 60:00 (3.8s) - Hero purple closing & rotating outro
    {"id": 25, "type": "video", "src": v_fliptastic, "ss": 10.0, "dur": 3.8},
]

total_dur = sum(s["dur"] for s in shots_config)
print(f"Total shots: {len(shots_config)}, Calculated Total Duration: {total_dur:.2f}s")
assert abs(total_dur - 60.0) < 0.001, f"Total duration is {total_dur}, expected 60.00s"

# 3. Render Segments
print("Rendering 25 montage segments with Gaussian blur letterbox & Ken Burns...")

seg_files = []
for idx, seg in enumerate(shots_config):
    sid = seg["id"]
    dur = seg["dur"]
    frames = int(round(dur * 30))
    out_file = TMP_SEGS / f"dyn_seg_{sid:02d}.mp4"
    seg_files.append(out_file)
    
    if out_file.exists() and out_file.stat().st_size > 30000:
        print(f"  [{sid:02d}/25] Cached: {out_file.name}")
        continue
        
    print(f"  [{sid:02d}/25] Rendering ({seg['type']}, {dur:.1f}s)...")
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
    else: # image with Ken Burns zoom-in
        filter_str = (
            "[0:v]loop=loop=-1:size=1:start=0,setsar=1,fps=30,"
            "split=2[v_bg][v_fg];"
            "[v_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:6[bg];"
            "[v_fg]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(1080-iw)/2:(1920-ih)/2:color=black@0,"
            f"zoompan=z='min(zoom+0.0013,1.10)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30[fg_zoom];"
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

# Concat 25 segments
concat_list = TMP_SEGS / "concat_25.txt"
with open(concat_list, "w", encoding="utf-8") as f:
    for sf in seg_files:
        f.write(f"file '{sf.resolve()}'\n")

raw_montage = TMP_SEGS / "dynamic_montage_25cuts_raw.mp4"
print("Concatenating 25 segments into raw montage...")
cmd_concat = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(concat_list),
    "-c", "copy",
    str(raw_montage)
]
subprocess.run(cmd_concat, capture_output=True, check=True)
print(f"Montage created: {raw_montage.stat().st_size} bytes")

# 4. Generate Kinetic Subtitles + Callouts ASS
with open(whisper_json, "r", encoding="utf-8") as f:
    whisper_data = json.load(f)

ass_file = TMP_OUTPUTS / "subtitles_60s_review.ass"

ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokeGhost,Mali-Bold,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,2,0,1,5.0,0,2,54,54,420,1
Style: KineticTitle,Prompt-Black,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,2.0,3.0,8,40,40,40,1
Style: KineticLaser,Arial,6,&H0066FF00,&H0066FF00,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,40,1
Style: KineticMetric,Prompt-Black,68,&H0066FF00,&H0066FF00,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,2.5,4.0,8,40,40,40,1
Style: Watermark,Prompt,22,&H50FFFFFF,&H50FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,1.5,0,2,20,20,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

events = []

# A. Source Attribution Watermark (Rule 17)
events.append("Dialogue: 0,0:00:00.00,0:01:00.00,Watermark,,0,0,0,,Source : mi.com Official")

# B. 5 Kinetic Text Callouts (Synchronized with speech timeline)
callouts_def = [
    {
        "start": "0:00:07.00", "end": "0:00:13.50",
        "title": "OUTER DISPLAY",
        "metric": "4.01\" 1.5K 120Hz"
    },
    {
        "start": "0:00:18.20", "end": "0:00:24.50",
        "title": "INNER LTPO OLED",
        "metric": "6.86\" 3,000 NITS"
    },
    {
        "start": "0:00:28.50", "end": "0:00:34.50",
        "title": "LEICA DUAL OPTICS",
        "metric": "50MP SUMMILUX"
    },
    {
        "start": "0:00:38.80", "end": "0:00:45.00",
        "title": "SNAPDRAGON 8 GEN 3",
        "metric": "3D DUAL-VC COOLING"
    },
    {
        "start": "0:00:48.50", "end": "0:00:54.50",
        "title": "SURGE BATTERY",
        "metric": "4,780 mAh / 67W"
    }
]

for c in callouts_def:
    st = c["start"]
    et = c["end"]
    title = c["title"]
    metric = c["metric"]
    events.append(
        f"Dialogue: 1,{st},{et},KineticTitle,,0,0,0,,{{\\fad(0,250)\\an8\\pos(540,280)\\fscx50\\fscy50\\alpha&HFF&\\t(0,200,\\fscx118\\fscy118\\alpha&H00&)\\t(200,380,\\fscx100\\fscy100)}}{title}"
    )
    events.append(
        f"Dialogue: 1,{st},{et},KineticLaser,,0,0,0,,{{\\fad(0,250)\\an5\\pos(540,350)\\fscx0\\fscy100\\alpha&HFF&\\t(60,260,\\fscx100\\fscy100\\alpha&H00&)\\p1}}m 0 -2 l 440 -2 l 440 2 l 0 2{{\\p0}}"
    )
    events.append(
        f"Dialogue: 1,{st},{et},KineticMetric,,0,0,0,,{{\\fad(0,250)\\an8\\pos(540,375)\\fscx30\\fscy30\\alpha&HFF&\\t(120,320,\\fscx122\\fscy122\\alpha&H00&)\\t(320,500,\\fscx100\\fscy100)}}{metric}"
    )

# C. Subtitles with Character Bounce
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
                line_parts.append(f"{{\\c&H00FF66&\\fscx118\\fscy118\\alpha&H00&}}{ch}")
            else:
                line_parts.append(f"{{\\c&HFFFFFF&\\fscx100\\fscy100\\alpha&H90&}}{ch}")
                
        full_line = "".join(line_parts)
        events.append(f"Dialogue: 2,{st_str},{et_str},KaraokeGhost,,0,0,0,,{full_line}")

with open(ass_file, "w", encoding="utf-8") as f:
    f.write(ass_header)
    for ev in events:
        f.write(ev + "\n")

print(f"ASS generated with {len(events)} events: {ass_file}")

# 5. Final Composite (Burn ASS + Mix Fenrir Voice 1.0 & BGM 0.12)
master_output = TMP_OUTPUTS / "demo_xiaomi_mix_flip_cinematic_60s.mp4"
ass_escaped = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")

print("Rendering Master Video with audio mix & subtitle burn-in...")
final_cmd = [
    "ffmpeg", "-y",
    "-i", str(raw_montage),
    "-i", str(voice_wav),
    "-i", str(bgm_mp3),
    "-filter_complex",
    f"[0:v]subtitles='{ass_escaped}'[v];"
    "[1:a]volume=1.0[v_voice];"
    "[2:a]volume=0.12,aloop=loop=-1:size=2e+09[v_bgm];"
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

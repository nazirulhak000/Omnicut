import json
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp" / "gadget_demo"
PRODUCTS_DIR = PROJECT_ROOT / ".tmp" / "gadget_products" / "Xiaomi_xiaomi_mix_flip"


def render_cinematic_master():
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Assets
    voice_wav = TMP_DIR / "voice_mix_flip_60s_sync.wav"
    bgm_mp3 = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_lofi_daily.wav"

    v_fliptastic = PRODUCTS_DIR / "inserts" / "insert_official_fliptastic_design.mp4"
    v_unboxing = PRODUCTS_DIR / "inserts" / "insert_official_unboxing_fan.mp4"
    v_main = PRODUCTS_DIR / "video_clean_1080p.mp4"

    p_widgets = PRODUCTS_DIR / "photos" / "widget_display_centered.jpg"
    p_flex = PRODUCTS_DIR / "photos" / "asset_22055_s-2.png"
    p_leica = PRODUCTS_DIR / "photos" / "micom_leica_optics.png"
    p_snapdragon = PRODUCTS_DIR / "photos" / "asset_64490_39062-new.png"
    p_battery = PRODUCTS_DIR / "photos" / "asset_18669_40205-new.png"

    # Verify all assets exist
    for p in [voice_wav, bgm_mp3, v_fliptastic, v_unboxing, v_main, p_widgets, p_flex, p_leica, p_snapdragon, p_battery]:
        if not p.exists():
            raise FileNotFoundError(f"Missing asset: {p}")

    print("All 10 media assets verified!")

    # 2. Build 10 Segments (each 6.0 seconds = total 60.0 seconds)
    segments_config = [
        {"type": "video", "src": v_fliptastic, "ss": 0.0, "dur": 6.0, "out": TMP_DIR / "seg1.mp4"},
        {"type": "video", "src": v_main, "ss": 0.0, "dur": 6.0, "out": TMP_DIR / "seg2.mp4"},
        {"type": "image", "src": p_widgets, "dur": 6.0, "out": TMP_DIR / "seg3.mp4"},
        {"type": "video", "src": v_unboxing, "ss": 2.0, "dur": 6.0, "out": TMP_DIR / "seg4.mp4"},
        {"type": "image", "src": p_flex, "dur": 6.0, "out": TMP_DIR / "seg5.mp4"},
        {"type": "image", "src": p_leica, "dur": 6.0, "out": TMP_DIR / "seg6.mp4"},
        {"type": "image", "src": p_snapdragon, "dur": 6.0, "out": TMP_DIR / "seg7.mp4"},
        {"type": "video", "src": v_main, "ss": 10.0, "dur": 6.0, "out": TMP_DIR / "seg8.mp4"},
        {"type": "image", "src": p_battery, "dur": 6.0, "out": TMP_DIR / "seg9.mp4"},
        {"type": "video", "src": v_fliptastic, "ss": 8.0, "dur": 6.0, "out": TMP_DIR / "seg10.mp4"},
    ]

    print("Rendering 10 montage segments with Gaussian blur letterbox...")

    for idx, seg in enumerate(segments_config):
        out_file = seg["out"]
        if out_file.exists() and out_file.stat().st_size > 50000:
            print(f"  Segment {idx+1} already cached: {out_file.name}")
            continue

        print(f"  Rendering Segment {idx+1}/10 ({seg['type']})...")
        if seg["type"] == "video":
            filter_str = (
                f"[0:v]trim=start={seg['ss']}:duration={seg['dur']},setpts=PTS-STARTPTS,setsar=1,fps=30,"
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
                "-t", str(seg["dur"]),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                str(out_file)
            ]
        else:  # image
            filter_str = (
                "[0:v]loop=loop=-1:size=1:start=0,setsar=1,fps=30,"
                "split=2[v_bg][v_fg];"
                "[v_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:6[bg];"
                "[v_fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-framerate", "30", "-t", str(seg["dur"]),
                "-i", str(seg["src"]),
                "-filter_complex", filter_str,
                "-map", "[outv]",
                "-t", str(seg["dur"]),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                str(out_file)
            ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error rendering segment {idx+1}: {res.stderr[-300:]}")
            raise RuntimeError(f"Segment {idx+1} failed")

    # Concat 10 segments
    concat_list = TMP_DIR / "concat_master.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in segments_config:
            f.write(f"file '{seg['out'].resolve()}'\n")

    raw_montage = TMP_DIR / "montage_60s_raw.mp4"
    print("Concatenating 10 segments into raw montage...")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_montage)
    ]
    subprocess.run(cmd_concat, capture_output=True, check=True)
    print(f"Montage created: {raw_montage.stat().st_size} bytes")

    # 3. Create Kinetic Subtitles + Callouts ASS
    whisper_file = TMP_DIR / "whisper_60s.json"
    if not whisper_file.exists():
        raise FileNotFoundError(f"Missing whisper file: {whisper_file}")

    with open(whisper_file, "r", encoding="utf-8") as f:
        whisper_data = json.load(f)

    # Styles
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

    # B. 5 Kinetic Text Callouts
    callouts_def = [
        {
            "start": "0:00:06.00", "end": "0:00:12.00",
            "title": "OUTER DISPLAY",
            "metric": "4.01\" 1.5K 120Hz"
        },
        {
            "start": "0:00:18.00", "end": "0:00:24.00",
            "title": "INNER LTPO OLED",
            "metric": "6.86\" 3,000 NITS"
        },
        {
            "start": "0:00:30.00", "end": "0:00:36.00",
            "title": "LEICA DUAL OPTICS",
            "metric": "50MP SUMMILUX"
        },
        {
            "start": "0:00:36.50", "end": "0:00:43.00",
            "title": "SNAPDRAGON 8 GEN 3",
            "metric": "3D DUAL-VC COOLING"
        },
        {
            "start": "0:00:48.00", "end": "0:00:54.00",
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
                    line_parts.append(f"{{\\alpha&HFF&}}{ch}")
            event_text = "".join(line_parts)
            events.append(f"Dialogue: 0,{st_str},{et_str},KaraokeGhost,,0,0,0,,{event_text}")

    final_ass_path = TMP_DIR / "master_cinematic_subtitles.ass"
    with open(final_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))

    print(f"Master ASS subtitles generated: {len(events)} events")

    # 4. Final Composite: Video + Audio + Subtitles + BGM
    master_output = TMP_DIR / "demo_xiaomi_mix_flip_cinematic_60s.mp4"
    print("Rendering Final 60-Second Masterpiece Video with Original Beloved Typography...")

    ass_filter_path = ".tmp/gadget_demo/subtitles_60s_review.ass"
    filter_complex_str = (
        f"[0:v]ass='{ass_filter_path}':fontsdir='02_Assets/Fonts'[v];"
        "[1:a]apad=pad_dur=2.5,volume=1.0[vocal];"
        "[2:a]volume=0.10,atrim=0:60.0,afade=t=out:st=57.5:d=2.5[bgm];"
        "[vocal][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )

    cmd_final = [
        "ffmpeg", "-y",
        "-i", str(raw_montage),
        "-i", str(voice_wav),
        "-i", str(bgm_mp3),
        "-filter_complex", filter_complex_str,
        "-map", "[v]",
        "-map", "[a]",
        "-t", "60.00",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(master_output)
    ]

    res = subprocess.run(cmd_final, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Render error: {res.stderr[-500:]}")
        raise RuntimeError("Final master render failed")

    print("\n==========================================")
    print("MASTERPIECE RENDERED SUCCESSFULLY!")
    print(f"Path: {master_output.resolve()}")
    print(f"Size: {master_output.stat().st_size} bytes")
    print("==========================================")


if __name__ == '__main__':
    render_cinematic_master()

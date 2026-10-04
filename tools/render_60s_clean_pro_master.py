"""Render 60-Second Clean Pro Master for Xiaomi MIX Flip.

User-directed refinements:
1. Pacing: 12 calm, smooth shots (each 3.3s to 6.0s), zero rushed cuts under 3s.
2. Aspect ratio: 100% uncropped original aspect ratio with smooth Gaussian blur background.
3. Typography: Top clunky callout font removed 100% for an ultra-clean, commercial YouTube-pro aesthetic.
4. Audio: SFX stem removed 100% (pure Voice 1.0 + BGM Rock Angel 0.065).
5. Subtitles: Mali-Bold 88px syllable clustering + progressive ghost reveal in neon green.
"""

import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCT_DIR = PROJECT_ROOT / ".tmp" / "Products" / "Xiaomi_MIX_Flip"
RAW_DIR = PRODUCT_DIR / "01_Raw"
WORKSPACE_DIR = PRODUCT_DIR / "02_Workspace"
EXPORT_DIR = PRODUCT_DIR / "03_Export"
TMP_SEGS = WORKSPACE_DIR / "temp_cuts"
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"
ART_DIR = PROJECT_ROOT / ".tmp" / "artifacts"


def render_clean_pro_master():
    TMP_SEGS.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Assets
    voice_wav = WORKSPACE_DIR / "audio" / "voice_mix_flip_60s_sync.wav"
    bgm_mp3 = PROJECT_ROOT / "02_Assets" / "Music" / "bgm_joakim_karud_rock_angel.mp3"

    v_fliptastic = RAW_DIR / "videos" / "insert_official_fliptastic_design.mp4"
    v_unboxing = RAW_DIR / "videos" / "insert_official_unboxing_fan.mp4"
    v_main = RAW_DIR / "videos" / "video_clean_1080p.mp4"

    photos = RAW_DIR / "photos"
    p_hero_dual = photos / "asset_78624_dbd8ab2e47beb33c1e0b9aa96287b35c.png"
    p_inner_flower = photos / "asset_40824_24388.jpg"
    p_leica_lenses = photos / "asset_29045_23481-new.png"
    p_beach_sunset = photos / "asset_97118_scroll-1-2.jpg"
    p_snapdragon = photos / "asset_64490_39062-new.png"
    p_vapor_chamber = photos / "asset_40437_39070-new.png"
    p_battery_4780 = photos / "asset_18669_40205-new.png"

    # 2. Define 12 Calm, Professional Shots (Exact Total: 60.00s)
    shots = [
        {"id": 1, "type": "video", "src": v_fliptastic, "ss": 0.0, "dur": 3.34},
        {"id": 2, "type": "image", "src": p_hero_dual, "dur": 3.40},
        {"id": 3, "type": "video", "src": v_main, "ss": 0.0, "dur": 5.70},
        {"id": 4, "type": "video", "src": v_main, "ss": 13.5, "dur": 5.70},
        {"id": 5, "type": "video", "src": v_unboxing, "ss": 15.0, "dur": 5.06},
        {"id": 6, "type": "image", "src": p_inner_flower, "dur": 5.08},
        {"id": 7, "type": "image", "src": p_leica_lenses, "dur": 5.22},
        {"id": 8, "type": "image", "src": p_beach_sunset, "dur": 5.28},
        {"id": 9, "type": "image", "src": p_snapdragon, "dur": 4.92},
        {"id": 10, "type": "image", "src": p_vapor_chamber, "dur": 4.94},
        {"id": 11, "type": "image", "src": p_battery_4780, "dur": 5.36},
        {"id": 12, "type": "video", "src": v_unboxing, "ss": 18.0, "dur": 6.00},
    ]

    total_dur = sum(s["dur"] for s in shots)
    print(f"Configured {len(shots)} smooth shots. Total duration: {total_dur:.2f}s")
    assert abs(total_dur - 60.0) < 0.01, f"Duration is {total_dur}, must be 60.00s"

    # 3. Render Segments
    seg_files = []
    print("Rendering 12 smooth segments with standard blur background (uncropped original)...")

    for seg in shots:
        sid = seg["id"]
        dur = seg["dur"]
        out_file = TMP_SEGS / f"smooth_seg_{sid:02d}.mp4"
        seg_files.append(out_file)

        print(f"  [{sid:02d}/12] Rendering {seg['type']} (dur={dur:.2f}s)...")
        filter_str = (
            "[0:v]setsar=1,fps=30,"
            "split=2[v_bg][v_fg];"
            "[v_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:4[bg];"
            "[v_fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )

        if seg["type"] == "video":
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(seg.get("ss", 0.0)),
                "-i", str(seg["src"]),
                "-filter_complex", filter_str,
                "-map", "[outv]",
                "-t", str(dur),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
                str(out_file)
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-framerate", "30", "-t", str(dur),
                "-i", str(seg["src"]),
                "-filter_complex", filter_str,
                "-map", "[outv]",
                "-t", str(dur),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
                str(out_file)
            ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error on seg {sid}:", res.stderr[-300:])
            raise RuntimeError(f"Segment {sid} failed")

    # 4. Concat 12 Segments
    concat_list = TMP_SEGS / "concat_12_smooth.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in seg_files:
            f.write(f"file '{sf.resolve()}'\n")

    raw_montage = TMP_SEGS / "smooth_montage_12cuts_raw.mp4"
    print("Concatenating into smooth montage...")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(raw_montage)],
        capture_output=True, check=True
    )
    print(f"Raw montage created: {raw_montage.stat().st_size / 1024 / 1024:.2f} MB")

    # 5. Generate Clean ASS
    from build_60s_mali_burst_ass import BURSTS_60S, format_ass_time

    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Mali,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.2,0,2,20,20,380,1",
        "Style: Watermark,Prompt,24,&H70FFFFFF,&H70FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,2.0,0,2,20,20,36,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    ass_lines.append("Dialogue: 0,0:00:00.00,0:01:00.00,Watermark,,0,0,0,,Source : mi.com Official")

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
                    parts.append(r"{\c&HFFFFFF&}" + txt)
                elif j == i:
                    parts.append(r"{\c&H66FF00&\fscx114\fscy114}" + txt + r"{\r\c&HFFFFFF&}")
                else:
                    parts.append(r"{\alpha&HFF&}" + txt)

            full_text = "".join(parts)
            st_str = format_ass_time(u_start)
            et_str = format_ass_time(u_end)
            ass_lines.append(f"Dialogue: 0,{st_str},{et_str},Default,,0,0,0,,{full_text}")

        last_u_end = units[-1][2]
        if b_end > last_u_end + 0.05:
            all_white = "".join(r"{\c&HFFFFFF&}" + u[0] for u in units)
            st_str = format_ass_time(last_u_end)
            et_str = format_ass_time(b_end)
            ass_lines.append(f"Dialogue: 0,{st_str},{et_str},Default,,0,0,0,,{all_white}")

    ass_path = WORKSPACE_DIR / "subtitles" / "subtitles_60s_clean_pro.ass"
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
    print(f"Generated clean ASS: {ass_path}")

    # 6. Composite Master Video
    master_output = EXPORT_DIR / "Xiaomi_MIX_Flip_60s_Master.mp4"
    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    fonts_escaped = str(FONTS_DIR.resolve()).replace("\\", "/").replace(":", "\\:")

    print("Rendering Final Composite...")
    final_cmd = (
        f'ffmpeg -y '
        f'-i "{raw_montage}" '
        f'-i "{voice_wav}" '
        f'-i "{bgm_mp3}" '
        f'-filter_complex "'
        f'[0:v]subtitles=\'{ass_escaped}\':fontsdir=\'{fonts_escaped}\'[v];'
        f'[1:a]volume=1.0[v_voice];'
        f'[2:a]volume=0.065,aloop=loop=-1:size=2e+09[v_bgm];'
        f'[v_voice][v_bgm]amix=inputs=2:duration=first:dropout_transition=2[a]" '
        f'-map "[v]" -map "[a]" -t 60.0 '
        f'-c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p '
        f'-c:a aac -b:a 192k "{master_output}"'
    )

    subprocess.run(final_cmd, shell=True, check=True)
    print(f"Master Video rendered: {master_output} ({master_output.stat().st_size / 1024 / 1024:.2f} MB)")

    dst_video = ART_DIR / "Xiaomi_MIX_Flip_60s_Master.mp4"
    shutil.copy2(master_output, dst_video)
    print(f"Copied to Artifact: {dst_video}")

    keyframe_points = [
        ("00:00:02.000", "02s_intro_fliptastic.jpg"),
        ("00:00:05.000", "05s_dual_hero_beauty.jpg"),
        ("00:00:10.000", "10s_clean_outer_display_otter.jpg"),
        ("00:00:21.000", "21s_smooth_unfolding_inner.jpg"),
        ("00:00:31.000", "31s_leica_optics_macro.jpg"),
        ("00:00:41.000", "41s_snapdragon_chip.jpg"),
        ("00:00:46.000", "46s_vapor_chamber_vc.jpg"),
        ("00:00:51.000", "51s_battery_4780mah.jpg"),
        ("00:00:57.000", "57s_flex_multi_angle_phones.jpg"),
    ]

    for ts, name in keyframe_points:
        out_f = ART_DIR / name
        cmd_frame = f'ffmpeg -y -ss {ts} -i "{master_output}" -vframes 1 -q:v 2 "{out_f}"'
        subprocess.run(cmd_frame, shell=True, check=True)
        print(f"Extracted {name}")

    print("ALL FINISHED WITH CLEAN PRO SPEC!")


if __name__ == '__main__':
    render_clean_pro_master()

import subprocess
from pathlib import Path

product_dir = Path(".tmp/gadget_products/Xiaomi_xiaomi_mix_flip")
src_video = product_dir / "video_clean_1080p.mp4"
img_screen = product_dir / "photos/poster_feature_banner_1.jpg"
img_leica = product_dir / "photos/micom_leica_optics.png"
img_hero = product_dir / "photos/poster_official_hero.png"
wav_path = Path(".tmp/gadget_demo/voice_mix_flip_60s_sync.wav")
bgm_music = Path("02_Assets/Music/bgm_lofi_daily.wav")
ass_path = Path(".tmp/gadget_demo/subtitles_60s_review.ass")
out_video = Path(".tmp/gadget_demo/demo_xiaomi_mix_flip_60s_review.mp4")

ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
fonts_dir = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")

# Let's test the concat filter with setsar=1,fps=30 on each segment
cmd = (
    f'ffmpeg -y '
    f'-stream_loop -1 -i "{src_video}" '
    f'-i "{wav_path}" '
    f'-stream_loop -1 -i "{bgm_music}" '
    f'-loop 1 -t 10 -framerate 30 -i "{img_screen}" '
    f'-loop 1 -t 10 -framerate 30 -i "{img_leica}" '
    f'-loop 1 -t 12 -framerate 30 -i "{img_hero}" '
    f'-filter_complex "'
    # Seg 1: Video 0s-18s (18s)
    f'[0:v]trim=0:18,setpts=PTS-STARTPTS,fps=30,setsar=1,split=2[v1_bg_raw][v1_fg_raw];'
    f'[v1_bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[v1_bg];'
    f'[v1_fg_raw]scale=1080:-2[v1_fg];'
    f'[v1_bg][v1_fg]overlay=0:(H-h)/2,setsar=1,fps=30[seg1];'
    # Seg 2: Screen Photo 10s
    f'[3:v]fps=30,setsar=1,split=2[v2_bg_raw][v2_fg_raw];'
    f'[v2_bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[v2_bg];'
    f'[v2_fg_raw]scale=1080:-2[v2_fg];'
    f'[v2_bg][v2_fg]overlay=0:(H-h)/2,trim=0:10,setpts=PTS-STARTPTS,setsar=1,fps=30[seg2];'
    # Seg 3: Leica Photo 10s
    f'[4:v]fps=30,setsar=1,split=2[v3_bg_raw][v3_fg_raw];'
    f'[v3_bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[v3_bg];'
    f'[v3_fg_raw]scale=1080:-2[v3_fg];'
    f'[v3_bg][v3_fg]overlay=0:(H-h)/2,trim=0:10,setpts=PTS-STARTPTS,setsar=1,fps=30[seg3];'
    # Seg 4: Video 20s-30s (10s)
    f'[0:v]trim=20:30,setpts=PTS-STARTPTS,fps=30,setsar=1,split=2[v4_bg_raw][v4_fg_raw];'
    f'[v4_bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[v4_bg];'
    f'[v4_fg_raw]scale=1080:-2[v4_fg];'
    f'[v4_bg][v4_fg]overlay=0:(H-h)/2,setsar=1,fps=30[seg4];'
    # Seg 5: Hero Photo 12s
    f'[5:v]fps=30,setsar=1,split=2[v5_bg_raw][v5_fg_raw];'
    f'[v5_bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[v5_bg];'
    f'[v5_fg_raw]scale=1080:-2[v5_fg];'
    f'[v5_bg][v5_fg]overlay=0:(H-h)/2,trim=0:12,setpts=PTS-STARTPTS,setsar=1,fps=30[seg5];'
    # Concat
    f'[seg1][seg2][seg3][seg4][seg5]concat=n=5:v=1:a=0[v_base];'
    # Burn in ASS
    f'[v_base]ass=\'{ass_filter_path}\':fontsdir=\'{fonts_dir}\'[v];'
    # Audio
    f'[1:a]apad=pad_dur=2.5[voice_padded];'
    f'[2:a]volume=0.08,afade=t=out:st=58.0:d=2.0[bgm_faded];'
    f'[voice_padded][bgm_faded]amix=inputs=2:duration=first:dropout_transition=2[a]" '
    f'-map "[v]" -map "[a]" -t 60.00 -c:v libx264 -preset fast -crf 20 -c:a aac -b:a 192k "{out_video}"'
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
if res.returncode != 0:
    print("Error:", res.stderr[-800:])
else:
    print("Success! Rendered:", out_video, out_video.stat().st_size)

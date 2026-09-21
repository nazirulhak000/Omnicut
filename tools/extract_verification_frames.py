import subprocess
from pathlib import Path

video = Path(".tmp/03_Outputs/Master_Clips_and_Previews/demo_xiaomi_mix_flip_cinematic_60s.mp4")
out_dir = Path(".tmp/03_Outputs/Master_Clips_and_Previews/verification_frames")
out_dir.mkdir(parents=True, exist_ok=True)

test_points = [
    (8.0, "08s_outer_display"),
    (13.0, "13s_pet_widgets"),
    (19.5, "19s_unfolding_hands"),
    (21.5, "21s_inner_686_oled"),
    (24.0, "24s_3000nits_galaxy_fix"),
    (29.0, "29s_leica_summilux_macro"),
    (31.5, "31s_leica_dual_lenses"),
    (35.5, "35s_cat_leica_sample"),
    (39.5, "39s_snapdragon_board"),
    (42.5, "42s_3d_vc_cooling_exploded"),
    (49.5, "49s_surge_battery_4780"),
    (52.5, "52s_puppy_flex_filming"),
    (58.0, "58s_hero_outro")
]

for t, name in test_points:
    out_img = out_dir / f"{name}.jpg"
    cmd = ["ffmpeg", "-y", "-ss", str(t), "-i", str(video), "-vframes", "1", "-vf", "scale=540:-1", str(out_img)]
    subprocess.run(cmd, capture_output=True)

print("Verification frames extracted!")

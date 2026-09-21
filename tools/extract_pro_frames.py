import subprocess
from pathlib import Path

video = Path(".tmp/03_Outputs/Master_Clips_and_Previews/demo_xiaomi_mix_flip_cinematic_60s.mp4")
out_dir = Path(".tmp/03_Outputs/Master_Clips_and_Previews/verification_pro")
out_dir.mkdir(parents=True, exist_ok=True)

test_points = [
    (8.0, "08s_outer_display_pro"),
    (20.0, "20s_unfolding_pro"),
    (23.0, "23s_inner_flower_pro"),
    (26.0, "26s_galaxy_3000nits_pro"),
    (30.0, "30s_leica_engraving_pro"),
    (36.0, "36s_beach_sample_pro"),
    (40.0, "40s_snapdragon_pro"),
    (44.0, "44s_3d_vc_holding_pro"),
    (47.0, "47s_3d_vc_still_holding_pro"),
    (50.0, "50s_surge_battery_pro")
]

for t, name in test_points:
    out_img = out_dir / f"{name}.jpg"
    cmd = ["ffmpeg", "-y", "-ss", str(t), "-i", str(video), "-vframes", "1", "-vf", "scale=540:-1", str(out_img)]
    subprocess.run(cmd, capture_output=True)

print("Pro verification frames extracted!")

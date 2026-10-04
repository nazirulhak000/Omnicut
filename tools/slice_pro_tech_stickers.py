"""
Slice photorealistic 3D IT review badge sheets into transparent PNG stickers.
Includes automatic backup of previous assets to 02_Assets/Stickers_Memes/_backup_cartoon/.
"""
import shutil
from pathlib import Path
from PIL import Image
import rembg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STICKERS_DIR = PROJECT_ROOT / "02_Assets" / "Stickers_Memes"
BACKUP_DIR = STICKERS_DIR / "_backup_cartoon"
DEFAULT_SHEET_DIR = PROJECT_ROOT / ".tmp" / "artifacts"

SHEET1 = {
    "badge_pros_review":    (0.01, 0.02, 0.49, 0.35),
    "badge_cons_review":    (0.51, 0.02, 0.99, 0.35),
    "badge_warning_review": (0.01, 0.35, 0.49, 0.67),
    "badge_pro_tip_review": (0.51, 0.35, 0.99, 0.67),
    "badge_performance_3d": (0.01, 0.67, 0.49, 0.98),
    "badge_verdict_review": (0.51, 0.67, 0.99, 0.98),
}

SHEET2 = {
    "badge_battery_life_3d":  (0.01, 0.02, 0.49, 0.35),
    "badge_build_quality_3d": (0.51, 0.02, 0.99, 0.35),
    "badge_specs_3d":         (0.01, 0.35, 0.49, 0.67),
    "badge_value_3d":         (0.51, 0.35, 0.99, 0.67),
    "arrow_tech_cyan_3d":     (0.01, 0.67, 0.49, 0.98),
    "hud_callout_bracket_3d": (0.51, 0.67, 0.99, 0.98),
}

SHEET3 = {
    "badge_score_review":     (0.01, 0.02, 0.49, 0.35),
    "badge_must_buy_3d":      (0.51, 0.02, 0.99, 0.35),
    "badge_display_3d":       (0.01, 0.35, 0.49, 0.67),
    "badge_audio_3d":         (0.51, 0.35, 0.99, 0.67),
    "badge_camera_3d":        (0.01, 0.67, 0.49, 0.98),
    "badge_connectivity_3d":  (0.51, 0.67, 0.99, 0.98),
}

def slice_pro_tech_stickers(sheet_dir=None):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    sheet_dir = Path(sheet_dir) if sheet_dir else DEFAULT_SHEET_DIR

    s1_path = sheet_dir / "it_pro_review_badges_sheet1_1788863222289.jpg"
    s2_path = sheet_dir / "it_pro_review_badges_sheet2_1788863242333.jpg"
    s3_path = sheet_dir / "it_pro_review_badges_sheet3_1788863338261.jpg"

    if not (s1_path.exists() and s2_path.exists() and s3_path.exists()):
        print(f"Sheet files not found in {sheet_dir}. Skipping slice.")
        return 0


    all_sheets = [
        ("Sheet 1 (Core Review)", s1_path, SHEET1),
        ("Sheet 2 (Hardware Specs)", s2_path, SHEET2),
        ("Sheet 3 (Features & Rating)", s3_path, SHEET3),
    ]

    session = rembg.new_session()
    saved_count = 0

    for sheet_name, path, boxes in all_sheets:
        print(f"\nProcessing {sheet_name} from {path.name}...")
        img = Image.open(path).convert("RGB")
        W, H = img.size

        for name, (x0, y0, x1, y1) in boxes.items():
            out_file = STICKERS_DIR / f"{name}.png"
            if out_file.exists():
                # Back up existing file to _backup_cartoon
                backup_file = BACKUP_DIR / out_file.name
                if not backup_file.exists():
                    shutil.copy2(out_file, backup_file)
                    print(f"  Backed up existing {out_file.name} -> {backup_file.name}")

            box = (int(W * x0), int(H * y0), int(W * x1), int(H * y1))
            crop = img.crop(box)
            nobg = rembg.remove(crop, session=session)
            bbox = nobg.getbbox()
            if bbox:
                nobg = nobg.crop(bbox)

            nobg.save(out_file, format="PNG", optimize=True)
            print(f"  [OK] Saved {out_file.name} - size {nobg.size} (RGBA)")
            saved_count += 1

    print(f"\nCompleted! Total {saved_count} photorealistic stickers saved to {STICKERS_DIR}")

if __name__ == "__main__":
    slice_pro_tech_stickers()

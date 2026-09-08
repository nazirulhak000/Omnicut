"""
Script to slice, background-remove, and catalog 3D CapCut-style sticker elements.
"""
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
import rembg

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "02_Assets"
STICKERS_DIR = ASSETS_DIR / "Stickers_Memes"

STICKERS_DIR.mkdir(parents=True, exist_ok=True)

def process_sticker_sheet(sheet_path: Path):
    img = Image.open(sheet_path)
    boxes = {
        'plate_banner_yellow_3d': (20, 30, 560, 260),
        'plate_banner_cyan_3d': (20, 260, 560, 480),
        'plate_banner_coral_3d': (20, 480, 560, 740),
        'frame_tech_callout_3d': (550, 30, 1050, 420),
        'arrow_pointer_yellow_3d': (1050, 30, 1360, 260),
        'arrow_pointer_cyan_3d': (1050, 260, 1360, 480),
        'accent_sparkle_star_3d': (550, 420, 810, 740),
        'badge_exclamation_alert_3d': (810, 420, 1070, 740),
        'icon_fire_hot_deal_3d': (1070, 480, 1360, 750),
    }

    for name, box in boxes.items():
        cropped = img.crop(box)
        nobg = rembg.remove(cropped)
        bbox = nobg.getbbox()
        if bbox:
            nobg = nobg.crop(bbox)
        out_path = STICKERS_DIR / f"{name}.png"
        nobg.save(out_path)
        print(f"Saved: {out_path} ({nobg.size})")

        # Create hollow variant for the frame
        if name == 'frame_tech_callout_3d':
            arr = np.array(nobg.convert('RGBA'))
            mask = np.zeros((arr.shape[0] + 2, arr.shape[1] + 2), np.uint8)
            rgb = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
            cv2.floodFill(rgb, mask, (arr.shape[1]//2, arr.shape[0]//2), (0, 0, 0), loDiff=(15, 15, 15), upDiff=(15, 15, 15))
            interior_mask = mask[1:-1, 1:-1] > 0
            arr_hollow = arr.copy()
            arr_hollow[interior_mask, 3] = 0
            hollow_im = Image.fromarray(arr_hollow)
            hollow_path = STICKERS_DIR / "frame_tech_callout_hollow_3d.png"
            hollow_im.save(hollow_path)
            print(f"Saved: {hollow_path} ({hollow_im.size})")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        process_sticker_sheet(Path(sys.argv[1]))
    else:
        master = STICKERS_DIR / "capcut_3d_assets_sheet_master.jpg"
        if master.exists():
            process_sticker_sheet(master)
        else:
            print("Usage: python tools/slice_capcut_stickers.py <path_to_sheet.jpg>")

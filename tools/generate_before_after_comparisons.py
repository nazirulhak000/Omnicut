"""
Generate Before vs After visual side-by-side comparison images.
Stitches baseline (Before) and live (After) screenshots with clear labels.
"""
import os
import sys
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CONV_ID = "b77e5ea7-30df-42da-82cc-823331993d51"
ARTIFACT_DIRS = [
    Path(fr"C:\Users\nazir\AppData\Roaming\AntigravityProfiles\Profile4\.gemini\antigravity\brain\{CONV_ID}"),
    Path(fr"C:\Users\nazir\AppData\Roaming\AntigravityProfiles\Profile3\.gemini\antigravity\brain\{CONV_ID}"),
]
OUT_DIR = Path("_Docs/Reports/comparisons")
OUT_DIR.mkdir(parents=True, exist_ok=True)
for ad in ARTIFACT_DIRS:
    ad.mkdir(parents=True, exist_ok=True)

COMPARISONS = [
    {
        "id": "compare_01_product_flow",
        "title": "1. หน้าสินค้า → คลิป (ProductToClip)",
        "desc": "ก่อนแก้: ใช้ Glassmorphism โปร่งแสงฟุ้งกระจาย, เส้นขอบนีออน | หลังแก้: Obsidian Pro Dark (#0A0D14), รหัสสินค้าเด่นชัด, ปุ่ม Action สุขุม",
        "before": "_Docs/Reports/baseline_phase00/desktop_01_product_to_clip.png",
        "after": "_Docs/Reports/live_snapshot/live_desktop_01_product_flow.png",
        "is_mobile": False,
    },
    {
        "id": "compare_02_editor_navbar",
        "title": "2. ห้องตัดต่อ Editor (Navbar & Canvas)",
        "desc": "ก่อนแก้: แสงเรืองรอบกรอบ, ชิปสถานะกระพริบ | หลังแก้: Obsidian Pro Dark, ชิปสถานะนิ่งตามความจริง, 9:16 Canvas ชัดเจน",
        "before": "_Docs/Reports/baseline_phase00/desktop_02_editor.png",
        "after": "_Docs/Reports/live_snapshot/live_desktop_02_editor.png",
        "is_mobile": False,
    },
    {
        "id": "compare_03_settings",
        "title": "3. การตั้งค่าระบบ (System Settings)",
        "desc": "ก่อนแก้: ตัวเลือกธีมและฟอนต์เป็น Gradient สีนีออน-ชมพูฉูดฉาด | หลังแก้: Obsidian Dark Card, ฟอนต์สไตล์ Studio เรียบหรู",
        "before": "_Docs/Reports/baseline_phase00/desktop_06_settings.png",
        "after": "_Docs/Reports/live_snapshot/live_desktop_06_settings.png",
        "is_mobile": False,
    },
    {
        "id": "compare_04_mobile_editor",
        "title": "4. Mobile Viewport: หน้าตัดต่อ Editor (แก้ Navbar ชนกัน)",
        "desc": "ก่อนแก้: Navbar ชนกันในจอ 390px ตัวหนังสือเบียดปุ่มเรนเดอร์ตกขอบ | หลังแก้: ยุบปุ่มและเว้นระยะพอดี ปุ่มเรนเดอร์เห็นครบ 100%",
        "before": "_Docs/Reports/baseline_phase00/mobile_03_editor.png",
        "after": "_Docs/Reports/live_snapshot/live_mobile_02_editor.png",
        "is_mobile": True,
    },
    {
        "id": "compare_05_tracker",
        "title": "5. Content Tracker 4 เฟส",
        "desc": "ก่อนแก้: พื้นหลังโปร่งแสง แสงสีฟุ้ง | หลังแก้: กระดาน Kanban คมชัด โทน Matte Neutral ระดับมืออาชีพ",
        "before": "_Docs/Reports/baseline_phase00/desktop_03_tracker.png",
        "after": "_Docs/Reports/live_snapshot/live_desktop_03_tracker.png",
        "is_mobile": False,
    },
]

def make_side_by_side(item):
    b_img = Image.open(item["before"]).convert("RGB")
    a_img = Image.open(item["after"]).convert("RGB")

    w, h = b_img.size
    banner_h = 70
    gap = 20
    total_w = (w * 2) + gap
    total_h = h + banner_h

    # Create composite canvas
    canvas = Image.new("RGB", (total_w, total_h), (10, 13, 20))
    draw = ImageDraw.Draw(canvas)

    # Paste images
    canvas.paste(b_img, (0, banner_h))
    canvas.paste(a_img, (w + gap, banner_h))

    # Banner backgrounds
    # Left banner: Red / Amber tint for "BEFORE"
    draw.rectangle([0, 0, w, banner_h], fill=(45, 15, 20))
    draw.rectangle([0, banner_h - 4, w, banner_h], fill=(239, 68, 68))

    # Right banner: Emerald / Cyan tint for "AFTER"
    draw.rectangle([w + gap, 0, total_w, banner_h], fill=(15, 35, 30))
    draw.rectangle([w + gap, banner_h - 4, total_w, banner_h], fill=(37, 244, 238))

    # Try font or fallback
    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_sub = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Draw text left
    draw.text((24, 12), "BEFORE (ก่อนปรับปรุง) — Slop / Glowing Halos / Overflow", fill=(255, 120, 120), font=font_title)
    draw.text((24, 42), "Glassmorphism จัดจ้าน, แสงเรืองรอบกรอบ, ตัวเลือกสีรุ้ง, Mobile Navbar ชนตกขอบ", fill=(200, 150, 150), font=font_sub)

    # Draw text right
    draw.text((w + gap + 24, 12), "AFTER (หลังปรับปรุง) — Obsidian Pro Dark NLE Studio", fill=(100, 255, 220), font=font_title)
    draw.text((w + gap + 24, 42), "พื้นหลัง #0A0D14 สุขุม, ลบแสงฟุ้ง, ชิปสถานะนิ่งตามความจริง, ปุ่มเรนเดอร์บนมือถือครบ 100%", fill=(160, 220, 210), font=font_sub)

    # Resize if too huge (for desktop 1440x2=2880 + 20 -> 2900 px, scale down to 1920 width for crisp preview)
    if total_w > 1920:
        scale = 1920 / total_w
        canvas = canvas.resize((1920, int(total_h * scale)), Image.Resampling.LANCZOS)

    out_file = OUT_DIR / f"{item['id']}.png"
    canvas.save(out_file, quality=92)

    # Copy to artifact directories
    for ad in ARTIFACT_DIRS:
        art_file = ad / f"{item['id']}.png"
        shutil.copyfile(str(out_file), str(art_file))

    print(f"Generated: {out_file} ({canvas.size[0]}x{canvas.size[1]})")
    return {
        "id": item["id"],
        "title": item["title"],
        "desc": item["desc"],
        "path": str(ARTIFACT_DIRS[0] / f"{item['id']}.png").replace("\\", "/"),
    }

if __name__ == "__main__":
    results = []
    for item in COMPARISONS:
        if os.path.exists(item["before"]) and os.path.exists(item["after"]):
            r = make_side_by_side(item)
            results.append(r)
        else:
            print("Missing file for", item["id"])
    print(f"\nCompleted {len(results)} side-by-side comparison images.")

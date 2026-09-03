"""
SUPERSEDED -- output does not match what is actually on disk anymore.

02_Assets/Stickers_Memes/ currently holds the 8 badge_*_3d.png files
produced by build_3d_pro_badges.py (the canonical sticker generator).
Re-running this script would regenerate a different, mismatched set of
filenames that nothing in the render pipeline references. Kept for
reference only -- do not run without first checking what StudioStep3Audio.jsx
and scripts/sfx_manager.py-style consumers actually expect.
"""

import os
import sys
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "02_Assets"
STICKERS_DIR = ASSETS_DIR / "Stickers_Memes"
FONTS_DIR = ASSETS_DIR / "Fonts"

STICKERS_DIR.mkdir(parents=True, exist_ok=True)

def find_font(font_name="Kanit-Black.ttf", size=48):
    candidate = FONTS_DIR / font_name
    if candidate.exists():
        return ImageFont.truetype(str(candidate), size)
    ttf_files = list(FONTS_DIR.glob("*.ttf"))
    if ttf_files:
        return ImageFont.truetype(str(ttf_files[0]), size)
    return ImageFont.load_default()

def remove_bg_rembg(image_path: Path, output_path: Path):
    """Removes solid background using rembg if available, or smart color keying."""
    try:
        from rembg import remove
        input_img = Image.open(image_path)
        output_img = remove(input_img)
        output_img.save(output_path, "PNG")
        print(f"[rembg] Saved transparent PNG: {output_path.name}")
        return True
    except Exception as e:
        print(f"[rembg fallback] {e}")
        img = Image.open(image_path).convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        img.save(output_path, "PNG")
        print(f"[keyed] Saved transparent PNG: {output_path.name}")
        return True

def create_rounded_gradient_badge(
    text_main,
    text_sub,
    color_top,
    color_bottom,
    icon_symbol="⚡",
    output_name="badge_sample.png",
    width=560,
    height=220,
    corner_radius=36,
    border_color=(255, 215, 0)
):
    """Synthesizes a high-end 3D glossy e-commerce badge with lighting, shadows, and Thai typography."""
    scale = 2
    w, h = width * scale, height * scale
    r = corner_radius * scale

    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # 1. Outer Glow / Soft 3D Drop Shadow
    shadow_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_img)
    shadow_rect = [16 * scale, 20 * scale, w - 16 * scale, h - 12 * scale]
    shadow_draw.rounded_rectangle(shadow_rect, radius=r, fill=(0, 0, 0, 160))
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=10 * scale))
    canvas.paste(shadow_img, (0, 0), shadow_img)

    # 2. Main Badge Base (Linear Gradient)
    base_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base_draw = ImageDraw.Draw(base_img)
    badge_rect = [14 * scale, 14 * scale, w - 14 * scale, h - 20 * scale]

    for y in range(int(badge_rect[1]), int(badge_rect[3])):
        ratio = (y - badge_rect[1]) / (badge_rect[3] - badge_rect[1])
        r_c = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g_c = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b_c = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        base_draw.line([(badge_rect[0], y), (badge_rect[2], y)], fill=(r_c, g_c, b_c, 255))

    mask = Image.new("L", (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(badge_rect, radius=r, fill=255)
    
    # 3. Outer Border
    border_width = 4 * scale
    border_mask = Image.new("L", (w, h), 0)
    border_draw = ImageDraw.Draw(border_mask)
    border_draw.rounded_rectangle(badge_rect, radius=r, outline=255, width=border_width)

    badge_composite = Image.composite(base_img, Image.new("RGBA", (w, h), (0, 0, 0, 0)), mask)

    # 4. Top Gloss Highlight (3D Glass Reflection)
    gloss_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gloss_draw = ImageDraw.Draw(gloss_img)
    gloss_rect = [badge_rect[0], badge_rect[1], badge_rect[2], badge_rect[1] + (badge_rect[3] - badge_rect[1]) * 0.45]
    gloss_draw.rounded_rectangle([gloss_rect[0] + 4, gloss_rect[1] + 4, gloss_rect[2] - 4, gloss_rect[3]], radius=r, fill=(255, 255, 255, 70))
    gloss_composite = Image.composite(gloss_img, Image.new("RGBA", (w, h), (0, 0, 0, 0)), mask)

    canvas.paste(badge_composite, (0, 0), badge_composite)
    canvas.paste(gloss_composite, (0, 0), gloss_composite)

    border_img = Image.new("RGBA", (w, h), (*border_color, 255))
    canvas.paste(border_img, (0, 0), border_mask)

    # 5. Draw Typography & Icon
    font_main = find_font("Kanit-Black.ttf", int(36 * scale))
    font_sub = find_font("Prompt-Bold.ttf", int(20 * scale))

    draw = ImageDraw.Draw(canvas)

    main_y = badge_rect[1] + 18 * scale if text_sub else (badge_rect[1] + badge_rect[3]) / 2 - 24 * scale
    main_x = badge_rect[0] + 28 * scale

    # Text Drop Shadow
    draw.text((main_x + 2 * scale, main_y + 3 * scale), f"{icon_symbol} {text_main}", font=font_main, fill=(0, 0, 0, 220))
    # Main White Text
    draw.text((main_x, main_y), f"{icon_symbol} {text_main}", font=font_main, fill=(255, 255, 255, 255))

    if text_sub:
        sub_y = main_y + 44 * scale
        sub_bbox = font_sub.getbbox(text_sub)
        sub_w = sub_bbox[2] - sub_bbox[0] + 24 * scale
        sub_h = sub_bbox[3] - sub_bbox[1] + 10 * scale
        pill_rect = [main_x, sub_y - 2 * scale, main_x + sub_w, sub_y + sub_h]
        draw.rounded_rectangle(pill_rect, radius=8 * scale, fill=(0, 0, 0, 140))
        draw.text((main_x + 12 * scale, sub_y), text_sub, font=font_sub, fill=(255, 235, 80, 255))

    final_img = canvas.resize((width, height), Image.Resampling.LANCZOS)
    out_path = STICKERS_DIR / output_name
    final_img.save(out_path, "PNG")
    print(f"[Generated Badge] {output_name} ({width}x{height})")
    return out_path

def main():
    print("🚀 Starting Professional 3D Sticker & Badge Generation...")

    # 1. Process AI Images if found in brain dir
    for jpg_file in BRAIN_DIR.glob("badge_*.jpg"):
        clean_name = jpg_file.stem.split("_1788")[0] + ".png"
        out_png = STICKERS_DIR / clean_name
        remove_bg_rembg(jpg_file, out_png)

    # 2. Synthesize High-Impact Thai E-Commerce Badges Suite (560x220)
    create_rounded_gradient_badge(
        text_main="FLASH SALE ลดด่วน!",
        text_sub="⚡ มีจำนวนจำกัด กดสั่งซื้อก่อนหมด",
        color_top=(254, 44, 85),
        color_bottom=(180, 10, 40),
        icon_symbol="⚡",
        output_name="badge_flash_sale_red.png",
        border_color=(255, 220, 50)
    )

    create_rounded_gradient_badge(
        text_main="ลดพิเศษ -50% วันนี้",
        text_sub="🔥 โปรโมชั่นพิเศษเฉพาะในคลิปนี้",
        color_top=(255, 120, 0),
        color_bottom=(220, 60, 0),
        icon_symbol="🏷️",
        output_name="badge_discount_50.png",
        border_color=(255, 240, 100)
    )

    create_rounded_gradient_badge(
        text_main="ซื้อ 1 แถม 1 ฟรี!",
        text_sub="🎁 คุ้มสุดๆ เซตของแถมจัดเต็ม",
        color_top=(147, 51, 234),
        color_bottom=(90, 20, 170),
        icon_symbol="🎁",
        output_name="badge_buy1_get1.png",
        border_color=(37, 244, 238)
    )

    create_rounded_gradient_badge(
        text_main="ส่งฟรีทั่วไทย 0 บาท",
        text_sub="🚚 จัดส่งด่วน ได้รับสินค้าใน 1-2 วัน",
        color_top=(16, 185, 129),
        color_bottom=(5, 120, 80),
        icon_symbol="🚚",
        output_name="badge_free_shipping.png",
        border_color=(167, 243, 208)
    )

    create_rounded_gradient_badge(
        text_main="⭐⭐⭐⭐⭐ 5.0 ดาว",
        text_sub="🏆 การันตีรีวิวจากผู้ใช้จริงกว่า 10,000+ คน",
        color_top=(234, 179, 8),
        color_bottom=(160, 110, 5),
        icon_symbol="👑",
        output_name="rating_5_stars.png",
        border_color=(255, 255, 200)
    )

    create_rounded_gradient_badge(
        text_main="มีเก็บเงินปลายทาง (COD)",
        text_sub="🛡️ เช็กของก่อนจ่ายเงิน มั่นใจได้ 100%",
        color_top=(30, 64, 175),
        color_bottom=(15, 35, 110),
        icon_symbol="💰",
        output_name="badge_cod_cash_on_delivery.png",
        border_color=(255, 215, 0)
    )

    create_rounded_gradient_badge(
        text_main="ของแท้ 100% มีประกัน",
        text_sub="✅ ศูนย์ไทย รับประกันเปลี่ยนคืนสินค้า",
        color_top=(13, 148, 136),
        color_bottom=(5, 90, 85),
        icon_symbol="🛡️",
        output_name="icon_check_verified.png",
        border_color=(37, 244, 238)
    )

    create_rounded_gradient_badge(
        text_main="จิ้มตะกร้าสีเหลืองซ้ายล่าง",
        text_sub="👉 กดที่ลิงก์ตรงนี้เพื่อดูราคาโปรโมชั่นเลย!",
        color_top=(234, 179, 8),
        color_bottom=(180, 120, 5),
        icon_symbol="🛒",
        output_name="sticker_yellow_basket_arrow.png",
        border_color=(255, 255, 255)
    )

    print("✨ All 8 Professional 3D Thai E-Commerce Badges Generated Successfully!")

if __name__ == "__main__":
    main()

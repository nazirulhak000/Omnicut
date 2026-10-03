"""Build 3D Pro Universal Badges and E-Commerce Stickers for Omnicut.

Generates:
1. Universal Video Badges (6 canonical review headers: PROS, CONS, WARNING, PRO TIP, VERDICT, SCORE)
   as defined in .agents/rules/sticker_generation.md.
2. Thai E-Commerce Badges (Free shipping, Best seller, Cart, Authentic shield, etc.)

Features:
- Sub-millimeter pixel precision with BiRefNet (Bilateral Reference Network)
- Automatic white die-cut contour stroke (12-16px, default 14px)
- Ultra-soft ambient 3D drop shadow
- Full transparency alpha channels (RGBA)
- GPU accelerated on NVIDIA RTX 4060 with safe CPU fallback
"""

import argparse
import math
import os
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.birefnet_engine import BiRefNetEngine, DEFAULT_MODEL, SUPPORTED_MODELS

ASSETS_DIR = BASE_DIR / "02_Assets"
STICKERS_DIR = ASSETS_DIR / "Stickers_Memes"
FONTS_DIR = ASSETS_DIR / "Fonts"

STICKERS_DIR.mkdir(parents=True, exist_ok=True)


def get_font(size=44, font_name="Kanit-Black.ttf") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    cand = FONTS_DIR / font_name
    if cand.exists():
        try:
            return ImageFont.truetype(str(cand), size)
        except Exception:
            pass
    ttfs = list(FONTS_DIR.glob("*.ttf"))
    if ttfs:
        try:
            return ImageFont.truetype(str(ttfs[0]), size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_3d_glossy_circle_badge(
    title_top: str,
    title_main: str,
    title_sub: str,
    theme_color: tuple[int, int, int],  # (R, G, B) primary
    theme_dark: tuple[int, int, int],   # (R, G, B) shadow
    icon_type: str,                     # "truck", "stars", "cart", "shield", "gift", "fire", "coins", "check", "cross", "warning", "lightbulb", "crown"
    output_filename: str,
    size: int = 600,
    output_dir: Path | None = None,
    add_diecut: bool = True,
    border_width: int = 14,
    engine: BiRefNetEngine | None = None,
) -> Path:
    """Renders a high-end 3D glossy circular/shield badge with optional white die-cut stroke."""
    scale = 2
    dim = size * scale
    cx, cy = dim // 2, dim // 2
    outer_r = int(dim * 0.44)
    inner_r = int(dim * 0.37)

    canvas = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))

    # 1. Soft 3D Ambient Drop Shadow (inner badge shadow before die-cut)
    if not add_diecut:
        shadow = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.ellipse(
            [cx - outer_r, cy - outer_r + 28 * scale, cx + outer_r, cy + outer_r + 28 * scale],
            fill=(0, 0, 0, 170),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=22 * scale))
        canvas.paste(shadow, (0, 0), shadow)

    # 2. Outer Metallic Gold Ring (3D Chamfer)
    gold_ring = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gold_ring)

    gold_top = (255, 235, 130)
    gold_mid = (230, 180, 40)
    g_draw.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r], fill=gold_mid)

    for i in range(outer_r - inner_r):
        curr_r = outer_r - i
        ratio = i / max(1, (outer_r - inner_r))
        r_col = int(gold_top[0] * (1 - ratio) + gold_mid[0] * ratio)
        g_col = int(gold_top[1] * (1 - ratio) + gold_mid[1] * ratio)
        b_col = int(gold_top[2] * (1 - ratio) + gold_mid[2] * ratio)
        g_draw.ellipse(
            [cx - curr_r, cy - curr_r, cx + curr_r, cy + curr_r],
            outline=(r_col, g_col, b_col, 255),
            width=2 * scale,
        )

    canvas.paste(gold_ring, (0, 0), gold_ring)

    # 3. Inner 3D Glossy Dome
    dome = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    d_draw = ImageDraw.Draw(dome)

    for r_step in range(inner_r, 0, -2 * scale):
        norm = (inner_r - r_step) / inner_r
        r_c = int(theme_color[0] * (1 - norm) + theme_dark[0] * norm)
        g_c = int(theme_color[1] * (1 - norm) + theme_dark[1] * norm)
        b_c = int(theme_color[2] * (1 - norm) + theme_dark[2] * norm)
        d_draw.ellipse([cx - r_step, cy - r_step, cx + r_step, cy + r_step], fill=(r_c, g_c, b_c, 255))

    dome_mask = Image.new("L", (dim, dim), 0)
    ImageDraw.Draw(dome_mask).ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=255)
    dome_comp = Image.composite(dome, Image.new("RGBA", (dim, dim), (0, 0, 0, 0)), dome_mask)
    canvas.paste(dome_comp, (0, 0), dome_comp)

    # 4. 3D Glass Specular Highlight (Top Crescent Gloss)
    gloss = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    gl_draw = ImageDraw.Draw(gloss)
    gl_rect = [cx - int(inner_r * 0.85), cy - int(inner_r * 0.95), cx + int(inner_r * 0.85), cy + int(inner_r * 0.15)]
    gl_draw.ellipse(gl_rect, fill=(255, 255, 255, 110))
    gloss_comp = Image.composite(gloss, Image.new("RGBA", (dim, dim), (0, 0, 0, 0)), dome_mask)
    canvas.paste(gloss_comp, (0, 0), gloss_comp)

    # 5. Draw 3D Center Icon & Graphics
    icon_layer = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    i_draw = ImageDraw.Draw(icon_layer)
    icon_cy = cy - int(inner_r * 0.18)

    if icon_type == "truck":
        truck_w, truck_h = int(140 * scale), int(90 * scale)
        tx, ty = cx - truck_w // 2, icon_cy - truck_h // 2
        i_draw.rounded_rectangle([tx, ty + 20 * scale, tx + truck_w - 40 * scale, ty + truck_h], radius=12 * scale, fill=(255, 255, 255, 255))
        i_draw.rounded_rectangle([tx + truck_w - 48 * scale, ty + 30 * scale, tx + truck_w, ty + truck_h], radius=10 * scale, fill=(255, 220, 50, 255))
        i_draw.rounded_rectangle([tx + truck_w - 38 * scale, ty + 36 * scale, tx + truck_w - 8 * scale, ty + 60 * scale], radius=6 * scale, fill=(30, 40, 60, 255))
        i_draw.ellipse([tx + 20 * scale, ty + truck_h - 16 * scale, tx + 52 * scale, ty + truck_h + 16 * scale], fill=(30, 30, 30, 255), outline=(230, 180, 40, 255), width=3 * scale)
        i_draw.ellipse([tx + truck_w - 42 * scale, ty + truck_h - 16 * scale, tx + truck_w - 10 * scale, ty + truck_h + 16 * scale], fill=(30, 30, 30, 255), outline=(230, 180, 40, 255), width=3 * scale)
        i_draw.polygon([(tx - 40 * scale, ty + 30 * scale), (tx - 10 * scale, ty + 30 * scale), (tx - 25 * scale, ty + 40 * scale)], fill=(255, 235, 80, 255))
        i_draw.polygon([(tx - 35 * scale, ty + 50 * scale), (tx - 10 * scale, ty + 50 * scale), (tx - 20 * scale, ty + 60 * scale)], fill=(255, 235, 80, 255))

    elif icon_type == "stars":
        cr_w = int(120 * scale)
        cr_pts = [
            (cx - cr_w // 2, icon_cy - 10 * scale),
            (cx - cr_w // 3, icon_cy + 25 * scale),
            (cx, icon_cy - 25 * scale),
            (cx + cr_w // 3, icon_cy + 25 * scale),
            (cx + cr_w // 2, icon_cy - 10 * scale),
            (cx + cr_w // 2 - 10 * scale, icon_cy + 35 * scale),
            (cx - cr_w // 2 + 10 * scale, icon_cy + 35 * scale),
        ]
        i_draw.polygon(cr_pts, fill=(255, 215, 0, 255), outline=(255, 245, 160, 255))
        for s_i in range(5):
            angle = math.radians(-150 + s_i * 30)
            star_r = int(inner_r * 0.70)
            sx = cx + int(star_r * math.cos(angle))
            sy = cy - int(star_r * math.sin(angle)) - 20 * scale
            i_draw.ellipse([sx - 12 * scale, sy - 12 * scale, sx + 12 * scale, sy + 12 * scale], fill=(255, 240, 100, 255))

    elif icon_type == "cart":
        cw, ch = int(100 * scale), int(80 * scale)
        cart_x, cart_y = cx - cw // 2 - 20 * scale, icon_cy - ch // 2
        i_draw.polygon([
            (cart_x, cart_y),
            (cart_x + cw, cart_y),
            (cart_x + cw - 16 * scale, cart_y + ch),
            (cart_x + 16 * scale, cart_y + ch),
        ], fill=(255, 255, 255, 255))
        i_draw.ellipse([cart_x + 20 * scale, cart_y + ch + 4 * scale, cart_x + 44 * scale, cart_y + ch + 28 * scale], fill=(255, 215, 0, 255))
        i_draw.ellipse([cart_x + cw - 40 * scale, cart_y + ch + 4 * scale, cart_x + cw - 16 * scale, cart_y + ch + 28 * scale], fill=(255, 215, 0, 255))
        arr_pts = [
            (cx + 40 * scale, icon_cy - 40 * scale),
            (cx + 70 * scale, icon_cy - 40 * scale),
            (cx + 70 * scale, icon_cy + 10 * scale),
            (cx + 95 * scale, icon_cy + 10 * scale),
            (cx + 55 * scale, icon_cy + 55 * scale),
            (cx + 15 * scale, icon_cy + 10 * scale),
            (cx + 40 * scale, icon_cy + 10 * scale),
        ]
        i_draw.polygon(arr_pts, fill=(255, 235, 20, 255), outline=(255, 255, 255, 255))

    elif icon_type == "shield":
        sw, sh = int(120 * scale), int(130 * scale)
        sh_pts = [
            (cx - sw // 2, icon_cy - sh // 3),
            (cx + sw // 2, icon_cy - sh // 3),
            (cx + sw // 2, icon_cy + 10 * scale),
            (cx, icon_cy + sh // 2),
            (cx - sw // 2, icon_cy + 10 * scale),
        ]
        i_draw.polygon(sh_pts, fill=(255, 255, 255, 255), outline=(255, 215, 0, 255))
        sh_inner = [
            (cx - sw // 2 + 10 * scale, icon_cy - sh // 3 + 8 * scale),
            (cx + sw // 2 - 10 * scale, icon_cy - sh // 3 + 8 * scale),
            (cx + sw // 2 - 10 * scale, icon_cy + 8 * scale),
            (cx, icon_cy + sh // 2 - 12 * scale),
            (cx - sw // 2 + 10 * scale, icon_cy + 8 * scale),
        ]
        i_draw.polygon(sh_inner, fill=(16, 185, 129, 255))
        i_draw.line([(cx - 24 * scale, icon_cy + 2 * scale), (cx - 6 * scale, icon_cy + 20 * scale), (cx + 26 * scale, icon_cy - 16 * scale)], fill=(255, 255, 255, 255), width=9 * scale)

    elif icon_type == "gift":
        gw, gh = int(110 * scale), int(90 * scale)
        gx, gy = cx - gw // 2, icon_cy - gh // 2 + 10 * scale
        i_draw.rounded_rectangle([gx, gy, gx + gw, gy + gh], radius=10 * scale, fill=(236, 72, 153, 255))
        i_draw.rectangle([cx - 12 * scale, gy, cx + 12 * scale, gy + gh], fill=(255, 215, 0, 255))
        i_draw.rectangle([gx, gy + gh // 2 - 12 * scale, gx + gw, gy + gh // 2 + 12 * scale], fill=(255, 215, 0, 255))
        i_draw.ellipse([cx - 36 * scale, gy - 26 * scale, cx - 4 * scale, gy + 4 * scale], fill=(255, 220, 50, 255))
        i_draw.ellipse([cx + 4 * scale, gy - 26 * scale, cx + 36 * scale, gy + 4 * scale], fill=(255, 220, 50, 255))

    elif icon_type == "fire":
        fw, fh = int(100 * scale), int(120 * scale)
        flame_pts = [
            (cx, icon_cy - fh // 2),
            (cx + fw // 2, icon_cy + 20 * scale),
            (cx + fw // 3, icon_cy + fh // 2),
            (cx - fw // 3, icon_cy + fh // 2),
            (cx - fw // 2, icon_cy + 20 * scale),
        ]
        i_draw.polygon(flame_pts, fill=(255, 100, 0, 255), outline=(255, 220, 50, 255))
        flame_inner = [
            (cx, icon_cy - fh // 4),
            (cx + fw // 4, icon_cy + 20 * scale),
            (cx + fw // 6, icon_cy + fh // 2 - 10 * scale),
            (cx - fw // 6, icon_cy + fh // 2 - 10 * scale),
            (cx - fw // 4, icon_cy + 20 * scale),
        ]
        i_draw.polygon(flame_inner, fill=(255, 235, 50, 255))

    elif icon_type == "coins":
        coin_w, coin_h = int(90 * scale), int(36 * scale)
        for c_idx in range(3):
            c_y = icon_cy + 15 * scale - c_idx * 22 * scale
            i_draw.ellipse([cx - coin_w // 2, c_y, cx + coin_w // 2, c_y + coin_h], fill=(255, 200, 20, 255), outline=(255, 245, 160, 255), width=3 * scale)
            i_draw.ellipse([cx - coin_w // 2 + 10 * scale, c_y + 6 * scale, cx + coin_w // 2 - 10 * scale, c_y + coin_h - 6 * scale], fill=(245, 160, 10, 255))

    elif icon_type == "check":
        # Glowing 3D Checkmark for PROS
        circ_r = int(55 * scale)
        i_draw.ellipse([cx - circ_r, icon_cy - circ_r, cx + circ_r, icon_cy + circ_r], fill=(34, 197, 94, 255), outline=(255, 255, 255, 255), width=4 * scale)
        i_draw.line([(cx - 28 * scale, icon_cy), (cx - 6 * scale, icon_cy + 22 * scale), (cx + 30 * scale, icon_cy - 18 * scale)], fill=(255, 255, 255, 255), width=10 * scale)

    elif icon_type == "cross":
        # Bold 3D Cross for CONS
        circ_r = int(55 * scale)
        i_draw.ellipse([cx - circ_r, icon_cy - circ_r, cx + circ_r, icon_cy + circ_r], fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=4 * scale)
        arm = int(24 * scale)
        i_draw.line([(cx - arm, icon_cy - arm), (cx + arm, icon_cy + arm)], fill=(255, 255, 255, 255), width=9 * scale)
        i_draw.line([(cx - arm, icon_cy + arm), (cx + arm, icon_cy - arm)], fill=(255, 255, 255, 255), width=9 * scale)

    elif icon_type == "warning":
        # 3D Hazard Triangle for WARNING
        tw, th = int(120 * scale), int(105 * scale)
        tri_pts = [
            (cx, icon_cy - th // 2 - 5 * scale),
            (cx + tw // 2, icon_cy + th // 2),
            (cx - tw // 2, icon_cy + th // 2),
        ]
        i_draw.polygon(tri_pts, fill=(245, 158, 11, 255), outline=(255, 255, 255, 255))
        # Exclamation point
        i_draw.line([(cx, icon_cy - 15 * scale), (cx, icon_cy + 15 * scale)], fill=(30, 30, 30, 255), width=8 * scale)
        i_draw.ellipse([cx - 5 * scale, icon_cy + 25 * scale, cx + 5 * scale, icon_cy + 35 * scale], fill=(30, 30, 30, 255))

    elif icon_type == "lightbulb":
        # 3D Glowing Bulb for PRO TIP
        bw, bh = int(70 * scale), int(70 * scale)
        i_draw.ellipse([cx - bw // 2, icon_cy - bh // 2 - 10 * scale, cx + bw // 2, icon_cy + bh // 2 - 10 * scale], fill=(255, 240, 80, 255), outline=(255, 255, 255, 255), width=3 * scale)
        # Bulb base
        i_draw.rounded_rectangle([cx - 16 * scale, icon_cy + bh // 2 - 14 * scale, cx + 16 * scale, icon_cy + bh // 2 + 10 * scale], radius=4 * scale, fill=(180, 180, 180, 255))
        # Glow rays
        for angle_deg in (-45, 0, 45, -90, 90):
            rad = math.radians(angle_deg - 90)
            x1 = cx + int(48 * scale * math.cos(rad))
            y1 = icon_cy - 10 * scale + int(48 * scale * math.sin(rad))
            x2 = cx + int(65 * scale * math.cos(rad))
            y2 = icon_cy - 10 * scale + int(65 * scale * math.sin(rad))
            i_draw.line([(x1, y1), (x2, y2)], fill=(255, 235, 100, 255), width=4 * scale)

    elif icon_type == "crown":
        # 3D Royal Crown / Stamp for VERDICT
        cr_w = int(120 * scale)
        cr_pts = [
            (cx - cr_w // 2, icon_cy - 10 * scale),
            (cx - cr_w // 3, icon_cy + 25 * scale),
            (cx, icon_cy - 25 * scale),
            (cx + cr_w // 3, icon_cy + 25 * scale),
            (cx + cr_w // 2, icon_cy - 10 * scale),
            (cx + cr_w // 2 - 10 * scale, icon_cy + 35 * scale),
            (cx - cr_w // 2 + 10 * scale, icon_cy + 35 * scale),
        ]
        i_draw.polygon(cr_pts, fill=(255, 215, 0, 255), outline=(255, 245, 160, 255))
        # Holographic jewels
        i_draw.ellipse([cx - 8 * scale, icon_cy - 22 * scale, cx + 8 * scale, icon_cy - 6 * scale], fill=(236, 72, 153, 255))

    canvas.paste(icon_layer, (0, 0), icon_layer)

    # 6. Typography Banner
    draw = ImageDraw.Draw(canvas)
    font_title = get_font(size=int(46 * scale), font_name="Kanit-Black.ttf")
    font_sub = get_font(size=int(26 * scale), font_name="Prompt-Bold.ttf")

    banner_w = int(dim * 0.78)
    banner_h = int(72 * scale)
    banner_x = cx - banner_w // 2
    banner_y = cy + int(inner_r * 0.40)

    # Banner Shadow & Body
    draw.rounded_rectangle(
        [banner_x + 4 * scale, banner_y + 6 * scale, banner_x + banner_w + 4 * scale, banner_y + banner_h + 6 * scale],
        radius=18 * scale,
        fill=(0, 0, 0, 160),
    )
    draw.rounded_rectangle(
        [banner_x, banner_y, banner_x + banner_w, banner_y + banner_h],
        radius=18 * scale,
        fill=(255, 255, 255, 255),
        outline=(255, 215, 0, 255),
        width=3 * scale,
    )

    t_box = font_title.getbbox(title_main)
    t_w = t_box[2] - t_box[0]
    t_h = t_box[3] - t_box[1]
    text_x = cx - t_w // 2
    text_y = banner_y + (banner_h - t_h) // 2 - 4 * scale

    draw.text((text_x + 2 * scale, text_y + 2 * scale), title_main, font=font_title, fill=(0, 0, 0, 160))
    draw.text((text_x, text_y), title_main, font=font_title, fill=(*theme_dark, 255))

    if title_sub:
        s_box = font_sub.getbbox(title_sub)
        s_w = s_box[2] - s_box[0]
        sub_x = cx - s_w // 2
        sub_y = banner_y + banner_h + 10 * scale
        draw.text((sub_x + 2 * scale, sub_y + 2 * scale), title_sub, font=font_sub, fill=(0, 0, 0, 220))
        draw.text((sub_x, sub_y), title_sub, font=font_sub, fill=(255, 240, 100, 255))

    final_badge = canvas.resize((size, size), Image.Resampling.LANCZOS)

    # Apply 3D white die-cut contour & ambient shadow if requested
    if add_diecut:
        final_badge = BiRefNetEngine.create_diecut_sticker(
            final_badge,
            border_width=border_width,
            border_color=(255, 255, 255, 255),
            shadow_blur=16,
            shadow_offset=(0, 10),
            shadow_opacity=140,
        )

    target_dir = output_dir or STICKERS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / output_filename
    final_badge.save(out_file, "PNG")
    print(f"[3D Badge Created] {output_filename} ({final_badge.size[0]}x{final_badge.size[1]}) -> {out_file.name}")
    return out_file


def generate_universal_badges(
    output_dir: Path | None = None,
    add_diecut: bool = True,
    border_width: int = 14,
    engine: BiRefNetEngine | None = None,
) -> list[Path]:
    """Generate the 6 Canonical Universal Video Badges per .agents/rules/sticker_generation.md."""
    print("🎨 Generating 6 Canonical Universal Video Badges with Die-Cut Borders...")
    created = []

    # 1. PROS (Universal Green Frosted Glass Badge with glowing checkmark)
    p1 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="PROS",
        title_sub="จุดเด่น / ข้อดี",
        theme_color=(34, 197, 94),
        theme_dark=(21, 128, 61),
        icon_type="check",
        output_filename="badge_pros_review.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p1)

    # 2. CONS (Universal Amber Red Frosted Glass Badge with cross icon)
    p2 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="CONS",
        title_sub="ข้อสังเกต / จุดด้อย",
        theme_color=(239, 68, 68),
        theme_dark=(185, 28, 28),
        icon_type="cross",
        output_filename="badge_cons_review.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p2)

    # 3. WARNING (Universal Hazard Yellow & Black with triangle warning)
    p3 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="WARNING",
        title_sub="ข้อควรระวัง / คำเตือน",
        theme_color=(245, 158, 11),
        theme_dark=(180, 83, 9),
        icon_type="warning",
        output_filename="badge_warning_review.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p3)

    # 4. PRO TIP (Universal Neon Cyan & Acrylic with glowing lightbulb)
    p4 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="PRO TIP",
        title_sub="เคล็ดลับ / เทคนิค",
        theme_color=(6, 182, 212),
        theme_dark=(14, 116, 144),
        icon_type="lightbulb",
        output_filename="badge_pro_tip_review.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p4)

    # 5. VERDICT (Universal Premium Holographic Certified Stamp / Crown)
    p5 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="VERDICT",
        title_sub="สรุป / ฟันธง",
        theme_color=(168, 85, 247),
        theme_dark=(126, 34, 206),
        icon_type="crown",
        output_filename="badge_verdict_review.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p5)

    # 6. SCORE (Universal Titanium & Star Rating Badge)
    p6 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="SCORE",
        title_sub="RATING ⭐⭐⭐⭐⭐",
        theme_color=(234, 179, 8),
        theme_dark=(161, 98, 7),
        icon_type="stars",
        output_filename="badge_score_review.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p6)

    return created


def generate_ecommerce_badges(
    output_dir: Path | None = None,
    add_diecut: bool = True,
    border_width: int = 14,
    engine: BiRefNetEngine | None = None,
) -> list[Path]:
    """Generate the Thai E-Commerce Badge Suite."""
    print("🎨 Generating Thai E-Commerce 3D Badges Suite...")
    created = []

    # 1) Free Shipping
    p1 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="ส่งฟรีทั่วไทย",
        title_sub="FREE SHIPPING",
        theme_color=(16, 185, 129),
        theme_dark=(5, 100, 60),
        icon_type="truck",
        output_filename="badge_free_shipping_3d.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p1)

    # 2) Best Seller
    p2 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="สินค้าขายดี",
        title_sub="BEST SELLER ⭐⭐⭐⭐⭐",
        theme_color=(234, 179, 8),
        theme_dark=(140, 80, 5),
        icon_type="stars",
        output_filename="badge_best_seller_3d.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p2)

    # 3) TikTok Yellow Cart
    p3 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="กดสั่งในตะกร้า",
        title_sub="SHOP NOW 👇",
        theme_color=(250, 204, 21),
        theme_dark=(180, 110, 0),
        icon_type="cart",
        output_filename="badge_yellow_cart_3d.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p3)

    # 4) Authentic Shield
    p4 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="การันตีของแท้",
        title_sub="100% AUTHENTIC",
        theme_color=(13, 148, 136),
        theme_dark=(6, 80, 70),
        icon_type="shield",
        output_filename="badge_authentic_shield_3d.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p4)

    # 5) Special Deal
    p5 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="โปรโมชั่นพิเศษ",
        title_sub="SPECIAL DEAL 🎁",
        theme_color=(168, 85, 247),
        theme_dark=(95, 25, 160),
        icon_type="gift",
        output_filename="badge_special_gift_3d.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p5)

    # 6) Hot Trending
    p6 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="ดีลเด็ดมาแรง",
        title_sub="HOT TRENDING 🔥",
        theme_color=(239, 68, 68),
        theme_dark=(150, 15, 25),
        icon_type="fire",
        output_filename="badge_hot_deal_3d.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p6)

    # 7) Cash on Delivery
    p7 = draw_3d_glossy_circle_badge(
        title_top="",
        title_main="เก็บเงินปลายทาง",
        title_sub="CASH ON DELIVERY 💰",
        theme_color=(30, 64, 175),
        theme_dark=(15, 30, 100),
        icon_type="coins",
        output_filename="badge_cod_secure_3d.png",
        output_dir=output_dir,
        add_diecut=add_diecut,
        border_width=border_width,
        engine=engine,
    )
    created.append(p7)

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 3D Badges & Stickers with Die-Cut and BiRefNet")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")
    parser.add_argument("--universal-only", action="store_true", help="Generate only the 6 universal badges")
    parser.add_argument("--ecommerce-only", action="store_true", help="Generate only the e-commerce badges")
    parser.add_argument("--no-diecut", action="store_true", help="Disable white die-cut border")
    parser.add_argument("--border-width", type=int, default=14, help="Die-cut border width in px (12-16)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, choices=SUPPORTED_MODELS, help="BiRefNet model")

    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve() if args.output_dir else STICKERS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = BiRefNetEngine(default_model=args.model)
    add_diecut = not args.no_diecut

    if args.universal_only:
        generate_universal_badges(output_dir=out_dir, add_diecut=add_diecut, border_width=args.border_width, engine=engine)
    elif args.ecommerce_only:
        generate_ecommerce_badges(output_dir=out_dir, add_diecut=add_diecut, border_width=args.border_width, engine=engine)
    else:
        generate_universal_badges(output_dir=out_dir, add_diecut=add_diecut, border_width=args.border_width, engine=engine)
        generate_ecommerce_badges(output_dir=out_dir, add_diecut=add_diecut, border_width=args.border_width, engine=engine)

    print("✨ All requested 3D Badges & Stickers successfully generated!")


if __name__ == "__main__":
    main()

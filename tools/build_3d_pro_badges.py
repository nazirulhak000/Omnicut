import os
import sys
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

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

def get_font(size=44, font_name="Kanit-Black.ttf"):
    cand = FONTS_DIR / font_name
    if cand.exists():
        return ImageFont.truetype(str(cand), size)
    ttfs = list(FONTS_DIR.glob("*.ttf"))
    if ttfs:
        return ImageFont.truetype(str(ttfs[0]), size)
    return ImageFont.load_default()

def draw_3d_glossy_circle_badge(
    title_top: str,
    title_main: str,
    title_sub: str,
    theme_color: tuple,       # (R, G, B) primary
    theme_dark: tuple,        # (R, G, B) shadow
    icon_type: str,           # "lightning", "truck", "stars", "cart", "shield", "gift", "fire", "coins"
    output_filename: str,
    size: int = 600
):
    """
    Renders an ultra-luxurious 3D glossy circular/shield e-commerce badge with:
    - 3D Spherical bevel & drop shadow
    - Concentric metallic gold ring with reflection highlights
    - Deep glossy 3D inner dome with radial gradient
    - Glassmorphism top specular highlight
    - 3D metallic icon & typography
    - 100% Clean transparent alpha background (600x600)
    """
    scale = 2
    dim = size * scale
    cx, cy = dim // 2, dim // 2
    outer_r = int(dim * 0.44)
    inner_r = int(dim * 0.37)

    canvas = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))

    # 1. Soft 3D Ambient Drop Shadow
    shadow = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.ellipse(
        [cx - outer_r, cy - outer_r + 28 * scale, cx + outer_r, cy + outer_r + 28 * scale],
        fill=(0, 0, 0, 170)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=22 * scale))
    canvas.paste(shadow, (0, 0), shadow)

    # 2. Outer Metallic Gold Ring (3D Chamfer)
    gold_ring = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gold_ring)
    
    # Draw metallic gold gradient ring
    gold_top = (255, 235, 130)
    gold_mid = (230, 180, 40)
    gold_dark = (140, 95, 15)

    g_draw.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r], fill=gold_mid)
    
    # Add 3D bevel shading on outer ring
    for i in range(outer_r - inner_r):
        curr_r = outer_r - i
        ratio = i / (outer_r - inner_r)
        # Highlight top-left, shadow bottom-right
        shade = int(255 * (1.0 - ratio * 0.5))
        r_col = int(gold_top[0] * (1 - ratio) + gold_mid[0] * ratio)
        g_col = int(gold_top[1] * (1 - ratio) + gold_mid[1] * ratio)
        b_col = int(gold_top[2] * (1 - ratio) + gold_mid[2] * ratio)
        g_draw.ellipse([cx - curr_r, cy - curr_r, cx + curr_r, cy + curr_r], outline=(r_col, g_col, b_col, 255), width=2 * scale)

    canvas.paste(gold_ring, (0, 0), gold_ring)

    # 3. Inner 3D Glossy Dome (Spherical Shading)
    dome = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    d_draw = ImageDraw.Draw(dome)

    # Draw radial gradient dome
    for r_step in range(inner_r, 0, -2 * scale):
        norm = (inner_r - r_step) / inner_r
        # Light source at (cx - inner_r*0.3, cy - inner_r*0.35)
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
    
    # Mask gloss to inner dome
    gloss_comp = Image.composite(gloss, Image.new("RGBA", (dim, dim), (0, 0, 0, 0)), dome_mask)
    canvas.paste(gloss_comp, (0, 0), gloss_comp)

    # 5. Draw 3D Center Icon & Graphics
    icon_layer = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    i_draw = ImageDraw.Draw(icon_layer)
    icon_cy = cy - int(inner_r * 0.18)

    if icon_type == "truck":
        # 3D Emerald Delivery Truck
        truck_w, truck_h = int(140 * scale), int(90 * scale)
        tx, ty = cx - truck_w // 2, icon_cy - truck_h // 2
        # Body
        i_draw.rounded_rectangle([tx, ty + 20*scale, tx + truck_w - 40*scale, ty + truck_h], radius=12*scale, fill=(255, 255, 255, 255))
        # Cabin
        i_draw.rounded_rectangle([tx + truck_w - 48*scale, ty + 30*scale, tx + truck_w, ty + truck_h], radius=10*scale, fill=(255, 220, 50, 255))
        # Window
        i_draw.rounded_rectangle([tx + truck_w - 38*scale, ty + 36*scale, tx + truck_w - 8*scale, ty + 60*scale], radius=6*scale, fill=(30, 40, 60, 255))
        # Wheels
        i_draw.ellipse([tx + 20*scale, ty + truck_h - 16*scale, tx + 52*scale, ty + truck_h + 16*scale], fill=(30, 30, 30, 255), outline=(230, 180, 40, 255), width=3*scale)
        i_draw.ellipse([tx + truck_w - 42*scale, ty + truck_h - 16*scale, tx + truck_w - 10*scale, ty + truck_h + 16*scale], fill=(30, 30, 30, 255), outline=(230, 180, 40, 255), width=3*scale)
        # Fast Speed Wings / Streaks
        i_draw.polygon([(tx - 40*scale, ty + 30*scale), (tx - 10*scale, ty + 30*scale), (tx - 25*scale, ty + 40*scale)], fill=(255, 235, 80, 255))
        i_draw.polygon([(tx - 35*scale, ty + 50*scale), (tx - 10*scale, ty + 50*scale), (tx - 20*scale, ty + 60*scale)], fill=(255, 235, 80, 255))

    elif icon_type == "stars":
        # 3D 5 Stars + Royal Trophy Crown
        # Crown
        cr_w = int(120 * scale)
        cr_pts = [
            (cx - cr_w//2, icon_cy - 10*scale),
            (cx - cr_w//3, icon_cy + 25*scale),
            (cx, icon_cy - 25*scale),
            (cx + cr_w//3, icon_cy + 25*scale),
            (cx + cr_w//2, icon_cy - 10*scale),
            (cx + cr_w//2 - 10*scale, icon_cy + 35*scale),
            (cx - cr_w//2 + 10*scale, icon_cy + 35*scale),
        ]
        i_draw.polygon(cr_pts, fill=(255, 215, 0, 255), outline=(255, 245, 160, 255))
        # 5 Golden Stars Arc
        for s_i in range(5):
            angle = math.radians(-150 + s_i * 30)
            star_r = int(inner_r * 0.70)
            sx = cx + int(star_r * math.cos(angle))
            sy = cy - int(star_r * math.sin(angle)) - 20 * scale
            # Small star
            i_draw.ellipse([sx - 12*scale, sy - 12*scale, sx + 12*scale, sy + 12*scale], fill=(255, 240, 100, 255))

    elif icon_type == "cart":
        # 3D TikTok Shopping Cart + Dynamic Downward Arrow
        cw, ch = int(100 * scale), int(80 * scale)
        cart_x, cart_y = cx - cw // 2 - 20*scale, icon_cy - ch // 2
        # Cart Basket
        i_draw.polygon([
            (cart_x, cart_y),
            (cart_x + cw, cart_y),
            (cart_x + cw - 16*scale, cart_y + ch),
            (cart_x + 16*scale, cart_y + ch)
        ], fill=(255, 255, 255, 255))
        # Cart Wheels
        i_draw.ellipse([cart_x + 20*scale, cart_y + ch + 4*scale, cart_x + 44*scale, cart_y + ch + 28*scale], fill=(255, 215, 0, 255))
        i_draw.ellipse([cart_x + cw - 40*scale, cart_y + ch + 4*scale, cart_x + cw - 16*scale, cart_y + ch + 28*scale], fill=(255, 215, 0, 255))
        # 3D Glossy Glowing Down Arrow
        arr_pts = [
            (cx + 40*scale, icon_cy - 40*scale),
            (cx + 70*scale, icon_cy - 40*scale),
            (cx + 70*scale, icon_cy + 10*scale),
            (cx + 95*scale, icon_cy + 10*scale),
            (cx + 55*scale, icon_cy + 55*scale),
            (cx + 15*scale, icon_cy + 10*scale),
            (cx + 40*scale, icon_cy + 10*scale),
        ]
        i_draw.polygon(arr_pts, fill=(255, 235, 20, 255), outline=(255, 255, 255, 255))

    elif icon_type == "shield":
        # 3D Authentic Guarantee Shield with Checkmark
        sw, sh = int(120 * scale), int(130 * scale)
        sh_pts = [
            (cx - sw//2, icon_cy - sh//3),
            (cx + sw//2, icon_cy - sh//3),
            (cx + sw//2, icon_cy + 10*scale),
            (cx, icon_cy + sh//2),
            (cx - sw//2, icon_cy + 10*scale)
        ]
        i_draw.polygon(sh_pts, fill=(255, 255, 255, 255), outline=(255, 215, 0, 255))
        # Emerald inner shield
        sh_inner = [
            (cx - sw//2 + 10*scale, icon_cy - sh//3 + 8*scale),
            (cx + sw//2 - 10*scale, icon_cy - sh//3 + 8*scale),
            (cx + sw//2 - 10*scale, icon_cy + 8*scale),
            (cx, icon_cy + sh//2 - 12*scale),
            (cx - sw//2 + 10*scale, icon_cy + 8*scale)
        ]
        i_draw.polygon(sh_inner, fill=(16, 185, 129, 255))
        # Shiny Checkmark
        i_draw.line([(cx - 24*scale, icon_cy + 2*scale), (cx - 6*scale, icon_cy + 20*scale), (cx + 26*scale, icon_cy - 16*scale)], fill=(255, 255, 255, 255), width=9*scale)

    elif icon_type == "gift":
        # 3D Open Gift Box with Golden Ribbons & Stars
        gw, gh = int(110 * scale), int(90 * scale)
        gx, gy = cx - gw // 2, icon_cy - gh // 2 + 10*scale
        # Box
        i_draw.rounded_rectangle([gx, gy, gx + gw, gy + gh], radius=10*scale, fill=(236, 72, 153, 255))
        # Gold Vertical & Horizontal Ribbons
        i_draw.rectangle([cx - 12*scale, gy, cx + 12*scale, gy + gh], fill=(255, 215, 0, 255))
        i_draw.rectangle([gx, gy + gh//2 - 12*scale, gx + gw, gy + gh//2 + 12*scale], fill=(255, 215, 0, 255))
        # Top Bow Lid
        i_draw.ellipse([cx - 36*scale, gy - 26*scale, cx - 4*scale, gy + 4*scale], fill=(255, 220, 50, 255))
        i_draw.ellipse([cx + 4*scale, gy - 26*scale, cx + 36*scale, gy + 4*scale], fill=(255, 220, 50, 255))

    elif icon_type == "fire":
        # 3D Hot Deal Flame
        fw, fh = int(100 * scale), int(120 * scale)
        flame_pts = [
            (cx, icon_cy - fh//2),
            (cx + fw//2, icon_cy + 20*scale),
            (cx + fw//3, icon_cy + fh//2),
            (cx - fw//3, icon_cy + fh//2),
            (cx - fw//2, icon_cy + 20*scale),
        ]
        i_draw.polygon(flame_pts, fill=(255, 100, 0, 255), outline=(255, 220, 50, 255))
        # Inner Yellow Core
        flame_inner = [
            (cx, icon_cy - fh//4),
            (cx + fw//4, icon_cy + 20*scale),
            (cx + fw//6, icon_cy + fh//2 - 10*scale),
            (cx - fw//6, icon_cy + fh//2 - 10*scale),
            (cx - fw//4, icon_cy + 20*scale),
        ]
        i_draw.polygon(flame_inner, fill=(255, 235, 50, 255))

    elif icon_type == "coins":
        # 3D Golden Coins Stack
        coin_w, coin_h = int(90 * scale), int(36 * scale)
        for c_idx in range(3):
            c_y = icon_cy + 15*scale - c_idx * 22*scale
            i_draw.ellipse([cx - coin_w//2, c_y, cx + coin_w//2, c_y + coin_h], fill=(255, 200, 20, 255), outline=(255, 245, 160, 255), width=3*scale)
            i_draw.ellipse([cx - coin_w//2 + 10*scale, c_y + 6*scale, cx + coin_w//2 - 10*scale, c_y + coin_h - 6*scale], fill=(245, 160, 10, 255))

    canvas.paste(icon_layer, (0, 0), icon_layer)

    # 6. Draw 3D Curved / Bounded Typography
    draw = ImageDraw.Draw(canvas)
    
    font_title = get_font(size=int(46 * scale), font_name="Kanit-Black.ttf")
    font_sub = get_font(size=int(26 * scale), font_name="Prompt-Bold.ttf")

    # Lower Ribbon Banner for Main Text
    banner_w = int(dim * 0.78)
    banner_h = int(72 * scale)
    banner_x = cx - banner_w // 2
    banner_y = cy + int(inner_r * 0.40)

    # Banner 3D Drop Shadow
    draw.rounded_rectangle(
        [banner_x + 4*scale, banner_y + 6*scale, banner_x + banner_w + 4*scale, banner_y + banner_h + 6*scale],
        radius=18*scale, fill=(0, 0, 0, 160)
    )
    # Banner Body (Gold / White Gradient)
    draw.rounded_rectangle(
        [banner_x, banner_y, banner_x + banner_w, banner_y + banner_h],
        radius=18*scale, fill=(255, 255, 255, 255), outline=(255, 215, 0, 255), width=3*scale
    )

    # Center Text in Banner
    t_box = font_title.getbbox(title_main)
    t_w = t_box[2] - t_box[0]
    t_h = t_box[3] - t_box[1]
    text_x = cx - t_w // 2
    text_y = banner_y + (banner_h - t_h) // 2 - 4 * scale

    # Text Shadow + Gradient Color Text
    draw.text((text_x + 2*scale, text_y + 2*scale), title_main, font=font_title, fill=(0, 0, 0, 160))
    draw.text((text_x, text_y), title_main, font=font_title, fill=(*theme_dark, 255))

    # Sub-text (Below Banner or Inside top)
    if title_sub:
        s_box = font_sub.getbbox(title_sub)
        s_w = s_box[2] - s_box[0]
        sub_x = cx - s_w // 2
        sub_y = banner_y + banner_h + 10 * scale
        draw.text((sub_x + 2*scale, sub_y + 2*scale), title_sub, font=font_sub, fill=(0, 0, 0, 220))
        draw.text((sub_x, sub_y), title_sub, font=font_sub, fill=(255, 240, 100, 255))

    # Downscale supersampled image for crisp 3D anti-aliasing
    final_badge = canvas.resize((size, size), Image.Resampling.LANCZOS)
    out_file = STICKERS_DIR / output_filename
    final_badge.save(out_file, "PNG")
    print(f"[3D Badge Created] {output_filename} ({size}x{size})")
    return out_file

def main():
    print("🎨 Building Consistent 3D Circular/Shield E-Commerce Badge Suite...")

    # 1. Clean up old rectangular plain boxes from Stickers folder
    unwanted = [
        "badge_buy1_get1.png",
        "badge_discount_50.png",
        "badge_flash_sale_red.png",
        "badge_free_shipping.png",
        "badge_cod_cash_on_delivery.png",
        "icon_check_verified.png",
        "rating_5_stars.png",
        "sticker_yellow_basket_arrow.png",
        "icon_check_green.png",
        "icon_cross_red.png"
    ]
    for old_file in unwanted:
        p = STICKERS_DIR / old_file
        if p.exists():
            try:
                p.unlink()
                print(f"🗑️ Removed old rectangle box: {old_file}")
            except Exception:
                pass

    # 2. Generate the Full Consistent 3D Glossy Circular Badge Suite (NO specific numbers!)
    
    # 1) Free Shipping (Emerald Green & Gold)
    draw_3d_glossy_circle_badge(
        title_top="",
        title_main="ส่งฟรีทั่วไทย",
        title_sub="FREE SHIPPING",
        theme_color=(16, 185, 129),
        theme_dark=(5, 100, 60),
        icon_type="truck",
        output_filename="badge_free_shipping_3d.png"
    )

    # 2) Best Seller / 5-Star Social Proof (Royal Gold & Purple)
    draw_3d_glossy_circle_badge(
        title_top="",
        title_main="สินค้าขายดี",
        title_sub="BEST SELLER ⭐⭐⭐⭐⭐",
        theme_color=(234, 179, 8),
        theme_dark=(140, 80, 5),
        icon_type="stars",
        output_filename="badge_best_seller_3d.png"
    )

    # 3) TikTok Yellow Cart Arrow (Sunny Yellow & Orange)
    draw_3d_glossy_circle_badge(
        title_top="",
        title_main="กดสั่งในตะกร้า",
        title_sub="SHOP NOW 👇",
        theme_color=(250, 204, 21),
        theme_dark=(180, 110, 0),
        icon_type="cart",
        output_filename="badge_yellow_cart_3d.png"
    )

    # 4) 100% Authentic / Quality Guarantee (Teal & Gold Shield)
    draw_3d_glossy_circle_badge(
        title_top="",
        title_main="การันตีของแท้",
        title_sub="100% AUTHENTIC",
        theme_color=(13, 148, 136),
        theme_dark=(6, 80, 70),
        icon_type="shield",
        output_filename="badge_authentic_shield_3d.png"
    )

    # 5) Special Deal / Bonus Gift (Neon Purple & Cyan)
    draw_3d_glossy_circle_badge(
        title_top="",
        title_main="โปรโมชั่นพิเศษ",
        title_sub="SPECIAL DEAL 🎁",
        theme_color=(168, 85, 247),
        theme_dark=(95, 25, 160),
        icon_type="gift",
        output_filename="badge_special_gift_3d.png"
    )

    # 6) Hot Trending / Viral Deal (Fiery Red & Orange)
    draw_3d_glossy_circle_badge(
        title_top="",
        title_main="ดีลเด็ดมาแรง",
        title_sub="HOT TRENDING 🔥",
        theme_color=(239, 68, 68),
        theme_dark=(150, 15, 25),
        icon_type="fire",
        output_filename="badge_hot_deal_3d.png"
    )

    # 7) Cash on Delivery / Secure Payment (Royal Navy & Gold)
    draw_3d_glossy_circle_badge(
        title_top="",
        title_main="เก็บเงินปลายทาง",
        title_sub="CASH ON DELIVERY 💰",
        theme_color=(30, 64, 175),
        theme_dark=(15, 30, 100),
        icon_type="coins",
        output_filename="badge_cod_secure_3d.png"
    )

    print("✨ Consistent 3D Circular/Shield E-Commerce Badges Suite Ready!")

if __name__ == "__main__":
    main()

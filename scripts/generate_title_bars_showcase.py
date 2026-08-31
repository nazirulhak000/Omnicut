"""
Generate Hook Title Bar Showcase Specimen Sheet
Showcases 5 distinct high-converting Hook Title Bar designs overlaid on 9:16 vertical video frames.
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

FONTS_DIR = Path("02_Assets/Fonts")
OUT_DIR = Path("02_Assets/Templates")
OUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path(r"C:\Users\Winon\.gemini\antigravity-ide\brain\6f51235b-b5d0-407b-9efc-9c44bcc9a6f1")

# Canvas Dimensions: 2000 x 2500 px
W, H = 2000, 2500

# Base Background: Deep Obsidian Slate
base = Image.new("RGBA", (W, H), (10, 14, 24, 255))
draw = ImageDraw.Draw(base)

# Background Ambient Glows
glow_canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gdraw = ImageDraw.Draw(glow_canvas)
gdraw.ellipse((-150, -150, 750, 750), fill=(254, 44, 85, 30))
gdraw.ellipse((W - 650, 400, W + 250, 1300), fill=(37, 244, 238, 25))
gdraw.ellipse((300, H - 750, 1200, H + 100), fill=(255, 230, 0, 20))
glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(140))
base = Image.alpha_composite(base, glow_canvas)
draw = ImageDraw.Draw(base)

# Fonts
title_font = ImageFont.truetype(str(FONTS_DIR / "Mitr-Bold.ttf"), 66)
subtitle_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 28)
tag_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 20)
card_title_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 30)
desc_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 21)
badge_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 18)

# Header Section
header_y = 60
badge_text = "2026 TIKTOK HOOK TITLE BAR DESIGNS"
bbox = tag_font.getbbox(badge_text)
bw, bh = bbox[2] - bbox[0] + 36, bbox[3] - bbox[1] + 16
bx = int((W - bw) / 2)
draw.rounded_rectangle([bx, header_y, bx + bw, header_y + bh], radius=14, fill=(254, 44, 85, 40), outline=(254, 44, 85, 180), width=2)
draw.text((bx + 18, header_y + 5), badge_text, font=tag_font, fill=(255, 255, 255, 255))

# Title
t_text = "ดีไซน์แถบพาดหัว Hook Title Bar 5 สไตล์"
t_bbox = title_font.getbbox(t_text)
draw.text((int((W - (t_bbox[2] - t_bbox[0])) / 2), header_y + 52), t_text, font=title_font, fill=(255, 255, 255, 255))

# Subtitle
sub_text = "แสดงผลช่วง 0 - 3.5 วินาทีแรก เพื่อหยุดนิ้วคนดูบน TikTok และกระตุ้นให้อยู่ดูจนจบ"
s_bbox = subtitle_font.getbbox(sub_text)
draw.text((int((W - (s_bbox[2] - s_bbox[0])) / 2), header_y + 138), sub_text, font=subtitle_font, fill=(160, 175, 200, 255))

draw.line([(80, header_y + 195), (W - 80, header_y + 195)], fill=(255, 255, 255, 20), width=2)

# 5 Title Bar Designs
DESIGNS = [
    {
        "id": "A",
        "name": "Style A: Neon Glow Capsule Pill",
        "tag": "นีออนเรืองแสง & แคปซูลมน",
        "tag_color": (37, 244, 238),
        "desc": "กล่องแคปซูลสีดำโปร่งใส ขอบเรืองแสงสีฟ้า/เหลืองนีออน + แบดจ์ HOOK สีแดงสะดุดตา",
        "font_name": "Prompt-Black.ttf",
        "title_text": "อย่าเพิ่งซื้อ! สายชาร์จแม่เหล็ก 3-in-1",
        "badge_text": "HOT HOOK",
        "badge_bg": (254, 44, 85),
        "bar_bg": (0, 0, 0, 220),
        "border_color": (37, 244, 238, 220),
        "text_color": (255, 255, 255),
        "accent_color": (255, 235, 59)
    },
    {
        "id": "B",
        "name": "Style B: Urgent Flash Warning",
        "tag": "แถบเตือนสีแดง-ดำ ด่วนกระชากสายตา",
        "tag_color": (255, 60, 60),
        "desc": "แถบเตือนสีแดงสด Gradient ดำ เหมาะกับคลิปแนว 'เตือนแล้วนะ / อย่าเพิ่งซื้อ / พังง่าย'",
        "font_name": "Kanit-Black.ttf",
        "title_text": "เตือนแล้วนะ! อย่าเพิ่งเลื่อนผ่านคลิปนี้",
        "badge_text": "WARNING 18+",
        "badge_bg": (255, 230, 0),
        "badge_text_color": (0, 0, 0),
        "bar_bg": (140, 10, 25, 240),
        "border_color": (255, 60, 60, 240),
        "text_color": (255, 255, 255),
        "accent_color": (255, 230, 0)
    },
    {
        "id": "C",
        "name": "Style C: Clean Aesthetic Frosted Glass",
        "tag": "มินิมอลเกาหลี คลีนหรูหรา",
        "tag_color": (255, 215, 140),
        "desc": "กล่องกระจกฝ้า Frosted Glass สีขาวนวล + แบดจ์ทองแชมเปญ สบายตา ดูแพงระดับห้าง",
        "font_name": "Mitr-SemiBold.ttf",
        "title_text": "ป้ายยาไอเทมเด็ด: สายชาร์จมินิมอล",
        "badge_text": "AESTHETIC",
        "badge_bg": (255, 215, 140),
        "badge_text_color": (20, 20, 20),
        "bar_bg": (255, 255, 255, 30),
        "border_color": (255, 255, 255, 90),
        "text_color": (255, 255, 255),
        "accent_color": (255, 240, 160)
    },
    {
        "id": "D",
        "name": "Style D: Cyber Tech HUD Frame",
        "tag": "ดาร์กโหมดไฟ LED ไซเบอร์ไอที",
        "tag_color": (0, 230, 255),
        "desc": "แถบสีกรมท่าเข้มขอบฟ้าโฮโลแกรม LED + แบดจ์ TECH 2026 เหมาะกับสินค้าไอที & โต๊ะคอม",
        "font_name": "IBMPlexSansThai-Bold.ttf",
        "title_text": "TECH GADGET: ชาร์จเร็ว 66W ดูดแน่น",
        "badge_text": "TECH 2026",
        "badge_bg": (0, 230, 255),
        "badge_text_color": (5, 15, 30),
        "bar_bg": (5, 18, 38, 240),
        "border_color": (0, 230, 255, 220),
        "text_color": (255, 255, 255),
        "accent_color": (0, 230, 255)
    },
    {
        "id": "E",
        "name": "Style E: Vibrant TikTok Yellow Banner",
        "tag": "แถบสีเหลืองนีออนเต็มความกว้าง",
        "tag_color": (255, 230, 0),
        "desc": "แถบสีเหลือง TikTok เต็มความกว้าง ตัวหนังสือดำหนาคมกริบ สไตล์ช่องรีวิวโปรโมชั่นยอดขายสูง",
        "font_name": "Prompt-Black.ttf",
        "title_text": "ของมันต้องมี! ลดพิเศษวันนี้แค่ 149 บาท",
        "badge_text": "FLASH SALE",
        "badge_bg": (0, 0, 0),
        "badge_text_color": (255, 230, 0),
        "bar_bg": (255, 230, 0, 255),
        "border_color": (255, 230, 0, 255),
        "text_color": (0, 0, 0),
        "accent_color": (200, 0, 0)
    }
]

# Render 5 Design Rows
start_y = 285
card_w = 1840
card_h = 390
gap_y = 40

for idx, d in enumerate(DESIGNS):
    cy = start_y + (idx * (card_h + gap_y))
    cx = (W - card_w) // 2
    
    # Outer Card Background
    card_img = Image.new("RGBA", (card_w, card_h), (18, 24, 38, 220))
    cdraw = ImageDraw.Draw(card_img)
    cdraw.rounded_rectangle([0, 0, card_w, card_h], radius=20, outline=(255, 255, 255, 30), width=2)
    
    # Card Header
    # Letter ID Badge (A, B, C, D, E)
    cdraw.ellipse([24, 20, 68, 64], fill=(254, 44, 85, 40), outline=(254, 44, 85, 180), width=2)
    n_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 24)
    nb = n_font.getbbox(d["id"])
    cdraw.text((24 + int((44 - (nb[2] - nb[0])) / 2), 20 + int((44 - (nb[3] - nb[1])) / 2) - 2), d["id"], font=n_font, fill=(255, 255, 255))
    
    # Design Title
    cdraw.text((82, 22), d["name"], font=card_title_font, fill=(255, 255, 255))
    
    # Tag Badge
    t_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-SemiBold.ttf"), 17)
    tb = t_font.getbbox(d["tag"])
    tbw = tb[2] - tb[0] + 20
    tbh = tb[3] - tb[1] + 10
    tbx = card_w - tbw - 24
    tby = 24
    cdraw.rounded_rectangle([tbx, tby, tbx + tbw, tby + tbh], radius=10, fill=(d["tag_color"][0], d["tag_color"][1], d["tag_color"][2], 30), outline=d["tag_color"], width=1)
    cdraw.text((tbx + 10, tby + 3), d["tag"], font=t_font, fill=d["tag_color"])
    
    # Description
    cdraw.text((24, 76), d["desc"], font=desc_font, fill=(160, 175, 200))
    
    # Simulated Video Screen Viewport (Simulates the top portion of a vertical 9:16 TikTok video)
    vp_y = 120
    vp_h = 240
    cdraw.rounded_rectangle([18, vp_y, card_w - 18, vp_y + vp_h], radius=16, fill=(8, 11, 18, 255), outline=(255, 255, 255, 15), width=1)
    
    # Draw simulated video top UI (clock 9:41, wifi, battery indicators)
    stat_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 14)
    cdraw.text((36, vp_y + 12), "9:41  •  TikTok Camera Viewport (Top 25%)", font=stat_font, fill=(90, 100, 120))
    
    # RENDER THE ACTUAL TITLE BAR INSIDE THE SIMULATED VIDEO
    bar_y = vp_y + 65
    bar_h = 100
    bar_w = card_w - 140
    bar_x = (card_w - bar_w) // 2
    
    bar_font = ImageFont.truetype(str(FONTS_DIR / d["font_name"]), 38)
    
    # Draw Bar Container
    if d["id"] == "E":
        # Full width solid yellow banner
        cdraw.rectangle([19, bar_y, card_w - 19, bar_y + bar_h], fill=d["bar_bg"])
    elif d["id"] == "C":
        # Frosted glass capsule pill
        cdraw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=50, fill=d["bar_bg"], outline=d["border_color"], width=2)
    else:
        # High-tech neon capsule pill
        cdraw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=50, fill=d["bar_bg"], outline=d["border_color"], width=3)
        
    # Draw Internal Badge inside Bar (Left side)
    ib_text = d["badge_text"]
    ib_bbox = badge_font.getbbox(ib_text)
    ib_w = ib_bbox[2] - ib_bbox[0] + 24
    ib_h = ib_bbox[3] - ib_bbox[1] + 14
    ib_x = bar_x + 30 if d["id"] != "E" else 45
    ib_y = bar_y + (bar_h - ib_h) // 2
    
    ib_color = d.get("badge_text_color", (255, 255, 255))
    cdraw.rounded_rectangle([ib_x, ib_y, ib_x + ib_w, ib_y + ib_h], radius=12, fill=d["badge_bg"])
    cdraw.text((ib_x + 12, ib_y + 4), ib_text, font=badge_font, fill=ib_color)
    
    # Draw Main Title Text
    main_t = d["title_text"]
    tb_bbox = bar_font.getbbox(main_t)
    tb_h = tb_bbox[3] - tb_bbox[1]
    
    tx = ib_x + ib_w + 24
    ty = bar_y + (bar_h - tb_h) // 2 - 4
    
    # Outline if needed
    if d["id"] != "E":
        for ox in (-2, -1, 1, 2):
            for oy in (-2, -1, 1, 2):
                cdraw.text((tx + ox, ty + oy), main_t, font=bar_font, fill=(0, 0, 0, 200))
    cdraw.text((tx, ty), main_t, font=bar_font, fill=d["text_color"])

    base.paste(card_img, (cx, cy), card_img)

# Save Master Poster
out_png = OUT_DIR / "hook_title_bars_showcase.png"
base.save(out_png, "PNG")

# Also copy to artifacts directory
artifact_png = ARTIFACT_DIR / "hook_title_bars_showcase.png"
base.save(artifact_png, "PNG")

print(f"✓ Hook Title Bars Showcase generated successfully:\n  - {out_png}\n  - {artifact_png}")

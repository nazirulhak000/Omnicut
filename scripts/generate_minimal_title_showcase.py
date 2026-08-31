"""
Generate Minimal Frameless Big Title Headers Showcase (Font-Only with Outlines, NO Background Boxes)
Overlaid on realistic 9:16 vertical video backgrounds.
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
title_font = ImageFont.truetype(str(FONTS_DIR / "Mitr-Bold.ttf"), 64)
subtitle_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 28)
tag_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 20)
card_title_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 30)
desc_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 21)

# Header Section
header_y = 60
badge_text = "2026 MINIMAL FRAMELESS HOOK HEADERS"
bbox = tag_font.getbbox(badge_text)
bw, bh = bbox[2] - bbox[0] + 36, bbox[3] - bbox[1] + 16
bx = int((W - bw) / 2)
draw.rounded_rectangle([bx, header_y, bx + bw, header_y + bh], radius=14, fill=(254, 44, 85, 40), outline=(254, 44, 85, 180), width=2)
draw.text((bx + 18, header_y + 5), badge_text, font=tag_font, fill=(255, 255, 255, 255))

# Title
t_text = "ตัวอย่างฟอนต์พาดหัวตัวใหญ่ ไร้กรอบพื้นหลัง (Minimal Outline)"
t_bbox = title_font.getbbox(t_text)
draw.text((int((W - (t_bbox[2] - t_bbox[0])) / 2), header_y + 52), t_text, font=title_font, fill=(255, 255, 255, 255))

# Subtitle
sub_text = "ฟอนต์ใหญ่ คมชัด มีขอบดำตัดเส้น สะอาดตา ไม่บดบังวิดีโอ (0 - 3.5 วินาทีแรก)"
s_bbox = subtitle_font.getbbox(sub_text)
draw.text((int((W - (s_bbox[2] - s_bbox[0])) / 2), header_y + 138), sub_text, font=subtitle_font, fill=(160, 175, 200, 255))

draw.line([(80, header_y + 195), (W - 80, header_y + 195)], fill=(255, 255, 255, 20), width=2)

# 5 Minimal Title Styles (No background box, just pure large font + outline/shadow)
DESIGNS = [
    {
        "id": "01",
        "name": "Option 01: Pure White + Clean Soft Outline",
        "tag": "มินิมอลเกาหลี คลีนตา 100%",
        "tag_color": (37, 244, 238),
        "desc": "ตัวหนังสือสีขาวล้วน ขอบดำบาง 6px คมกริบ สบายตา ไม่รกฉากหลัง",
        "font_file": "Mitr-Bold.ttf",
        "font_size": 60,
        "line1": "อย่าเพิ่งซื้อสายชาร์จ",
        "line2": "ถ้ายังไม่เห็นตัวนี้!",
        "c1": (255, 255, 255),
        "c2": (255, 255, 255),
        "outline_w": 6,
        "outline_c": (0, 0, 0)
    },
    {
        "id": "02",
        "name": "Option 02: TikTok Viral Yellow + Solid Black Stroke",
        "tag": "สีเหลืองไวรัล เด่นสะดุดตา",
        "tag_color": (255, 230, 0),
        "desc": "ตัวหนังสือสีเหลืองนีออนขอบดำหนา 7px พลังหยุดนิ้วโป้งสูง สไตล์ช่องยอดขายหลักล้าน",
        "font_file": "Prompt-Black.ttf",
        "font_size": 58,
        "line1": "สายชาร์จแม่เหล็ก 3-in-1",
        "line2": "ตัวเดียวจบทุกปัญหา!",
        "c1": (255, 230, 0),
        "c2": (255, 230, 0),
        "outline_w": 7,
        "outline_c": (0, 0, 0)
    },
    {
        "id": "03",
        "name": "Option 03: Dual Tone (White + Gold Highlight)",
        "tag": "สองโทนสี ขาวสลับทอง",
        "tag_color": (255, 215, 140),
        "desc": "บรรทัดแรกสีขาว บรรทัดสองเน้นสีทอง/เหลือง เพิ่มมิติให้น่าอ่านและดูแพง",
        "font_file": "Mitr-Bold.ttf",
        "font_size": 60,
        "line1": "เตือนแล้วนะ!",
        "line2": "อย่าซื้อสายชาร์จแบบเดิม",
        "c1": (255, 255, 255),
        "c2": (255, 220, 80),
        "outline_w": 6,
        "outline_c": (0, 0, 0)
    },
    {
        "id": "04",
        "name": "Option 04: Cyber Tech Cyan (สายไอที / แกดเจ็ต)",
        "tag": "สีฟ้าไซเบอร์ สายเทคพรีเมียม",
        "tag_color": (0, 230, 255),
        "desc": "ตัวหนังสือสีฟ้า Cyber Cyan ขอบดำคม เหมาะกับสินค้าไอที โต๊ะคอม และอุปกรณ์ล้ำๆ",
        "font_file": "IBMPlexSansThai-Bold.ttf",
        "font_size": 56,
        "line1": "ชาร์จเร็ว 66W ดูดแน่น",
        "line2": "ข้อต่อหมุน 540 องศา",
        "c1": (0, 230, 255),
        "c2": (255, 255, 255),
        "outline_w": 5,
        "outline_c": (0, 0, 0)
    },
    {
        "id": "05",
        "name": "Option 05: High-Impact Red & Orange (สายแจ้งเตือน/ด่วน)",
        "tag": "สีแดงส้ม พลังกระชากสายตา",
        "tag_color": (255, 70, 70),
        "desc": "ตัวหนังสือสีส้มอมแดงขอบดำ เหมาะกับคลิปที่ต้องการให้คนหยุดดูแบบเร่งด่วน",
        "font_file": "Kanit-Black.ttf",
        "font_size": 60,
        "line1": "อย่าเพิ่งเลื่อนผ่าน!",
        "line2": "ของดีที่ต้องมีติดกระเป๋า",
        "c1": (255, 75, 75),
        "c2": (255, 230, 0),
        "outline_w": 8,
        "outline_c": (0, 0, 0)
    }
]

# Render 5 Options
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
    
    # Letter ID Badge (01, 02, ...)
    cdraw.ellipse([24, 20, 68, 64], fill=(254, 44, 85, 40), outline=(254, 44, 85, 180), width=2)
    n_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 22)
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
    
    # Simulated Video Screen Viewport (Simulates real video footage background)
    vp_y = 120
    vp_h = 240
    cdraw.rounded_rectangle([18, vp_y, card_w - 18, vp_y + vp_h], radius=16, fill=(12, 16, 26, 255), outline=(255, 255, 255, 15), width=1)
    
    # Draw simulated video scenery / lines in background
    for gy in range(vp_y + 35, vp_y + vp_h - 20, 45):
        cdraw.line([(32, gy), (card_w - 32, gy)], fill=(255, 255, 255, 8), width=1)
    
    stat_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 14)
    cdraw.text((36, vp_y + 12), "9:41  •  TikTok Camera Viewport (Top 25% - NO BACKGROUND BOX)", font=stat_font, fill=(90, 100, 120))
    
    # RENDER LARGE TITLE TEXT WITH CRISP OUTLINE (NO BOX)
    s_font = ImageFont.truetype(str(FONTS_DIR / d["font_file"]), d["font_size"])
    l1 = d["line1"]
    l2 = d["line2"]
    
    b1 = s_font.getbbox(l1)
    w1 = b1[2] - b1[0]
    h1 = b1[3] - b1[1]
    
    b2 = s_font.getbbox(l2)
    w2 = b2[2] - b2[0]
    h2 = b2[3] - b2[1]
    
    line_gap = 14
    total_h = h1 + line_gap + h2
    
    center_y = vp_y + int((vp_h - total_h) / 2) + 8
    y1 = center_y
    y2 = center_y + h1 + line_gap
    
    x1 = int((card_w - w1) / 2)
    x2 = int((card_w - w2) / 2)
    
    ow = d["outline_w"]
    oc = d["outline_c"]
    
    # 1. Draw crisp outline around text
    for ox in range(-ow, ow + 1):
        for oy in range(-ow, ow + 1):
            if ox != 0 or oy != 0:
                cdraw.text((x1 + ox, y1 + oy), l1, font=s_font, fill=oc)
                cdraw.text((x2 + ox, y2 + oy), l2, font=s_font, fill=oc)
                
    # 2. Draw front text
    cdraw.text((x1, y1), l1, font=s_font, fill=d["c1"])
    cdraw.text((x2, y2), l2, font=s_font, fill=d["c2"])

    base.paste(card_img, (cx, cy), card_img)

# Save Master Poster
out_png = OUT_DIR / "minimal_title_showcase.png"
base.save(out_png, "PNG")

# Also copy to artifacts directory
artifact_png = ARTIFACT_DIR / "minimal_title_showcase.png"
base.save(artifact_png, "PNG")

print(f"✓ Minimal Title Showcase generated successfully:\n  - {out_png}\n  - {artifact_png}")

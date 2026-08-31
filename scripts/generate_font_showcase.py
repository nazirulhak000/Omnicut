"""
Generate Ultra-Premium Thai Typography Showcase Specimen Sheet (Flawless Typography & Zero Tofu)
Creates an ultra-sharp design poster showcasing 6 font styles with real rendered Thai Google Fonts.
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

# Canvas Dimensions (Ultra Sharp 1800 x 2400)
W, H = 1800, 2400

# Base Background: Deep Obsidian Gradient (#0B0F19 -> #06080E)
base = Image.new("RGBA", (W, H), (11, 15, 25, 255))
draw = ImageDraw.Draw(base)

# Ambient Studio Lighting Glows
glow_canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gdraw = ImageDraw.Draw(glow_canvas)
gdraw.ellipse((-150, -150, 750, 750), fill=(254, 44, 85, 35)) # Top-left Crimson Glow
gdraw.ellipse((W - 650, 350, W + 250, 1250), fill=(37, 244, 238, 30)) # Right Cyan Glow
gdraw.ellipse((250, H - 850, 1150, H + 50), fill=(254, 44, 85, 22)) # Bottom Pink Glow
glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(130))
base = Image.alpha_composite(base, glow_canvas)
draw = ImageDraw.Draw(base)

# Load UI Fonts
title_font = ImageFont.truetype(str(FONTS_DIR / "Mitr-Bold.ttf"), 64)
subtitle_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 28)
tag_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 20)
card_title_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 32)
desc_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 22)
num_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Black.ttf"), 22)
tip_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 17)

# Header Section
header_y = 65

# Badge
badge_text = "2026 TIKTOK AFFILIATE TYPOGRAPHY SHOWCASE"
bbox = tag_font.getbbox(badge_text)
bw, bh = bbox[2] - bbox[0] + 36, bbox[3] - bbox[1] + 16
bx = int((W - bw) / 2)
draw.rounded_rectangle([bx, header_y, bx + bw, header_y + bh], radius=14, fill=(254, 44, 85, 40), outline=(254, 44, 85, 190), width=2)
draw.text((bx + 18, header_y + 5), badge_text, font=tag_font, fill=(255, 255, 255, 255))

# Title
t_text = "คอลเลกชันฟอนต์ซับไตเติลมินิมอล & ไอที"
t_bbox = title_font.getbbox(t_text)
draw.text((int((W - (t_bbox[2] - t_bbox[0])) / 2), header_y + 52), t_text, font=title_font, fill=(255, 255, 255, 255))

# Subtitle
sub_text = "คัดสรร 6 ฟอนต์ภาษาไทยยอดนิยม พร้อมสไตล์แต่งตัวหนังสือเพื่อคลิป TikTok ขายดี"
s_bbox = subtitle_font.getbbox(sub_text)
draw.text((int((W - (s_bbox[2] - s_bbox[0])) / 2), header_y + 138), sub_text, font=subtitle_font, fill=(160, 175, 200, 255))

# Divider Line
draw.line([(90, header_y + 195), (W - 90, header_y + 195)], fill=(255, 255, 255, 20), width=2)

# 6 Showcase Cards (2 Columns x 3 Rows)
CARDS = [
    {
        "id": "01",
        "name": "Mitr (มิตร)",
        "badge": "มินิมอลเกาหลี / คลีน",
        "badge_color": (37, 244, 238, 255),
        "desc": "เส้นสายโค้งมน สะอาดตา สบายตา ไม่บดบังภาพวิดีโอ (ยอดฮิตอันดับ 1)",
        "sample_line1": "อย่าเพิ่งซื้อสายชาร์จ",
        "sample_line2": "ถ้ายังไม่เห็นตัวนี้!",
        "font_file": "Mitr-SemiBold.ttf",
        "font_size": 48,
        "style_type": "soft_outline",
        "sub_color1": (255, 255, 255),
        "sub_color2": (255, 235, 59),
        "outline_color": (0, 0, 0),
        "outline_w": 5
    },
    {
        "id": "02",
        "name": "IBM Plex Sans Thai",
        "badge": "เทค / ไอทีพรีเมียม",
        "badge_color": (0, 230, 255, 255),
        "desc": "ฟอนต์มาตรฐานสากล คมกริบ เรียบหรู สไตล์แก็ดเจ็ตและโต๊ะคอมระดับไฮเอนด์",
        "sample_line1": "แม่เหล็กแรงดูดสูง 66W",
        "sample_line2": "ชาร์จเร็ว เครื่องไม่ร้อน",
        "font_file": "IBMPlexSansThai-Bold.ttf",
        "font_size": 45,
        "style_type": "soft_outline",
        "sub_color1": (0, 230, 255),
        "sub_color2": (255, 255, 255),
        "outline_color": (0, 0, 0),
        "outline_w": 4
    },
    {
        "id": "03",
        "name": "Prompt (พร้อมท์)",
        "badge": "โมเดิร์น เรขาคณิต",
        "badge_color": (255, 200, 50, 255),
        "desc": "อ่านง่าย ชัดเจนทุกมุมมอง ทรงพลัง ให้ความรู้สึกทันสมัยและเป็นมืออาชีพ",
        "sample_line1": "ข้อต่อหมุน 540 องศา",
        "sample_line2": "เล่นเกมไม่สะดุด ไม่ติดมือ",
        "font_file": "Prompt-Black.ttf",
        "font_size": 44,
        "style_type": "soft_outline",
        "sub_color1": (255, 255, 255),
        "sub_color2": (255, 240, 100),
        "outline_color": (0, 0, 0),
        "outline_w": 6
    },
    {
        "id": "04",
        "name": "Chakra Petch (จักรเพชร)",
        "badge": "ไซเบอร์ / ไฮเทค",
        "badge_color": (254, 44, 85, 255),
        "desc": "ทรงเหลี่ยมล้ำอนาคต เหมาะกับคลิปรีวิวไอที เกมมิ่ง และอุปกรณ์ไฮเทค",
        "sample_line1": "หมดปัญหาสายหักตรงคอ",
        "sample_line2": "เสียบในที่มืดได้ทันที",
        "font_file": "ChakraPetch-Bold.ttf",
        "font_size": 44,
        "style_type": "soft_outline",
        "sub_color1": (255, 240, 100),
        "sub_color2": (255, 255, 255),
        "outline_color": (0, 0, 0),
        "outline_w": 5
    },
    {
        "id": "05",
        "name": "Kanit (คณิต)",
        "badge": "ตัวหนา TikTok ไวรัล",
        "badge_color": (255, 60, 60, 255),
        "desc": "ตัวหนาพิเศษ พลังหยุดนิ้วโป้งสูง เหมาะกับการเน้นโปรโมชั่น และราคาพิเศษ",
        "sample_line1": "ลดพิเศษวันนี้ 149 บาท",
        "sample_line2": "จิ้มตะกร้าซ้ายล่างเลย!",
        "font_file": "Kanit-Black.ttf",
        "font_size": 44,
        "style_type": "bold_pop",
        "sub_color1": (255, 235, 59),
        "sub_color2": (255, 255, 255),
        "outline_color": (0, 0, 0),
        "outline_w": 7
    },
    {
        "id": "06",
        "name": "Minimal Dark Capsule Pill",
        "badge": "สไตล์กล่องแคปซูลมน",
        "badge_color": (160, 240, 160, 255),
        "desc": "ตัวหนังสือบนกล่องพื้นหลังสีดำกึ่งโปร่งใส ช่วยให้อ่านออก 100% บนทุกวิดีโอ",
        "sample_line1": "สั่งซื้อวันนี้ ส่งฟรี",
        "sample_line2": "มีรับประกัน 1 ปีเต็ม",
        "font_file": "Mitr-Medium.ttf",
        "font_size": 42,
        "style_type": "pill_box",
        "sub_color1": (255, 255, 255),
        "sub_color2": (255, 240, 120),
        "outline_color": (0, 0, 0),
        "outline_w": 0
    }
]

# Layout: 2 Columns x 3 Rows
card_w = 770
card_h = 600
start_x = 85
gap_x = 90
start_y = 295
gap_y = 55

for idx, card in enumerate(CARDS):
    col = idx % 2
    row = idx // 2
    cx = start_x + (col * (card_w + gap_x))
    cy = start_y + (row * (card_h + gap_y))
    
    # 1. Glass Card Background
    card_bg = Image.new("RGBA", (card_w, card_h), (20, 27, 44, 210))
    cdraw = ImageDraw.Draw(card_bg)
    cdraw.rounded_rectangle([0, 0, card_w, card_h], radius=24, outline=(255, 255, 255, 30), width=2)
    
    # Number badge
    cdraw.ellipse([24, 22, 68, 66], fill=(254, 44, 85, 40), outline=(254, 44, 85, 180), width=2)
    n_bbox = num_font.getbbox(card["id"])
    cdraw.text((24 + int((44 - (n_bbox[2] - n_bbox[0])) / 2), 22 + int((44 - (n_bbox[3] - n_bbox[1])) / 2) - 2), card["id"], font=num_font, fill=(255, 255, 255))
    
    # Title
    cdraw.text((84, 24), card["name"], font=card_title_font, fill=(255, 255, 255))
    
    # Category Badge on Right
    b_font = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-SemiBold.ttf"), 17)
    b_bbox = b_font.getbbox(card["badge"])
    bw = b_bbox[2] - b_bbox[0] + 20
    bh = b_bbox[3] - b_bbox[1] + 10
    bx = card_w - bw - 24
    by = 26
    cdraw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=(card["badge_color"][0], card["badge_color"][1], card["badge_color"][2], 30), outline=card["badge_color"], width=1)
    cdraw.text((bx + 10, by + 3), card["badge"], font=b_font, fill=card["badge_color"])
    
    # Description
    cdraw.text((26, 82), card["desc"], font=desc_font, fill=(165, 180, 205))
    
    # Preview Window (Simulated TikTok Video Frame Box)
    preview_box_y = 136
    preview_box_h = 420
    cdraw.rounded_rectangle([18, preview_box_y, card_w - 18, preview_box_y + preview_box_h], radius=18, fill=(10, 14, 24, 250), outline=(255, 255, 255, 18), width=1)
    
    # Draw simulated studio grid lines
    for gy in range(preview_box_y + 45, preview_box_y + preview_box_h - 40, 50):
        cdraw.line([(32, gy), (card_w - 32, gy)], fill=(255, 255, 255, 8), width=1)
    
    # Render Subtitle Sample inside preview box (2 Lines for perfect balance)
    s_font = ImageFont.truetype(str(FONTS_DIR / card["font_file"]), card["font_size"])
    
    l1 = card["sample_line1"]
    l2 = card["sample_line2"]
    
    bbox1 = s_font.getbbox(l1)
    w1 = bbox1[2] - bbox1[0]
    h1 = bbox1[3] - bbox1[1]
    
    bbox2 = s_font.getbbox(l2)
    w2 = bbox2[2] - bbox2[0]
    h2 = bbox2[3] - bbox2[1]
    
    line_gap = 26
    if card["style_type"] == "pill_box":
        line_gap = 42

    total_text_h = h1 + line_gap + h2
    
    center_y = preview_box_y + int((preview_box_h - total_text_h) / 2) - 10
    y1 = center_y
    y2 = center_y + h1 + line_gap
    
    x1 = int((card_w - w1) / 2)
    x2 = int((card_w - w2) / 2)
    
    if card["style_type"] == "pill_box":
        # Draw separate pill backgrounds with clean margins
        pill_pad_x = 26
        pill_pad_y = 12
        
        # Pill 1
        cdraw.rounded_rectangle([x1 - pill_pad_x, y1 - pill_pad_y, x1 + w1 + pill_pad_x, y1 + h1 + pill_pad_y], radius=16, fill=(0, 0, 0, 230), outline=(255, 255, 255, 60), width=1)
        cdraw.text((x1, y1), l1, font=s_font, fill=card["sub_color1"])
        
        # Pill 2
        cdraw.rounded_rectangle([x2 - pill_pad_x, y2 - pill_pad_y, x2 + w2 + pill_pad_x, y2 + h2 + pill_pad_y], radius=16, fill=(0, 0, 0, 230), outline=(255, 255, 255, 60), width=1)
        cdraw.text((x2, y2), l2, font=s_font, fill=card["sub_color2"])
    else:
        # Draw crisp outline
        ow = card["outline_w"]
        for ox in range(-ow, ow + 1):
            for oy in range(-ow, ow + 1):
                if ox != 0 or oy != 0:
                    cdraw.text((x1 + ox, y1 + oy), l1, font=s_font, fill=card["outline_color"])
                    cdraw.text((x2 + ox, y2 + oy), l2, font=s_font, fill=card["outline_color"])
        # Front text
        cdraw.text((x1, y1), l1, font=s_font, fill=card["sub_color1"])
        cdraw.text((x2, y2), l2, font=s_font, fill=card["sub_color2"])
        
    # Label at bottom of preview
    tip_text = "Preview แสดงผลจริงบนวิดีโอ TikTok 9:16 (คมชัดระดับพรีเมียม)"
    tp_bbox = tip_font.getbbox(tip_text)
    cdraw.text((int((card_w - (tp_bbox[2] - tp_bbox[0])) / 2), preview_box_y + preview_box_h - 36), tip_text, font=tip_font, fill=(110, 125, 150))

    base.paste(card_bg, (cx, cy), card_bg)

# Save Master Poster
out_png = OUT_DIR / "thai_typography_showcase.png"
base.save(out_png, "PNG")

# Also copy to artifacts directory
artifact_png = ARTIFACT_DIR / "thai_typography_showcase.png"
base.save(artifact_png, "PNG")

print(f"✓ Showcase Poster regenerated without flaws:\n  - {out_png}\n  - {artifact_png}")

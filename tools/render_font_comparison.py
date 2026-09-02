import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS_DIR = Path("d:/Winona/Programmer/Capcut/02_Assets/Fonts")
ARTIFACTS_DIR = Path("C:/Users/Winon/.gemini/antigravity-ide/brain/27833363-7167-4895-a5f6-9434892b9de9")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# Comparison canvas: 5 columns (or 5 vertical mockup cards)
W, H = 1920, 1080
canvas = Image.new("RGB", (W, H), "#0B0F17")
draw = ImageDraw.Draw(canvas)

# Title Header
try:
    title_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 48)
    sub_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 24)
except Exception:
    title_font = ImageFont.load_default()
    sub_font = ImageFont.load_default()

# Header Background Banner
draw.rectangle([(0, 0), (W, 110)], fill="#0D121F")
draw.line([(0, 110), (W, 110)], fill="#1E293B", width=2)
draw.text((60, 24), "🔥 ตัวอย่างเปรียบเทียบฟอนต์จริง 5 รูปแบบยอดนิยมสำหรับ TikTok & วิดีโอ", fill="#FFFFFF", font=title_font)
draw.text((60, 78), "เรนเดอร์จากไฟล์ฟอนต์จริง (.ttf) • แสดงผลสไตล์ Hook 3 วิ + ซับไตเติลตัดต่อระดับมืออาชีพ", fill="#25F4EE", font=sub_font)

FONT_CONFIGS = [
    {
        "name": "1. Prompt (พร้อมท์)",
        "badge": "โมเดิร์น แบรนด์เนม",
        "badge_bg": "#3B82F6",
        "file": "Prompt-Black.ttf",
        "hook": "ยกระดับชีวิตให้โปร!",
        "body_1": "เครื่องดูดฝุ่นไร้สาย",
        "body_2": "แรงดูดสูง ดีไซน์มินิมอล",
        "style_desc": "อ่านง่าย 100% คลีน สากล",
        "accent": "#60A5FA",
        "bg_gradient": ("#131B2E", "#0B0F17")
    },
    {
        "name": "2. IBM Plex Thai",
        "badge": "เทค ไอที พรีเมียม",
        "badge_bg": "#0D9488",
        "file": "IBMPlexSansThai-Bold.ttf",
        "hook": "Setup โต๊ะคอมระดับ Pro",
        "body_1": "สายชาร์จแม่เหล็ก 66W",
        "body_2": "ชิป E-Marker คุมความร้อน",
        "style_desc": "คมกริบ ไฮเทค เป๊ะทุกองศา",
        "accent": "#2DD4BF",
        "bg_gradient": ("#0F2424", "#0B0F17")
    },
    {
        "name": "3. Kanit (คณิต)",
        "badge": "ตัวหนา TikTok ไวรัล",
        "badge_bg": "#FE2C55",
        "file": "Kanit-Black.ttf",
        "hook": "🔥 อย่าเพิ่งเลื่อนผ่าน!",
        "body_1": "Flash Sale เหลือ 149.-",
        "body_2": "เสียบปึ้ง ติดแน่น ชาร์จไว!",
        "style_desc": "หนา ตัน หยุดนิ้วโป้งสูงสุด",
        "accent": "#FE2C55",
        "bg_gradient": ("#2A111A", "#0B0F17")
    },
    {
        "name": "4. Mitr (มิตร)",
        "badge": "มินิมอล เกาหลี คลีน",
        "badge_bg": "#EC4899",
        "file": "Mitr-SemiBold.ttf",
        "hook": "กู้ผิวโทรมด่วน ✨",
        "body_1": "เซรั่มหน้าฉ่ำโกลว์",
        "body_2": "ซึมไว ล็อคผิวชุ่มชื้น 72ชม.",
        "style_desc": "โค้งมน นุ่มนวล สบายตา",
        "accent": "#F472B6",
        "bg_gradient": ("#251220", "#0B0F17")
    },
    {
        "name": "5. Chakra Petch",
        "badge": "ไซเบอร์ เกมมิ่ง",
        "badge_bg": "#F59E0B",
        "file": "ChakraPetch-Bold.ttf",
        "hook": "⚡ อัปเกรดความแรง",
        "body_1": "คีย์บอร์ดเกมมิ่ง RGB",
        "body_2": "สวิตช์แม่เหล็ก 8000Hz",
        "style_desc": "ทรงเหลี่ยม ตัดมุม ล้ำอนาคต",
        "accent": "#FBBF24",
        "bg_gradient": ("#261D0E", "#0B0F17")
    }
]

card_w = 340
card_h = 880
start_x = 60
start_y = 150
gap = 35

def draw_text_with_outline(draw_obj, pos, text, font, fill_color, outline_color, outline_w=4):
    x, y = pos
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx*dx + dy*dy <= outline_w*outline_w and (dx != 0 or dy != 0):
                draw_obj.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw_obj.text((x, y), text, font=font, fill=fill_color)

for i, cfg in enumerate(FONT_CONFIGS):
    cx = start_x + i * (card_w + gap)
    cy = start_y

    # Card background (Phone Mockup Box)
    card_img = Image.new("RGBA", (card_w, card_h), (18, 24, 38, 255))
    c_draw = ImageDraw.Draw(card_img)

    # Gradient simulated header
    c_draw.rectangle([(0, 0), (card_w, 140)], fill=cfg["bg_gradient"][0])
    c_draw.line([(0, 140), (card_w, 140)], fill=cfg["accent"], width=3)

    # Card Title & Badge
    try:
        f_name_font = ImageFont.truetype(str(FONTS_DIR / cfg["file"]), 24)
        badge_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 14)
        hook_font = ImageFont.truetype(str(FONTS_DIR / cfg["file"]), 28)
        body_font = ImageFont.truetype(str(FONTS_DIR / cfg["file"]), 22)
        desc_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 14)
    except Exception as e:
        print(f"Font load error: {e}")
        f_name_font = title_font
        badge_font = sub_font
        hook_font = title_font
        body_font = sub_font
        desc_font = sub_font

    # Header in card
    c_draw.text((20, 20), cfg["name"], fill="#FFFFFF", font=f_name_font)
    
    # Badge Pill
    c_draw.rectangle([(20, 60), (20 + 170, 90)], fill=cfg["badge_bg"])
    c_draw.text((30, 66), cfg["badge"], fill="#FFFFFF", font=badge_font)
    
    c_draw.text((20, 105), cfg["style_desc"], fill="#94A3B8", font=desc_font)

    # 9:16 Video Frame Simulation inside card
    frame_x, frame_y = 20, 160
    frame_w, frame_h = card_w - 40, 580
    
    # Video Frame Background
    c_draw.rectangle([(frame_x, frame_y), (frame_x + frame_w, frame_y + frame_h)], fill="#05070B", outline="#334155", width=2)
    
    # Grid lines / aesthetic BG in video
    for gy in range(frame_y + 40, frame_y + frame_h, 60):
        c_draw.line([(frame_x, gy), (frame_x + frame_w, gy)], fill="#0E1726", width=1)
    
    # Top Hook Subtitle in Video Frame
    hook_bg_y = frame_y + 40
    c_draw.rectangle([(frame_x + 10, hook_bg_y), (frame_x + frame_w - 10, hook_bg_y + 55)], fill="#000000", outline="#25F4EE", width=2)
    draw_text_with_outline(c_draw, (frame_x + 20, hook_bg_y + 10), cfg["hook"], hook_font, "#FFFFFF", "#000000", outline_w=3)

    # Mid Mockup Product Silhouette Box
    c_draw.rectangle([(frame_x + 30, frame_y + 130), (frame_x + frame_w - 30, frame_y + 350)], fill="#111827", outline="#1F2937", width=1)
    c_draw.text((frame_x + 55, frame_y + 225), "📦 [ พื้นหลังวิดีโอ ]", fill="#475569", font=desc_font)

    # Subtitle Micro-bursts at bottom of 9:16 frame
    sub_bg_y = frame_y + 400
    
    # Line 1 (Yellow / Accent Highlight)
    draw_text_with_outline(c_draw, (frame_x + 25, sub_bg_y), cfg["body_1"], body_font, "#FFDF00", "#000000", outline_w=4)
    
    # Line 2 (White with sharp stroke)
    draw_text_with_outline(c_draw, (frame_x + 20, sub_bg_y + 45), cfg["body_2"], body_font, "#FFFFFF", "#000000", outline_w=4)

    # Bottom Call to Action Badge
    cta_y = frame_y + 510
    c_draw.rectangle([(frame_x + 20, cta_y), (frame_x + frame_w - 20, cta_y + 45)], fill="#FE2C55")
    c_draw.text((frame_x + 40, cta_y + 10), "🛒 จิ้มตะกร้าซ้ายล่าง", fill="#FFFFFF", font=f_name_font)

    # Card Footer Info
    c_draw.text((20, 760), "📌 เหมาะสำหรับ:", fill="#CBD5E1", font=badge_font)
    if i == 0:
        c_draw.text((20, 790), "• เครื่องใช้ไฟฟ้า / สินค้าทางการ\n• รีวิวสเปกคลีนตา สไตล์สากล", fill="#94A3B8", font=desc_font)
    elif i == 1:
        c_draw.text((20, 790), "• แกดเจ็ต / ไอที / โต๊ะคอม\n• คอนเทนต์ผู้เชี่ยวชาญ เทคโนโลยี", fill="#94A3B8", font=desc_font)
    elif i == 2:
        c_draw.text((20, 790), "• ป้ายยา Flash Sale / ด่วน 15 วิ\n• เน้นหยุดนิ้วโป้ง ยอดวิวไวรัล", fill="#94A3B8", font=desc_font)
    elif i == 3:
        c_draw.text((20, 790), "• สกินแคร์ / เสื้อผ้าแฟชั่น / คาเฟ่\n• Vlogger สบายตา สไตล์เกาหลี", fill="#94A3B8", font=desc_font)
    elif i == 4:
        c_draw.text((20, 790), "• เกมมิ่ง / สายลุย / รถยนต์\n• กราฟิกทรงเหลี่ยม ไฮเทคล้ำยุค", fill="#94A3B8", font=desc_font)

    # Paste Card onto Main Canvas
    canvas.paste(card_img, (cx, cy))

# Save output image
out_file = ARTIFACTS_DIR / "font_comparison_real_mockup.png"
canvas.save(str(out_file), quality=95)
print(f"Saved comparison to: {out_file}")

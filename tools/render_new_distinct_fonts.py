import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path("d:/Winona/Programmer/Capcut/02_Assets/Fonts")
ARTIFACTS_DIR = Path("C:/Users/Winon/.gemini/antigravity-ide/brain/27833363-7167-4895-a5f6-9434892b9de9")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

NEW_SHOWCASE = [
    {
        "id": "anuphan",
        "name": "1. Anuphan (อนุพันธ์)",
        "badge": "💎 Neo-Grotesque ทันสมัยยุค 2026",
        "file": "Anuphan-Bold.ttf",
        "hook": "🚀 สเปกแรง นวัตกรรมล้ำอนาคต",
        "sample": "คมกริบ แน่น ทันสมัย สไตล์สตาร์ทอัพ Silicon Valley",
        "accent": "#38BDF8",
        "tag": "โมเดิร์น ไฮเอนด์"
    },
    {
        "id": "sarabun",
        "name": "2. Sarabun (สารบรรณ)",
        "badge": "🏛️ มีหัว คลาสสิก เป็นทางการสูง",
        "file": "Sarabun-Bold.ttf",
        "hook": "📜 มาตรฐานแห่งความน่าเชื่อถือ",
        "sample": "ตัวพิมพ์มีหัว คลีน นิ่ง อ่านง่าย 100% สไตล์องค์กรใหญ่",
        "accent": "#10B981",
        "tag": "ทางการ น่าเชื่อถือ"
    },
    {
        "id": "krub",
        "name": "3. Krub (ครับ)",
        "badge": "🏢 เรขาคณิต สไตล์สถาปัตยกรรม",
        "file": "Krub-Bold.ttf",
        "hook": "✨ ดีไซน์เรียบหรู สัมผัสความโปร่ง",
        "sample": "ทรงกลมเรขาคณิต เรียบเท่ สไตล์คอนโดหรู & Luxury Living",
        "accent": "#A855F7",
        "tag": "มินิมอล หรูหรา"
    },
    {
        "id": "mali",
        "name": "4. Mali (มะลิ)",
        "badge": "🧸 ลายมือน่ารัก การ์ตูน ขี้เล่น",
        "file": "Mali-Bold.ttf",
        "hook": "🎀 น้อนนนน น่ารักจนใจเจ็บ!",
        "sample": "ลายมือน่ารัก มีหัวกลม เป็นกันเอง สไตล์สินค้าสัตว์เลี้ยง/แม่และเด็ก",
        "accent": "#F472B6",
        "tag": "น่ารัก เป็นกันเอง"
    },
    {
        "id": "itim",
        "name": "5. Itim (ไอติม)",
        "badge": "🍧 คาเฟ่ วัยรุ่น ขนมหวาน สดใส",
        "file": "Itim-Regular.ttf",
        "hook": "🍓 อร่อยสดชื่น หวานละมุนลิ้น",
        "sample": "ลายมือวัยรุ่น สดใส มีชีวิตชีวา สไตล์ร้านอาหาร ขนม คาเฟ่",
        "accent": "#FB923C",
        "tag": "วัยรุ่น คาเฟ่"
    },
    {
        "id": "chonburi",
        "name": "6. Chonburi (ชลบุรี)",
        "badge": "👑 Luxury แฟชั่น วินเทจ นิตยสาร",
        "file": "Chonburi-Regular.ttf",
        "hook": "💎 เสน่ห์อันหรูหราระดับ Masterpiece",
        "sample": "ฟอนต์มีเชิง (Serif) หนาบางคมชัด สไตล์ Vogue / แบรนด์เนม / น้ำหอม",
        "accent": "#FBBF24",
        "tag": "วินเทจ ไฮแฟชั่น"
    },
    {
        "id": "baijamjuree",
        "name": "7. Bai Jamjuree (จามจุรี)",
        "badge": "🏎️ สปอร์ต โฉบเฉี่ยว ไฮสปีด",
        "file": "BaiJamjuree-Bold.ttf",
        "hook": "⚡ ทะยานสู่ความเร็วขั้นสุด!",
        "sample": "ทรงกึ่งเหลี่ยม โฉบเฉี่ยว ดุดัน สไตล์แต่งรถ มอเตอร์สปอร์ต ฟิตเนส",
        "accent": "#EF4444",
        "tag": "สปอร์ต ไฮสปีด"
    },
    {
        "id": "pridi",
        "name": "8. Pridi (ปรีดี)",
        "badge": "📖 บทความพรีเมียม สไตล์ Editorial",
        "file": "Pridi-Bold.ttf",
        "hook": "🖋️ คุณค่าเหนือกาลเวลา ถ่ายทอดเรื่องราว",
        "sample": "กึ่งทางการ มีเชิงอ่อนๆ ดูอบอุ่น สไตล์หนังสือพิมพ์และพอดแคสต์คุณภาพ",
        "accent": "#6EE7B7",
        "tag": "Editorial พรีเมียม"
    }
]

W, H = 1920, 1080
canvas = Image.new("RGB", (W, H), "#07090E")
draw = ImageDraw.Draw(canvas)

# Header
draw.rectangle([(0, 0), (W, 100)], fill="#0D121F")
draw.line([(0, 100), (W, 100)], fill="#1E293B", width=2)

try:
    h1_f = ImageFont.truetype(str(FONTS_DIR / "Anuphan-Bold.ttf"), 36)
    sub_f = ImageFont.truetype(str(FONTS_DIR / "Anuphan-Bold.ttf"), 18)
except Exception:
    h1_f = ImageFont.load_default()
    sub_f = ImageFont.load_default()

draw.text((50, 20), "✨ รวม 8 ฟอนต์ไทยดีไซน์ใหม่ที่ฉีกแนว (New Distinct Thai Typography Showcase)", fill="#FFFFFF", font=h1_f)
draw.text((50, 65), "เรนเดอร์สดจากไฟล์ .ttf จริง • ครอบคลุมตั้งแต่ สตาร์ทอัพ, มีหัวทางการ, ลายมือน่ารัก, แฟชั่นวินเทจ, ไปจนถึงสปอร์ตซิ่ง", fill="#25F4EE", font=sub_f)

# 2 Columns x 4 Rows
card_w = 880
card_h = 210
start_x = 50
start_y = 125
gap_x = 60
gap_y = 20

def draw_text_with_outline(draw_obj, pos, text, font, fill_color, outline_color, outline_w=3):
    x, y = pos
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx*dx + dy*dy <= outline_w*outline_w and (dx != 0 or dy != 0):
                draw_obj.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw_obj.text((x, y), text, font=font, fill=fill_color)

for i, item in enumerate(NEW_SHOWCASE):
    col = i % 2
    row = i // 2
    cx = start_x + col * (card_w + gap_x)
    cy = start_y + row * (card_h + gap_y)

    # Card box
    draw.rectangle([(cx, cy), (cx + card_w, cy + card_h)], fill="#0D111A", outline="#1E293B", width=1)
    draw.line([(cx, cy), (cx, cy + card_h)], fill=item["accent"], width=5)

    # Fonts
    try:
        f_title = ImageFont.truetype(str(FONTS_DIR / item["file"]), 24)
        f_hook = ImageFont.truetype(str(FONTS_DIR / item["file"]), 30)
        f_body = ImageFont.truetype(str(FONTS_DIR / item["file"]), 18)
        f_tag = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 12)
    except Exception as e:
        print(f"Font load error for {item['id']}: {e}")
        f_title = f_hook = f_body = f_tag = h1_f

    # Header Row in card
    draw.text((cx + 20, cy + 15), item["name"], fill="#FFFFFF", font=f_title)
    
    # Badge
    draw.rectangle([(cx + card_w - 240, cy + 12), (cx + card_w - 15, cy + 38)], fill="#1E293B")
    draw.text((cx + card_w - 230, cy + 16), item["badge"], fill=item["accent"], font=f_tag)

    # Hook Display (Big Sample)
    hook_box_y = cy + 55
    draw.rectangle([(cx + 20, hook_box_y), (cx + card_w - 20, hook_box_y + 60)], fill="#05070B", outline="#334155", width=1)
    draw_text_with_outline(draw, (cx + 35, hook_box_y + 12), item["hook"], f_hook, "#FFFFFF", "#000000", outline_w=3)

    # Subtitle / Description text
    draw.text((cx + 20, cy + 130), f"📌 ตัวอย่างข้อความ: {item['sample']}", fill="#CBD5E1", font=f_body)
    draw.text((cx + 20, cy + 175), f"💡 เหมาะสำหรับ: {item['tag']}", fill=item["accent"], font=f_tag)

out_file = ARTIFACTS_DIR / "new_distinct_fonts_board.png"
canvas.save(str(out_file), quality=95)
print(f"Saved New Distinct Fonts Board: {out_file}")

# Also render 4 Distinct UI screen mocks
W_UI, H_UI = 1600, 1000
ui_samples = [
    ("Anuphan-Bold.ttf", "Anuphan — สตาร์ทอัพ คมกริบ ไฮเทค", "ui_preview_anuphan.png"),
    ("Sarabun-Bold.ttf", "Sarabun — มีหัว คลีน นิ่ง เป็นทางการ", "ui_preview_sarabun.png"),
    ("Krub-Bold.ttf", "Krub — โมเดิร์น เรขาคณิต หรูหรา", "ui_preview_krub.png"),
    ("Mali-Bold.ttf", "Mali — ลายมือน่ารัก การ์ตูน อบอุ่น", "ui_preview_mali.png"),
]

for font_f, desc_label, out_name in ui_samples:
    c_ui = Image.new("RGB", (W_UI, H_UI), "#07090E")
    d_ui = ImageDraw.Draw(c_ui)

    f_u_h1 = ImageFont.truetype(str(FONTS_DIR / font_f), 22)
    f_u_b = ImageFont.truetype(str(FONTS_DIR / font_f), 14)
    f_u_body = ImageFont.truetype(str(FONTS_DIR / font_f), 13)

    # Topbar
    d_ui.rectangle([(0, 0), (W_UI, 60)], fill="#0D111A")
    d_ui.rectangle([(20, 12), (56, 48)], fill="#FE2C55")
    d_ui.text((68, 18), "CapCut Studio Pro", fill="#FFFFFF", font=f_u_h1)
    d_ui.rectangle([(340, 15), (750, 45)], fill="#131B2E", outline="#25F4EE", width=2)
    d_ui.text((355, 20), f"🎨 ฟอนต์หน้าโปรแกรม: {desc_label}", fill="#FFFFFF", font=f_u_b)

    # Sidebar
    d_ui.rectangle([(0, 60), (230, H_UI)], fill="#090D15")
    navs = ["🚀 1. สินค้า → คลิป", "📊 2. แทร็กเกอร์ 5 เฟส", "✨ 3. 1-Click Studio", "📁 4. Export Gallery"]
    for idx, n in enumerate(navs):
        ny = 80 + idx * 46
        if idx == 0:
            d_ui.rectangle([(10, ny), (220, ny + 38)], fill="#162032", outline="#25F4EE", width=1)
            d_ui.text((22, ny + 8), n, fill="#FFFFFF", font=f_u_b)
        else:
            d_ui.text((22, ny + 8), n, fill="#64748B", font=f_u_body)

    # Content
    d_ui.rectangle([(260, 85), (W_UI - 30, 200)], fill="#0D121F", outline="#1E293B", width=1)
    d_ui.text((290, 105), "Esseger สายชาร์จแม่เหล็ก 66W หมุน 360 องศา ชาร์จเร็ว พร้อมไฟ LED", fill="#FFFFFF", font=f_u_h1)
    d_ui.text((290, 145), "จุดเด่น: แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต สายถักไนลอนทนทาน", fill="#94A3B8", font=f_u_body)

    # Angle Card Grid
    d_ui.rectangle([(260, 220), (W_UI - 30, 420)], fill="#0D121F", outline="#1E293B", width=1)
    d_ui.text((290, 240), "💡 สคริปต์ 4 สไตล์การตลาดที่พร้อมใช้งาน:", fill="#25F4EE", font=f_u_b)
    d_ui.text((290, 280), "1. สไตล์ Flash Sale: อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก ลดเหลือ 149.- วันนี้วันเดียว", fill="#FFFFFF", font=f_u_body)
    d_ui.text((290, 320), "2. สไตล์แก้ Pain Point: สายชาร์จพังบ่อย เสียบยากในที่มืด ต้องลองดูดปึ้งติดทันที", fill="#FFFFFF", font=f_u_body)
    d_ui.text((290, 360), "3. สไตล์เกมมิ่งสเปกเทพ: ชาร์จไว 66W เล่นเกมไม่ติดมือ ข้อต่อหมุนอิสระ 360 องศา", fill="#FFFFFF", font=f_u_body)

    out_p = ARTIFACTS_DIR / out_name
    c_ui.save(str(out_p), quality=95)
    print(f"Saved {out_name}")

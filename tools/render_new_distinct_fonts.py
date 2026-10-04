import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "font_artifacts"

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
        "badge": "✨ โมเดิร์น เรขาคณิต หรูหรา",
        "file": "Krub-Bold.ttf",
        "hook": "💎 หรูหรา เรียบหรู ทุกองศา",
        "sample": "ทรงโค้งมนกว้าง ดีไซน์พรีเมียม สไตล์แบรนด์นาฬิกาและรถยนต์หรู",
        "accent": "#A78BFA",
        "tag": "ลักชัวรี พรีเมียม"
    },
    {
        "id": "mali",
        "name": "4. Mali (มะลิ)",
        "badge": "🎨 ลายมือน่ารัก มีเสน่ห์ อบอุ่น",
        "file": "Mali-Bold.ttf",
        "hook": "🧸 ป้ายยาน้องใหม่ น่ารักเกินปุยมุ้ย!",
        "sample": "ลายมือธรรมชาติ ตัวหนาอ่านง่าย เป็นกันเอง สไตล์ของใช้น่ารัก & ขนม",
        "accent": "#F472B6",
        "tag": "น่ารัก สบายตา"
    },
    {
        "id": "itim",
        "name": "5. Itim (ไอติม)",
        "badge": "🍦 สดใส ซุกซน ฟีลคาเฟ่",
        "file": "Itim-Regular.ttf",
        "hook": "🥤 พิกัดคาเฟ่ลับ ห้ามพลาด!",
        "sample": "ลายมือนุ่มฟู มีสไตล์ เป็นธรรมชาติ สไตล์รีวิวเครื่องดื่มและของหวาน",
        "accent": "#FBBF24",
        "tag": "คาเฟ่ สดใส"
    },
    {
        "id": "chonburi",
        "name": "6. Chonburi (ชลบุรี)",
        "badge": "👑 ย้อนยุค วินเทจ อลังการ",
        "file": "Chonburi-Regular.ttf",
        "hook": "🏆 ตำนานความอร่อย สืบทอด 50 ปี",
        "sample": "ตัวอักษรมีหัวพริ้วไหว วินเทจร่วมสมัย สไตล์อาหารไทย ของฝากพรีเมียม",
        "accent": "#FB923C",
        "tag": "วินเทจ พรีเมียม"
    },
    {
        "id": "baijamjuree",
        "name": "7. Bai Jamjuree (จามจุรี)",
        "badge": "⚙️ ไฮเทค กึ่งทางการ สไตล์ไอที",
        "file": "BaiJamjuree-Bold.ttf",
        "hook": "⚡ เทคโนโลยีแห่งปี 2026",
        "sample": "ตัวอักษรมีหัวผสมทรงเหลี่ยม อ่านง่ายมาก สไตล์บล็อกเทคและรีวิวฮาร์ดแวร์",
        "accent": "#2DD4BF",
        "tag": "เทคโนโลยี ไอที"
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


def draw_text_with_outline(draw_obj, pos, text, font, fill_color, outline_color, outline_w=4):
    x, y = pos
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx * dx + dy * dy <= outline_w * outline_w and (dx != 0 or dy != 0):
                draw_obj.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw_obj.text((x, y), text, font=font, fill=fill_color)


def render_new_distinct_fonts(output_dir: Path = None):
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    W, H = 1920, 1080
    canvas = Image.new("RGB", (W, H), "#07090E")
    draw = ImageDraw.Draw(canvas)

    try:
        h1_f = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 44)
        sub_f = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 22)
    except Exception:
        h1_f = ImageFont.load_default()
        sub_f = ImageFont.load_default()

    # Header
    draw.rectangle([(0, 0), (W, 110)], fill="#0D121F")
    draw.line([(0, 110), (W, 110)], fill="#1E293B", width=2)
    draw.text((60, 24), "🎨 ชุดคลัง 8 ฟอนต์ภาษาไทยใหม่ล่าสุดที่มีเอกลักษณ์เฉพาะตัวสูง (Distinct Typography)", fill="#FFFFFF", font=h1_f)
    draw.text((60, 78), "ดาวน์โหลดและติดตั้งในโปรเจกต์พร้อมใช้งานทันที • ครอบคลุมสไตล์ Neo-Grotesque, Luxury, น่ารัก, วินเทจ และ Editorial", fill="#38BDF8", font=sub_f)

    # Grid: 2 rows x 4 columns
    cols, rows = 4, 2
    card_w = 425
    card_h = 420
    start_x = 60
    start_y = 150
    gap_x = 30
    gap_y = 40

    for idx, item in enumerate(NEW_SHOWCASE):
        r = idx // cols
        c = idx % cols
        cx = start_x + c * (card_w + gap_x)
        cy = start_y + r * (card_h + gap_y)

        # Card container
        draw.rectangle([(cx, cy), (cx + card_w, cy + card_h)], fill="#0D121F", outline="#1E293B", width=2)
        draw.rectangle([(cx, cy), (cx + card_w, cy + 50)], fill="#162032")
        draw.line([(cx, cy + 50), (cx + card_w, cy + 50)], fill=item["accent"], width=2)

        try:
            f_title = ImageFont.truetype(str(FONTS_DIR / item["file"]), 24)
            f_hook = ImageFont.truetype(str(FONTS_DIR / item["file"]), 30)
            f_body = ImageFont.truetype(str(FONTS_DIR / item["file"]), 18)
            f_tag = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 12)
        except Exception:
            f_title = f_hook = f_body = f_tag = h1_f

        draw.text((cx + 20, cy + 15), item["name"], fill="#FFFFFF", font=f_title)
        draw.rectangle([(cx + card_w - 240, cy + 12), (cx + card_w - 15, cy + 38)], fill="#1E293B")
        draw.text((cx + card_w - 230, cy + 16), item["badge"], fill=item["accent"], font=f_tag)

        hook_box_y = cy + 55
        draw.rectangle([(cx + 20, hook_box_y), (cx + card_w - 20, hook_box_y + 60)], fill="#05070B", outline="#334155", width=1)
        draw_text_with_outline(draw, (cx + 35, hook_box_y + 12), item["hook"], f_hook, "#FFFFFF", "#000000", outline_w=3)

        draw.text((cx + 20, cy + 130), f"📌 ตัวอย่างข้อความ: {item['sample']}", fill="#CBD5E1", font=f_body)
        draw.text((cx + 20, cy + 175), f"💡 เหมาะสำหรับ: {item['tag']}", fill=item["accent"], font=f_tag)

    out_file = output_dir / "new_distinct_fonts_board.png"
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
        c_ui = Image.new("RGB", (W_UI, H_UI), "#080B12")
        d_ui = ImageDraw.Draw(c_ui)

        try:
            f_u_h1 = ImageFont.truetype(str(FONTS_DIR / font_f), 34)
            f_u_b = ImageFont.truetype(str(FONTS_DIR / font_f), 22)
            f_u_body = ImageFont.truetype(str(FONTS_DIR / font_f), 18)
        except Exception:
            f_u_h1 = f_u_b = f_u_body = h1_f

        d_ui.rectangle([(0, 0), (W_UI, 65)], fill="#0D121F")
        d_ui.line([(0, 65), (W_UI, 65)], fill="#1E293B", width=1)
        d_ui.text((30, 18), f"OmniCut Pro Studio • แสดงผล UI สดด้วยฟอนต์: {desc_label}", fill="#FFFFFF", font=f_u_h1)

        d_ui.rectangle([(0, 65), (240, H_UI)], fill="#0A0E18")
        d_ui.line([(240, 65), (240, H_UI)], fill="#1E293B", width=1)

        nav_items = ["คลังสินค้า", "แคตตาล็อก B-Roll", "สคริปต์รีวิว", "ตัดต่อ 9:16", "ตั้งค่าระบบ"]
        for idx, n in enumerate(nav_items):
            ny = 90 + idx * 50
            if idx == 0:
                d_ui.rectangle([(10, ny), (220, ny + 38)], fill="#162032", outline="#25F4EE", width=1)
                d_ui.text((22, ny + 8), n, fill="#FFFFFF", font=f_u_b)
            else:
                d_ui.text((22, ny + 8), n, fill="#64748B", font=f_u_body)

        d_ui.rectangle([(260, 85), (W_UI - 30, 200)], fill="#0D121F", outline="#1E293B", width=1)
        d_ui.text((290, 105), "Esseger สายชาร์จแม่เหล็ก 66W หมุน 360 องศา ชาร์จเร็ว พร้อมไฟ LED", fill="#FFFFFF", font=f_u_h1)
        d_ui.text((290, 145), "จุดเด่น: แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต สายถักไนลอนทนทาน", fill="#94A3B8", font=f_u_body)

        d_ui.rectangle([(260, 220), (W_UI - 30, 420)], fill="#0D121F", outline="#1E293B", width=1)
        d_ui.text((290, 240), "💡 สคริปต์ 4 สไตล์การตลาดที่พร้อมใช้งาน:", fill="#25F4EE", font=f_u_b)
        d_ui.text((290, 280), "1. สไตล์ Flash Sale: อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก ลดเหลือ 149.- วันนี้วันเดียว", fill="#FFFFFF", font=f_u_body)
        d_ui.text((290, 320), "2. สไตล์แก้ Pain Point: สายชาร์จพังบ่อย เสียบยากในที่มืด ต้องลองดูดปึ้งติดทันที", fill="#FFFFFF", font=f_u_body)
        d_ui.text((290, 360), "3. สไตล์เกมมิ่งสเปกเทพ: ชาร์จไว 66W เล่นเกมไม่ติดมือ ข้อต่อหมุนอิสระ 360 องศา", fill="#FFFFFF", font=f_u_body)

        out_p = output_dir / out_name
        c_ui.save(str(out_p), quality=95)
        print(f"Saved {out_name}")


if __name__ == '__main__':
    render_new_distinct_fonts()

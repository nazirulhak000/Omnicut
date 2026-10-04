import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "font_artifacts"

UI_CONFIGS = [
    {
        "id": "ui_preview_prompt",
        "font_name": "Prompt (พร้อมท์)",
        "vibe": "โมเดิร์น คลีน สบายตา สมดุลสูงสุด (มาตรฐานแอปอย่าง SCB / Robinhood)",
        "font_bold": "Prompt-Bold.ttf",
        "font_regular": "Prompt-Bold.ttf",  # using bold/medium
        "accent": "#25F4EE",
        "accent_text": "Prompt UI",
    },
    {
        "id": "ui_preview_ibm_plex",
        "font_name": "IBM Plex Sans Thai",
        "vibe": "เทคโนโลยี คมกริบ ระเบียบสูง สไตล์ Dev Tools (Linear / Vercel)",
        "font_bold": "IBMPlexSansThai-Bold.ttf",
        "font_regular": "IBMPlexSansThai-SemiBold.ttf",
        "accent": "#38BDF8",
        "accent_text": "IBM Plex UI",
    },
    {
        "id": "ui_preview_kanit",
        "font_name": "Kanit (คณิต)",
        "vibe": "ตัวหนา มีพลัง สนุก เข้าถึงง่าย (สไตล์ Shopee / TikTok Creator Studio)",
        "font_bold": "Kanit-Bold.ttf",
        "font_regular": "Kanit-Bold.ttf",
        "accent": "#FE2C55",
        "accent_text": "Kanit UI",
    },
    {
        "id": "ui_preview_mitr",
        "font_name": "Mitr (มิตร)",
        "vibe": "โค้งมน นุ่มนวล สบายตา เป็นมิตร ไม่แข็งกระด้าง (สไตล์ Wongnai / Lifestyle)",
        "font_bold": "Mitr-SemiBold.ttf",
        "font_regular": "Mitr-Medium.ttf",
        "accent": "#F472B6",
        "accent_text": "Mitr UI",
    }
]


def render_ui_font_comparison(output_dir: Path = None):
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    W, H = 1600, 1000

    for cfg in UI_CONFIGS:
        canvas = Image.new("RGB", (W, H), "#07090E")
        draw = ImageDraw.Draw(canvas)

        # Fonts
        try:
            f_h1 = ImageFont.truetype(str(FONTS_DIR / cfg["font_bold"]), 22)
            f_h2 = ImageFont.truetype(str(FONTS_DIR / cfg["font_bold"]), 17)
            f_body_b = ImageFont.truetype(str(FONTS_DIR / cfg["font_bold"]), 14)
            f_body = ImageFont.truetype(str(FONTS_DIR / cfg["font_regular"]), 13)
            f_caption = ImageFont.truetype(str(FONTS_DIR / cfg["font_regular"]), 11)
            f_mono = ImageFont.truetype(str(FONTS_DIR / "IBMPlexSansThai-Medium.ttf"), 11)
        except Exception:
            f_h1 = f_h2 = f_body_b = f_body = f_caption = f_mono = ImageFont.load_default()

        # 1. TOPBAR
        draw.rectangle([(0, 0), (W, 60)], fill="#0D111A")
        draw.line([(0, 60), (W, 60)], fill="#1E293B", width=1)

        draw.rectangle([(20, 12), (56, 48)], fill="#FE2C55")
        draw.text((68, 18), "CapCut Studio Pro", fill="#FFFFFF", font=f_h1)
        draw.rectangle([(245, 20), (315, 40)], fill="#1E293B")
        draw.text((255, 22), "v2.5 AI", fill="#25F4EE", font=f_mono)

        draw.rectangle([(340, 15), (720, 45)], fill="#131B2E", outline=cfg["accent"], width=2)
        draw.text((355, 20), f"🎨 ฟอนต์หน้าโปรแกรม: {cfg['font_name']}", fill="#FFFFFF", font=f_body_b)

        draw.rectangle([(W - 240, 15), (W - 140, 45)], fill="#064E3B", outline="#059669", width=1)
        draw.ellipse([(W - 225, 26), (W - 217, 34)], fill="#10B981")
        draw.text((W - 205, 21), "ระบบ Online", fill="#A7F3D0", font=f_body_b)

        draw.rectangle([(W - 125, 15), (W - 25, 45)], fill="#1E293B")
        draw.text((W - 110, 22), "🎬 12 คลิป", fill="#FFFFFF", font=f_body)

        # 2. SIDEBAR
        sb_w = 230
        draw.rectangle([(0, 60), (sb_w, H)], fill="#090D15")
        draw.line([(sb_w, 60), (sb_w, H)], fill="#1E293B", width=1)

        nav_items = [
            ("🚀", "1. สินค้า → คลิป", True),
            ("📊", "2. แทร็กเกอร์ 5 เฟส", False),
            ("✨", "3. 1-Click Studio", False),
            ("✂️", "4. ตัดต่อมือ (Manual)", False),
            ("📁", "5. Export Gallery", False),
            ("⚡", "6. AI ถอดซับ (SRT)", False),
            ("💡", "7. AI Script Lab", False),
            ("⚙️", "8. Assets & System", False),
        ]

        for idx, (icon, label, active) in enumerate(nav_items):
            ny = 80 + idx * 46
            if active:
                draw.rectangle([(10, ny), (sb_w - 10, ny + 38)], fill="#162032", outline=cfg["accent"], width=1)
                draw.text((22, ny + 8), f"{icon}  {label}", fill="#FFFFFF", font=f_body_b)
            else:
                draw.text((22, ny + 8), f"{icon}  {label}", fill="#64748B", font=f_body)

        # 3. MAIN CONTENT AREA
        mx = sb_w + 30
        my = 85
        mw = W - sb_w - 60

        # Header Card
        draw.rectangle([(mx, my), (mx + mw, my + 80)], fill="#0D121F", outline="#1E293B", width=1)

        draw.rectangle([(mx + 15, my + 15), (mx + 65, my + 65)], fill="#1E293B", outline=cfg["accent"], width=1)
        draw.text((mx + 28, my + 24), "📦", font=f_h1)

        draw.text((mx + 80, my + 16), "เลือกสินค้าในระบบ (4 รายการ):", fill="#94A3B8", font=f_caption)
        draw.rectangle([(mx + 80, my + 38), (mx + 500, my + 68)], fill="#07090E", outline="#334155", width=1)
        draw.text((mx + 95, my + 44), "Esseger สายชาร์จแม่เหล็ก 66W — (3/4 สคริปต์เสร็จ)", fill="#FFFFFF", font=f_body_b)

        draw.rectangle([(mx + mw - 220, my + 22), (mx + mw - 15, my + 58)], fill="#FE2C55")
        draw.text((mx + mw - 200, my + 30), "+ วิเคราะห์สินค้าใหม่", fill="#FFFFFF", font=f_body_b)

        # Product Master Details Card
        p_card_y = my + 100
        draw.rectangle([(mx, p_card_y), (mx + mw, p_card_y + 360)], fill="#0D121F", outline="#1E293B", width=1)

        draw.rectangle([(mx + 20, p_card_y + 20), (mx + 115, p_card_y + 44)], fill="#162032", outline="#25F4EE", width=1)
        draw.text((mx + 30, p_card_y + 24), "สินค้าปัจจุบัน", fill="#25F4EE", font=f_caption)

        draw.rectangle([(mx + 125, p_card_y + 20), (mx + 255, p_card_y + 44)], fill="#064E3B")
        draw.text((mx + 135, p_card_y + 24), "ลดพิเศษเหลือ 149.-", fill="#34D399", font=f_caption)

        draw.text((mx + 20, p_card_y + 55), "Esseger สายชาร์จแม่เหล็ก 66W หมุน 360 องศา ชาร์จเร็ว พร้อมไฟ LED", fill="#FFFFFF", font=f_h1)
        draw.text((mx + 20, p_card_y + 90), "จุดเด่น: แม่เหล็กแรงดูดสูง เสียบปึ้ง ติดทันที ชาร์จเร็ว ไม่ทำร้ายแบต สายถักไนลอนทนทาน", fill="#94A3B8", font=f_body)

        angles = [
            ("1. สไตล์ ป้ายยา Flash Sale", "🔥 อย่าเพิ่งเลื่อนผ่าน! สายชาร์จแม่เหล็ก 149 บาท", "💥 ลดราคาด่วน", "#FE2C55"),
            ("2. สไตล์ แก้ปัญหาคนใช้สายพัง", "❌ สายชาร์จพังบ่อย เสียบยากในที่มืด ต้องดูตัวนี้", "💡 แก้ Pain Point", "#38BDF8"),
            ("3. สไตล์ สเปกเทพ สายเกมมิ่ง", "⚡ ชาร์จไว 66W เล่นเกมไม่ติดมือ หมุน 360 องศา", "🚀 รีวิวสเปก", "#F59E0B"),
            ("4. สไตล์ ASMR โชว์เสียบปึ้ง", "✨ ฟังเสียงแม่เหล็กดูดปึ้ง! ชาร์จง่ายแม้หลับตา", "🌸 โชว์ฟังก์ชัน", "#10B981"),
        ]

        grid_y = p_card_y + 130
        gw = (mw - 50) // 2
        gh = 95

        for g_idx, (a_name, a_hook, a_badge, a_color) in enumerate(angles):
            gx = mx + 20 + (g_idx % 2) * (gw + 10)
            gy = grid_y + (g_idx // 2) * (gh + 12)

            draw.rectangle([(gx, gy), (gx + gw, gy + gh)], fill="#090D15", outline="#1E293B", width=1)
            draw.text((gx + 12, gy + 10), a_name, fill="#FFFFFF", font=f_body_b)

            draw.rectangle([(gx + gw - 120, gy + 8), (gx + gw - 12, gy + 28)], fill="#1E293B")
            draw.text((gx + gw - 110, gy + 11), a_badge, fill=a_color, font=f_caption)

            draw.rectangle([(gx + 12, gy + 35), (gx + gw - 12, gy + 62)], fill="#131B2E", outline="#334155", width=1)
            draw.text((gx + 20, gy + 40), a_hook, fill="#25F4EE", font=f_caption)

            draw.rectangle([(gx + gw - 150, gy + 68), (gx + gw - 12, gy + 88)], fill="#FE2C55")
            draw.text((gx + gw - 138, gy + 71), "🎬 ส่งตัดต่อ Studio", fill="#FFFFFF", font=f_caption)

        # 4. STUDIO STEP 3 PREVIEW
        studio_y = p_card_y + 380
        draw.rectangle([(mx, studio_y), (mx + mw, H - 30)], fill="#0D121F", outline="#1E293B", width=1)
        draw.text((mx + 20, studio_y + 16), "⚙️ 1-Click Studio — ขั้นตอนที่ 3: ปรับแต่งเสียงพากย์ AI & แบบฟอนต์", fill="#FFFFFF", font=f_h2)

        draw.rectangle([(mx + 20, studio_y + 50), (mx + mw - 20, studio_y + 85)], fill="#131B2E", outline=cfg["accent"], width=1)
        draw.text((mx + 35, studio_y + 58), f"💡 ข้อดีของฟอนต์นี้บน UI: {cfg['vibe']}", fill="#FFFFFF", font=f_body)

        out_file = output_dir / f"{cfg['id']}.png"
        canvas.save(str(out_file), quality=95)
        print(f"Saved UI Mockup: {out_file}")

    # Combined 2x2 UI Comparison Canvas
    GRID_W, GRID_H = 1920, 1200
    board = Image.new("RGB", (GRID_W, GRID_H), "#05070B")
    b_draw = ImageDraw.Draw(board)

    b_draw.rectangle([(0, 0), (GRID_W, 80)], fill="#0D111A")
    try:
        header_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 28)
        sub_header_font = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 16)
    except Exception:
        header_font = sub_header_font = ImageFont.load_default()

    b_draw.text((40, 16), "🖥️ ภาพตัวอย่างหน้าโปรแกรมจริง (Real Program UI) เปรียบเทียบ 4 ฟอนต์ไทยยอดนิยม", fill="#FFFFFF", font=header_font)
    b_draw.text((40, 50), "แสดงผลจริงของ เมนู, ปุ่มกด, การ์ดข้อมูล, แดชบอร์ด และหน้าจอตัดต่อ 1-Click Studio", fill="#25F4EE", font=sub_header_font)

    qw, qh = 920, 520
    quads = [
        (40, 100, "ui_preview_prompt.png", "1. Prompt — โมเดิร์น คลีน สากล (แนะนำค่าเริ่มต้น)"),
        (960, 100, "ui_preview_ibm_plex.png", "2. IBM Plex Thai — เทคโนโลยี คมกริบ ระเบียบสูง"),
        (40, 640, "ui_preview_kanit.png", "3. Kanit — ตัวหนา มีพลัง สนุก สไตล์ E-Commerce"),
        (960, 640, "ui_preview_mitr.png", "4. Mitr — โค้งมน ละมุน อบอุ่น สไตล์มินิมอล"),
    ]

    for qx, qy, fname, label in quads:
        im_path = output_dir / fname
        if im_path.exists():
            im = Image.open(str(im_path)).resize((qw, qh), Image.Resampling.LANCZOS)
            board.paste(im, (qx, qy))
            b_draw.rectangle([(qx, qy), (qx + qw, qy + 32)], fill="#0D121F")
            b_draw.text((qx + 15, qy + 6), label, fill="#25F4EE", font=sub_header_font)

    board_out = output_dir / "ui_font_comparison_board.png"
    board.save(str(board_out), quality=95)
    print(f"Saved Combined UI Board: {board_out}")


if __name__ == '__main__':
    render_ui_font_comparison()

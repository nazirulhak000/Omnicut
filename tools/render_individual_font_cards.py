import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "font_artifacts"

INDIVIDUAL_CONFIGS = [
    {
        "id": "card_1_prompt",
        "name": "1. Prompt (พร้อมท์)",
        "file": "Prompt-Black.ttf",
        "title": "📐 PROMPT — โมเดิร์น เรขาคณิต",
        "hook": "🔥 ยกระดับการทำงานให้สมบูรณ์แบบ!",
        "line1": "ดีไซน์บางเบา สเปกแรงสะใจ",
        "line2": "พร้อมรับประกันศูนย์ไทย 2 ปีเต็ม",
        "cta": "🛒 สั่งซื้อพร้อมโปรพิเศษวันนี้",
        "accent": "#38BDF8",
        "vibe": "น่าเชื่อถือ คลีน สากล เหมือนแบรนด์ Apple / SCB"
    },
    {
        "id": "card_2_ibm_plex",
        "name": "2. IBM Plex Thai",
        "file": "IBMPlexSansThai-Bold.ttf",
        "title": "💻 IBM PLEX — เทคโนโลยี & ไอทีพรีเมียม",
        "hook": "⚡ Setup โต๊ะคอมระดับ Pro ที่ทุกคนตามหา!",
        "line1": "สายชาร์จแม่เหล็ก 66W ดูดแน่น 360°",
        "line2": "ชิป E-Marker คุมความร้อนได้เสถียรสุดๆ",
        "cta": "🛒 กดดูพิกัดในตะกร้าด่วน",
        "accent": "#2DD4BF",
        "vibe": "คมกริบ ไฮเทค วิศวกรรม คมชัดระดับโปร"
    },
    {
        "id": "card_3_kanit",
        "name": "3. Kanit (คณิต)",
        "file": "Kanit-Black.ttf",
        "title": "💥 KANIT — ตัวหนา TikTok ไวรัล",
        "hook": "🔥 อย่าเพิ่งเลื่อนผ่าน! Flash Sale วันเดียว!",
        "line1": "ลดเหลือ 149.- เสียบปึ้ง ติดทันที!",
        "line2": "ชาร์จเร็ว ไม่ทำร้ายแบต ทนทานมาก",
        "cta": "🛒 จิ้มตะกร้าซ้ายล่างก่อนของหมด!",
        "accent": "#FE2C55",
        "vibe": "ตัวตัน หนา เด้ง พลังหยุดนิ้วโป้งสูงที่สุด"
    },
    {
        "id": "card_4_mitr",
        "name": "4. Mitr (มิตร)",
        "file": "Mitr-SemiBold.ttf",
        "title": "🌸 MITR — มินิมอลเกาหลี สกินแคร์",
        "hook": "✨ กู้ผิวโทรมด่วน! เซรั่มหน้าฉ่ำโกลว์",
        "line1": "เนื้อบางเบา ซึมไว ล็อคผิวฉ่ำ 72 ชม.",
        "line2": "ตื่นมาหน้าใส ผิวอิ่มน้ำ มีออร่าสุดๆ",
        "cta": "🛒 โปร 1 แถม 1 ในตะกร้าด่วน",
        "accent": "#F472B6",
        "vibe": "โค้งมน นุ่มนวล ละมุน สบายตา อบอุ่น"
    },
    {
        "id": "card_5_chakra",
        "name": "5. Chakra Petch",
        "file": "ChakraPetch-Bold.ttf",
        "title": "⚡ CHAKRA PETCH — ไซเบอร์ เกมมิ่ง",
        "hook": "🚀 ปลดล็อคความแรง! คีย์บอร์ด Rapid Trigger",
        "line1": "ตอบสนอง 0.1ms สวิตช์แม่เหล็ก 8000Hz",
        "line2": "ไฟ RGB จัดเต็ม กดมันส์สะใจทุกเกม",
        "cta": "🛒 กดสั่งพร้อมส่งฟรีวันนี้",
        "accent": "#FBBF24",
        "vibe": "ทรงเหลี่ยมตัดมุม ล้ำอนาคต ดุดัน ทรงพลัง"
    }
]


def draw_text_with_outline(draw_obj, pos, text, font, fill_color, outline_color, outline_w=5):
    x, y = pos
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx * dx + dy * dy <= outline_w * outline_w and (dx != 0 or dy != 0):
                draw_obj.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw_obj.text((x, y), text, font=font, fill=fill_color)


def render_individual_font_cards(output_dir: Path = None):
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    W, H = 1080, 1920

    for cfg in INDIVIDUAL_CONFIGS:
        img = Image.new("RGB", (W, H), "#080B12")
        draw = ImageDraw.Draw(img)

        # Background subtle pattern
        for y in range(0, H, 80):
            draw.line([(0, y), (W, y)], fill="#0E1422", width=1)

        # Fonts
        try:
            title_f = ImageFont.truetype(str(FONTS_DIR / cfg["file"]), 52)
            hook_f = ImageFont.truetype(str(FONTS_DIR / cfg["file"]), 58)
            sub_f = ImageFont.truetype(str(FONTS_DIR / cfg["file"]), 50)
            cta_f = ImageFont.truetype(str(FONTS_DIR / cfg["file"]), 44)
            info_f = ImageFont.truetype(str(FONTS_DIR / "Prompt-Bold.ttf"), 30)
        except Exception:
            title_f = ImageFont.load_default()
            hook_f = ImageFont.load_default()
            sub_f = ImageFont.load_default()
            cta_f = ImageFont.load_default()
            info_f = ImageFont.load_default()

        # Header Card Info Banner
        draw.rectangle([(60, 60), (W - 60, 180)], fill="#0F172A", outline=cfg["accent"], width=3)
        draw.text((90, 85), cfg["title"], fill="#FFFFFF", font=title_f)
        draw.text((90, 140), f"อารมณ์: {cfg['vibe']}", fill=cfg["accent"], font=info_f)

        # 9:16 Screen Mockup Frame Border
        draw.rectangle([(60, 220), (W - 60, H - 80)], fill="#05070B", outline="#1E293B", width=4)

        # Hook Banner (Top 3s)
        draw.rectangle([(100, 300), (W - 100, 440)], fill="#000000", outline=cfg["accent"], width=3)
        draw_text_with_outline(draw, (130, 335), cfg["hook"], hook_f, "#FFFFFF", "#000000", outline_w=6)

        # Center Product Video Mock Area
        draw.rectangle([(140, 520), (W - 140, 1200)], fill="#0F1524", outline="#1E293B", width=2)
        draw.text((360, 830), "🎬 [ วิดีโอสินค้า / B-Roll 9:16 ]", fill="#475569", font=info_f)

        # Subtitle Micro-bursts Line 1 (Yellow / Highlight)
        draw_text_with_outline(draw, (140, 1320), cfg["line1"], sub_f, "#FFE600", "#000000", outline_w=7)

        # Subtitle Micro-bursts Line 2 (White with Crisp Stroke)
        draw_text_with_outline(draw, (120, 1420), cfg["line2"], sub_f, "#FFFFFF", "#000000", outline_w=7)

        # Bottom Call to Action
        draw.rectangle([(120, 1600), (W - 120, 1720)], fill="#FE2C55")
        draw_text_with_outline(draw, (230, 1630), cfg["cta"], cta_f, "#FFFFFF", "#000000", outline_w=4)

        out_p = output_dir / f"{cfg['id']}.png"
        img.save(str(out_p), quality=95)
        print(f"Saved {cfg['id']} to {out_p}")


if __name__ == '__main__':
    render_individual_font_cards()

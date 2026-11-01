import pytest
from scripts.product_scraper import (
    _clean_rendered_description,
    _extract_specs_from_text,
    _clean_title,
    _deduplicate_and_filter_images,
    _looks_like_login_page,
    _looks_like_browser_challenge,
)

def test_clean_rendered_description_strips_header_and_footer():
    raw_text = """Search
1 / 9
2 / 9
-75%
฿
599
.10
฿2,399.00
【COD】หูฟังเปิดหู MONSTER AC530 ตัดเสียงรบกวน | เสียงเบสแน่น
Sold by MonsterStore.th
Select options
About this product
Product description
สัมผัสเสียงที่ไม่เคยมีมาก่อนด้วยหูฟังแบบเปิดหูของ MONSTER AC530 ออกแบบมาเพื่อความสบายสูงสุด
ข้อมูลจำเพาะของผลิตภัณฑ์:
รุ่นบลูทูธ: 6.0
คะแนนกันน้ำ: IPX7
Shop
Sell
Customer support
Legal
Free shipping
Buy now
Open TikTok
Not now"""

    cleaned = _clean_rendered_description(raw_text)
    assert "Search" not in cleaned
    assert "1 / 9" not in cleaned
    assert "Sold by" not in cleaned
    assert "Shop" not in cleaned
    assert "Legal" not in cleaned
    assert "Open TikTok" not in cleaned
    assert "สัมผัสเสียงที่ไม่เคยมีมาก่อนด้วยหูฟังแบบเปิดหูของ MONSTER AC530" in cleaned
    assert "รุ่นบลูทูธ: 6.0" in cleaned
    assert "คะแนนกันน้ำ: IPX7" in cleaned

def test_extract_specs_from_text():
    text = """
รุ่นบลูทูธ: 6.0
ขนาดลำโพง: ลำโพงไดนามิก Biofiber
แบตเตอรี่หูฟัง: ทนทานสำหรับการใช้งานเป็นเวลานาน
เวลาเล่นดนตรี: สูงสุด 7–12 ชั่วโมง
เวลาการชาร์จหูฟัง: ประมาณ 1 ชั่วโมง
แบตเตอรี่ของเคสชาร์จ: 300 มิลลิแอมป์
คะแนนกันน้ำ: IPX7
ตัวเลือกสี: ดำ ขาว
แบรนด์: ESSAGER
กำลังไฟสูงสุด: 240 วัตต์
"""
    specs = _extract_specs_from_text(text)
    assert len(specs) == 10
    spec_dict = {s.split(":")[0].strip(): s.split(":", 1)[1].strip() for s in specs}
    assert spec_dict["รุ่นบลูทูธ"] == "6.0"
    assert spec_dict["คะแนนกันน้ำ"] == "IPX7"
    assert spec_dict["แบรนด์"] == "ESSAGER"
    assert spec_dict["กำลังไฟสูงสุด"] == "240 วัตต์"

def test_clean_title_strips_badges_and_cod():
    title = "【COD】หูฟังเปิดหู MONSTER AC530 ตัดเสียงรบกวน | เสียงเบสแน่น | กันน้ำ IPX7 - TikTok Shop"
    clean = _clean_title(title)
    assert "【COD】" not in clean
    assert "- TikTok Shop" not in clean
    assert clean == "หูฟังเปิดหู MONSTER AC530 ตัดเสียงรบกวน | เสียงเบสแน่น | กันน้ำ IPX7"

def test_clean_title_rejects_login_or_challenge():
    assert _clean_title("Log in") == ""
    assert _clean_title("Sign in") == ""
    assert _clean_title("Security Check") == ""
    assert _clean_title("TikTok") == ""

def test_deduplicate_and_filter_images():
    urls = [
        "https://sf16-website.neutral.ttwstatic.com/obj/tiktok_web_static/.../tts_logo_light_theme.bf501d2c.png",
        "https://p16-common-sign.tiktokcdn.com/tos-alisg-avt-0068/643cb6a235ba238a0858960f0417b69f~tplv-tiktokx-cropcenter:100:100.webp",
        "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/98de2f23620d4c7ca5e1f4d1b2e9972a~tplv-aphluv4xwc-resize-jpeg:800:800.jpeg",
        "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/98de2f23620d4c7ca5e1f4d1b2e9972a~tplv-aphluv4xwc-resize-webp:800:800.webp",
        "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/f403e4a14d5b4eaf980650dfe9982fd7~tplv-aphluv4xwc-resize-webp:800:800.webp",
        "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/215623710125407db56ab1e01fb525a9~tplv-aphluv4xwc-crop-webp:300:300.webp",
    ]
    results = _deduplicate_and_filter_images(urls)
    assert len(results) == 3
    # Logos and avatars must be excluded
    assert not any("tts_logo" in u for u in results)
    assert not any("tos-alisg-avt" in u for u in results)
    # 98de2f23... must only appear once
    hashes = [u for u in results if "98de2f23620d4c7ca5e1f4d1b2e9972a" in u]
    assert len(hashes) == 1

def test_looks_like_login_and_challenge():
    assert _looks_like_login_page("Log in", "Log in to TikTok Manage your account") is True
    assert _looks_like_login_page("TikTok", "Feedback and help\nLog in to TikTok") is True
    assert _looks_like_login_page("Product Name", "Normal product page", "https://www.tiktok.com/login") is True
    assert _looks_like_login_page("Normal Product", "Normal Description", "https://shop.tiktok.com/th/pdp/123") is False

    assert _looks_like_browser_challenge("Verify to continue: drag the puzzle piece") is True
    assert _looks_like_browser_challenge("Normal Description") is False

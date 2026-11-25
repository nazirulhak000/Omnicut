"""
scripts/cart_name_cleaner.py

Sanitizes and curates clean product names for TikTok Shop Showcase cart links.
Strictly enforces:
1. Max 30 characters (TikTok Studio limit)
2. Zero illegal Unicode characters (converts Roman numerals Ⅰ..Ⅹ -> I..X, removes °, ™, emojis)
3. Word-boundary aware truncation (never leaves broken single Thai characters like " ป" at the end)
4. Human-curated name lookup per product_id
"""

import re
from typing import Optional, Dict

ROMAN_MAP = {
    'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV', 'Ⅴ': 'V',
    'Ⅵ': 'VI', 'Ⅶ': 'VII', 'Ⅷ': 'VIII', 'Ⅸ': 'IX', 'Ⅹ': 'X',
    '°': '', '™': '', '®': '', '©': ''
}

# 45 products curated clean cart names (all <= 30 chars)
CURATED_CART_NAMES: Dict[str, str] = {
    '20260904233315_1': 'คีย์บอร์ด Logitech Wave Keys',
    '20260905182956_2': 'สายชาร์จแม่เหล็ก ESSAGER',
    'e8c50275ed5d4748a046603377e8a216': 'เมาส์ไร้สาย Logitech Lift',
    '7d2fa34272ef4404a5784a9c6e627fb0': 'ไมโครโฟนไร้สาย GoChek S24',
    'b29140664441426ca00294388013fee8': 'พัดลมระบายความร้อน BlueWow',
    '02a82b8dbfbf4cdf97bb59643f9d295b': 'สมาร์ทแบนด์ LOOP Smartband',
    '5082eeff0635403a9c7f9f51d44f7404': 'หูฟัง In-Ear Synmax',
    '9505b042d58640f5aa58015bb86be097': 'หัวชาร์จเร็ว Essager PD 30W',
    'e5d6f8f844f644ffa98be4f879486fc2': 'ฮับแปลง UGREEN USB-C 6 in 1',
    '0912f877ec0d45379c92b263228760d5': 'เมาส์ไร้สาย IWACHI i6',
    '58bbe6f1ff6d41018ce26f4369f6e9ed': 'สายคล้องคอแม่เหล็ก TELESIN',
    '15fb4c590b8a4603b12de13bb7eb589e': 'สายชาร์จ Essager C-to-C 100W',
    'e9b48af5e1de4a3a899b924c9dc1703f': 'USB Hub อะแดปเตอร์ 4 in 1',
    '38d7670c472e4777af722a923d96644f': 'หูฟัง JBL Tune 310C Type-C',
    'a6973f9378c54a6a869fb445083d9a5e': 'คีย์บอร์ดกลไก MonsGeek M1W',
    'ba489c3106eb404c8ea050785f5dc99d': 'ขาตั้งแม่เหล็ก MagSafe 360',
    'b7c63177a93d4db68edbccbe3b8dab39': 'ไฟแขวนหน้าจอคอม Xiaomi',
    '8d2e86320e124f1a887009fbf5aee86b': 'พัดลมมือถือ Orashare',
    '8cee5445661b4474b887c507529f2324': 'รางปลั๊กไฟ Toshino',
    'c3c8f81d146b46de8047d27a34e00fbf': 'รางปลั๊กไฟ Toshino 2300W',
    'c6eca50968f04431849b6464aacb6f89': 'พัดลมตั้งโต๊ะ Hatari 16 นิ้ว',
    '1dc35c158d2c4d00b78d26c91e76f7c5': 'พัดลมระบายความร้อน BASIKE',
    'bd746c48b7dd4eada670a3fbf9e48b7b': 'SSD พกพา ORICO K20',
    'ba1fa60482e0443f9b72301474b3216d': 'กล้องติดหมวก MUFU V12S PRO',
    '673882d55bd84c57ba805000a910c466': 'พัดลมมือถือแม่เหล็ก HOYAUP',
    '37521e0dae1a419e8037e159254d4fdf': 'สายชาร์จ Orsen S6 PD 240W',
    'cde38b1c07e54ea69a3d50a6c1bb3f18': 'Hatari Cyclone Max 8 นิ้ว',
    '7900bbca318d41ed964b5a721c0d951f': 'มินิพาวเวอร์แบงค์ GOOJODOQ',
    'b0137078e2ff4c089b60131f60168b54': 'หูฟัง Bluetooth Redmi Buds 8',
    'jee01': 'หูฟัง Bluetooth Jeep EW011 TWS',
    'cbce4d403975449a98e364b621d98308': 'พาวเวอร์แบงค์ TTZ K106 30k',
    '8ebd5ef6dc2545398dc1b771aedda50d': 'หูฟังเปิดหู MONSTER AC530',
    '431165f167284094959bdf0f0e806899': 'สายชาร์จ Essager 100W E-Mark',
    '8ee264e8586d4a619c19516b9367043c': 'ฟิล์มกระจกนิรภัย ESSAGER 9H',
    'fb77e97e611e4e059b943b5512e8cb82': 'สายชาร์จแม่เหล็ก ESSAGER 240W',
    'b6611b951335492fa3cdbeb156ed66d4': 'สายชาร์จ ESSAGER ES-X93 60W',
    'a4dcf71082204bcd97f76952f6b4e48d': 'เมาส์ไร้สาย Memzuoix 2.4G RGB',
    '6f917039385a473bac3cdb2f9319ba00': 'ฝาครอบกันฝุ่น Type-C ESSAGER',
    'd3d53d59d13d4e97b8ed5a1dddc93f51': 'สายชาร์จ 2in1 ESSAGER LED',
    'aca2c88f2a6d463e903a8b4fe7c7320d': 'สายชาร์จเกมมิ่ง TRANYOO 65W',
    'e2109dc73f9c4bd4a3c98c28bc731bdf': 'ปลอกนิ้วเล่นเกม TRANYOO GS01',
    '5da1d0860cac4369acaa2f23cb179dce': 'สายชาร์จเร็ว TRANYOO T-S20',
    '45563682e68d4ec6bd2dc08bcaf3fcca': 'HOCO EW97 หูฟังไร้สาย ANC',
    'cc048aa24673485e824f18eba54cd7a3': 'Buddytech คีย์บอร์ดเมาส์ RGB',
    'ecc3e8df937945ffa7ce60695f4d336d': 'OKDO Balance II เก้าอี้สุขภาพ',
}


def sanitize_cart_name(name: str) -> str:
    """General sanitizer for any arbitrary product name to ensure TikTok compatibility."""
    if not name:
        return ''
    s = str(name)
    # 1. Normalize Roman Numerals and forbidden characters
    for k, v in ROMAN_MAP.items():
        s = s.replace(k, v)
    # 2. Keep only letters, digits, Thai characters, spaces, and safe punctuation (-, ., (), /, ,)
    s = re.sub(r'[^\w\s\-\.\(\)\/ก-๙]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()

    if len(s) <= 30:
        return s

    # 3. Smart truncate at Thai/English word boundary (never mid-word or mid-combining-mark)
    from scripts.product_scraper import _short_name
    return _short_name(s, limit=30, fallback='')


def get_clean_cart_name(product_id: Optional[str] = None, raw_name: Optional[str] = None) -> str:
    """Returns curated clean cart name strictly by product_id, else sanitizes raw_name."""
    if product_id and product_id in CURATED_CART_NAMES:
        return CURATED_CART_NAMES[product_id]

    if raw_name:
        return sanitize_cart_name(raw_name)

    return ''

# Convenience alias
clean_cart_name = get_clean_cart_name

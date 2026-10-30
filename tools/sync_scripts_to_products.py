# -*- coding: utf-8 -*-
"""Sync the 20 Southern Couple Paper Chat scripts for 9 products into ProductStore.

Reads:
  - _Docs/ttz_k106_20_scripts.json
  - _Docs/hatari_16inch_20_scripts.json
  - _Docs/hatari_cyclone_max_20_scripts.json
  - _Docs/hoyaup_magnetic_fan_20_scripts.json
  - _Docs/orsen_s6_20_scripts.json
  - _Docs/essager_pd30w_20_scripts.json
  - _Docs/redmi_buds8_20_scripts.json
  - _Docs/goojodoq_5000mah_20_scripts.json
  - _Docs/jeep_ew011_20_scripts.json

Writes to:
  - scripts.product_store.ProductStore (_Docs/products.json & _Docs/store.db)
  - _Docs/products_seed.json (tracked in Git for instant Colab/Cloud hydration)
"""

import sys
import json
import datetime
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.product_store import ProductStore
from scripts.config import BASE_DIR

DOCS_DIR = BASE_DIR / "_Docs"

PRODUCTS_CATALOG = [
    {
        "product_code": "TTZ01",
        "slug": "ttz_k106",
        "name": "TTZ K106 Magnetic Wireless Power Bank 30000mAh",
        "url": "https://vt.tiktok.com/ZS9ykaGuy492W-oNdZy/",
        "tiktok_product_id": "1734519304293746340",
        "category": "พาวเวอร์แบงค์ & อุปกรณ์ชาร์จ",
        "specs": [
            {"key": "ความจุ", "value": "30,000mAh"},
            {"key": "ชาร์จไร้สายแม่เหล็ก", "value": "Magnetic Wireless 15W"},
            {"key": "ชาร์จเร็วมีสาย", "value": "Type-C 22.5W / PD 20W"},
            {"key": "สายในตัว", "value": "สาย Type-C + Lightning ในตัว 2 เส้น"},
            {"key": "ขาตั้งพับ", "value": "ขาตั้งพับโลหะในตัว 90 องศา"},
            {"key": "มาตรฐาน", "value": "มอก. 2879-2560"},
        ],
        "pain_points": [
            "แบตหมดระหว่างวันเวลาเดินทางหรือไลฟ์สด",
            "ลืมพกสายชาร์จหรือสายพันกันรุงรังในกระเป๋า",
            "ถือพาวเวอร์แบงค์หนักๆ แล้วสายหลุดชาร์จไม่เข้า",
        ],
        "selling_points": [
            "แปะดูดหลังเครื่องแน่นหนาชาร์จไร้สาย 15W ไม่หลุด",
            "มีสายชาร์จในตัว 2 เส้นและขาตั้งพับตั้งดูซีรีส์ได้",
            "ความจุแน่น 30,000mAh ชาร์จไอโฟนได้ 5-6 รอบสบายๆ",
        ],
    },
    {
        "product_code": "HAT01",
        "slug": "hatari_16inch",
        "name": "Hatari พัดลมปรับระดับ 16 นิ้ว T16M1",
        "url": "https://vt.tiktok.com/ZS9yHatari16/",
        "tiktok_product_id": "1734519304293746001",
        "category": "เครื่องใช้ไฟฟ้าในบ้าน",
        "specs": [
            {"key": "ขนาดใบพัด", "value": "16 นิ้ว"},
            {"key": "ระบบความปลอดภัย", "value": "Thermal Fuse ตัดไฟอัตโนมัติ"},
            {"key": "ปรับระดับ", "value": "ปรับความสูงได้ 5 ระดับ"},
        ],
        "pain_points": ["อากาศร้อนอบอ้าว", "พัดลมเก่าเสียงดัง สั่น มอเตอร์ร้อนไว"],
        "selling_points": ["ลมแรงสะใจ ลมเย็นทั่วถึง มอเตอร์ทนทานตัดไฟปลอดภัย"],
    },
    {
        "product_code": "HAT02",
        "slug": "hatari_cyclone_max",
        "name": "Hatari พัดลมไซโคลนแม็กซ์ Cyclone Max",
        "url": "https://vt.tiktok.com/ZS9yHatariCyclone/",
        "tiktok_product_id": "1734519304293746002",
        "category": "เครื่องใช้ไฟฟ้าในบ้าน",
        "specs": [
            {"key": "เทคโนโลยีลม", "value": "Cyclone Wind Vortex"},
            {"key": "การครอบคลุม", "value": "หมุนเวียนอากาศได้ไกล 12 เมตร"},
        ],
        "pain_points": ["แอร์เย็นไม่ทั่วห้อง เปลืองค่าไฟ ห้องอับทึบ"],
        "selling_points": ["ลมเกลียวไซโคลนทรงพลัง ช่วยกระจายความเย็นแอร์ทั่วห้อง ประหยัดไฟ"],
    },
    {
        "product_code": "HOY01",
        "slug": "hoyaup_magnetic_fan",
        "name": "HOYAUP พัดลมแม่เหล็กไร้สายติดผนัง",
        "url": "https://vt.tiktok.com/ZS9yHoyaupFan/",
        "tiktok_product_id": "1734519304293746003",
        "category": "อุปกรณ์แก็ดเจ็ต & ของใช้ในบ้าน",
        "specs": [
            {"key": "การติดตั้ง", "value": "ฐานแม่เหล็กดูดติดผนัง / โต๊ะ / หัวเตียง"},
            {"key": "แบตเตอรี่", "value": "แบตเตอรี่ในตัวใช้งานไร้สายได้ 8 ชม."},
        ],
        "pain_points": ["เข้าครัวทำกับข้าวร้อนเหงื่อแตก เข้าห้องน้ำร้อนอบ ไม่มีปลั๊กใกล้ๆ"],
        "selling_points": ["แปะติดได้ทุกที่ ไร้สาย พกพาสะดวก ลมแรงเย็นสบาย"],
    },
    {
        "product_code": "ORS01",
        "slug": "orsen_s6",
        "name": "Orsen by Eloop S6 พาวเวอร์แบงค์ไร้สาย 10000mAh",
        "url": "https://vt.tiktok.com/ZS9yOrsenS6/",
        "tiktok_product_id": "1734519304293746004",
        "category": "พาวเวอร์แบงค์ & อุปกรณ์ชาร์จ",
        "specs": [
            {"key": "ความจุ", "value": "10,000mAh บางเบาพกง่าย"},
            {"key": "การชาร์จ", "value": "Magnetic Wireless 15W + PD 20W"},
        ],
        "pain_points": ["พาวเวอร์แบงค์เทอะทะ หนัก ล้นกระเป๋า"],
        "selling_points": ["บางเฉียบ ดีไซน์พรีเมียม แปะชาร์จแม่เหล็กแน่นสนิท พกพาสะดวก"],
    },
    {
        "product_code": "ESS01",
        "slug": "essager_pd30w",
        "name": "Essager หัวชาร์จเร็ว PD 30W GaN Fast Charger",
        "url": "https://vt.tiktok.com/ZS9yEssagerPD30/",
        "tiktok_product_id": "1734519304293746005",
        "category": "อุปกรณ์ชาร์จ & สายชาร์จ",
        "specs": [
            {"key": "กำลังไฟ", "value": "30W GaN Fast Charging"},
            {"key": "พอร์ต", "value": "Type-C + USB-A ชาร์จได้ 2 เครื่องพร้อมกัน"},
        ],
        "pain_points": ["หัวชาร์จเดิมชาร์จช้า หัวชาร์จร้อนจัด พกหัวชาร์จหลายอัน"],
        "selling_points": ["ชิป GaN ขนาดจิ๋ว ชาร์จไอโฟน 0-60% ใน 30 นาที ไม่ร้อน"],
    },
    {
        "product_code": "RED01",
        "slug": "redmi_buds8",
        "name": "Redmi Buds 8 หูฟังบลูทูธไร้สาย ANC",
        "url": "https://vt.tiktok.com/ZS9yRedmiBuds8/",
        "tiktok_product_id": "1734519304293746006",
        "category": "หูฟัง & ออดิโอ",
        "specs": [
            {"key": "ตัดเสียงรบกวน", "value": "Active Noise Cancelling 42dB"},
            {"key": "แบตเตอรี่", "value": "ใช้งานรวมเคส 36 ชั่วโมง"},
        ],
        "pain_points": ["ขึ้นรถไฟฟ้าเสียงดัง ฟังเพลงไม่รู้เรื่อง คุยโทรศัพท์เสียงลมเข้า"],
        "selling_points": ["ตัดเสียงรบกวนเงียบกริบ ไมค์ตัดเสียงลมชัดเจน เบสแน่น"],
    },
    {
        "product_code": "GOO01",
        "slug": "goojodoq_5000mah",
        "name": "GOOJODOQ มินิพาวเวอร์แบงค์พกพา 5000mAh",
        "url": "https://vt.tiktok.com/ZS9yGoojodoq5K/",
        "tiktok_product_id": "1734519304293746007",
        "category": "พาวเวอร์แบงค์ & อุปกรณ์ชาร์จ",
        "specs": [
            {"key": "ความจุ", "value": "5,000mAh เสียบก้นชาร์จตรง"},
            {"key": "ขนาด", "value": "เท่าลิปสติก น้ำหนักเพียง 98 กรัม"},
        ],
        "pain_points": ["กระเป๋าใบเล็กไม่มีที่ใส่พาวเวอร์แบงค์ ไม่อยากพกสายชาร์จ"],
        "selling_points": ["เสียบชาร์จได้ทันทีไม่ต้องพกสาย เล็กเท่าลิปสติก เล่นเกมถือไม่เมื่อย"],
    },
    {
        "product_code": "JEE01",
        "slug": "jeep_ew011",
        "name": "Jeep EW011 หูฟังบลูทูธ TWS ไร้สาย",
        "url": "https://vt.tiktok.com/ZS9yJeepEW011/",
        "tiktok_product_id": "1734519304293746008",
        "category": "หูฟัง & ออดิโอ",
        "specs": [
            {"key": "ดีไซน์", "value": "เคสเมทัลลิกสไตล์ Outdoor ทนทาน"},
            {"key": "บลูทูธ", "value": "Bluetooth 5.3 Low Latency"},
        ],
        "pain_points": ["หูฟังหลุดง่ายเวลาออกกำลังกาย ดีไซน์ซ้ำๆ ทั่วไป"],
        "selling_points": ["ดีไซน์เท่ สปอร์ต ดุดัน ใส่ออกกำลังกายกระชับแน่น ไม่หลุด"],
    },
]

def load_scripts_for_slug(slug: str):
    json_path = DOCS_DIR / f"{slug}_20_scripts.json"
    if not json_path.exists():
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def script_item_to_angle(item: dict, index: int, product_code: str) -> dict:
    angle_id = f"ang_{index+1:02d}"
    turns = item.get("turns", [])
    dialog_lines = []
    tts_lines = []
    
    for t in turns:
        # Format: ['F', [[burst_text, tts_text], ...]] or dict
        if isinstance(t, (list, tuple)) and len(t) >= 2:
            spk_code = t[0]
            bursts = t[1]
            spk = "nong_nui" if spk_code in ["F", "female", "nong_nui"] else "phi_bao"
            speaker_name = "น้องนุ้ย" if spk == "nong_nui" else "พี่บ่าว"
            
            # Extract readable text from bursts
            if isinstance(bursts, list):
                txt_parts = []
                for b in bursts:
                    if isinstance(b, (list, tuple)) and len(b) > 0:
                        txt_parts.append(str(b[0]))
                    elif isinstance(b, str):
                        txt_parts.append(b)
                txt = " ".join(txt_parts).strip()
            else:
                txt = str(bursts).strip()
                
            dialog_lines.append(f"{speaker_name}: {txt}")
            tts_lines.append({"speaker": spk, "text": txt, "bursts": bursts})
        elif isinstance(t, dict):
            spk = t.get("speaker", "")
            txt = t.get("text", "").strip()
            speaker_name = "น้องนุ้ย" if spk in ["F", "female", "nong_nui"] else "พี่บ่าว"
            dialog_lines.append(f"{speaker_name}: {txt}")
            tts_lines.append({"speaker": spk, "text": txt})
    
    script_text = "\n".join(dialog_lines)
    
    hl_list = []
    for h in item.get("headlines", []):
        if isinstance(h, dict):
            parts = [h.get("sub", ""), h.get("t", ""), h.get("hl", "")]
            hl_list.append(" - ".join([p for p in parts if p]))
        elif isinstance(h, str):
            hl_list.append(h)
    key_features = ", ".join(hl_list)
    
    return {
        "angle_id": angle_id,
        "angle_name": item.get("title", f"ตอนที่ {index+1}"),
        "badge": item.get("category", "General"),
        "product_name": item.get("hook_title", ""),
        "hook_title": item.get("hook_title", ""),
        "pain_point": item.get("scenario", ""),
        "key_features": key_features,
        "price_deal": "",
        "ad_tone": "comedy_couple_southern",
        "script_lines": dialog_lines,
        "tiktok_caption": f"{item.get('title', '')} #tiktokshop #ป้ายยา",
        "tiktok_hashtags": ["#tiktokshop", "#ป้ายยา", "#คู่รักสายใต้"],
        "script_text": script_text,
        "tts_lines": tts_lines,
        "tts_hook_title": item.get("hook_title", ""),
        "status": "scripted",
        "voice_preset": "couple_southern",
        "updated_at": datetime.datetime.now().isoformat(),
        "extra_beats": [],
    }

def sync_all():
    store = ProductStore()
    existing_products = store.list()
    product_by_code = {p.get("product_code"): p for p in existing_products if p.get("product_code")}
    
    total_angles_synced = 0
    synced_products = []

    for entry in PRODUCTS_CATALOG:
        code = entry["product_code"]
        slug = entry["slug"]
        scripts = load_scripts_for_slug(slug)
        if not scripts:
            print(f"[-] No scripts found for {slug} ({code})")
            continue
        
        angles = [script_item_to_angle(s, idx, code) for idx, s in enumerate(scripts)]
        total_angles_synced += len(angles)
        
        existing = product_by_code.get(code)
        scope = ProductStore._scope(None, all_channels=True)
        if existing:
            # Update angles in existing product
            print(f"[+] Updating {code} ({existing['name']}) with {len(angles)} couple scripts...")
            with ProductStore._scoped_mutate(scope) as prods:
                for p in prods:
                    if p.get("product_code") == code or p.get("id") == existing["id"]:
                        p["angles"] = angles
                        p["status"] = "scripted"
                        p["updated_at"] = ProductStore._now()
                        synced_products.append(p)
                        break
        else:
            # Create new product
            print(f"[+] Creating new product {code}: {entry['name']} with {len(angles)} couple scripts...")
            new_prod = ProductStore.add(
                name=entry["name"],
                url=entry["url"],
                category=entry["category"],
                specs=entry["specs"],
                pain_points=entry["pain_points"],
                selling_points=entry["selling_points"],
                tiktok_product_id=entry["tiktok_product_id"],
                product_code=code,
                angles=angles,
            )
            synced_products.append(new_prod)

    # Reload full list
    all_products = store.list()
    print(f"\n[DONE] Successfully synced {len(synced_products)} products with {total_angles_synced} total couple angles!")
    print(f"[DONE] Total products in ProductStore: {len(all_products)}")

    # Write out products_seed.json
    seed_path = DOCS_DIR / "products_seed.json"
    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Generated tracked seed file: {seed_path} ({len(all_products)} products)")

if __name__ == "__main__":
    sync_all()

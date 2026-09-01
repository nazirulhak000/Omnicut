"""
Product Scraper and AI Content Matrix Engine for Shopee & TikTok Shop.
Extracts product metadata, follows redirects (short URLs), decodes URL slugs, and generates 4-5 viral script angles with captions & hashtags.
"""

import os
import re
import sys
import json
import html
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import INBOX_DIR, RAW_DIR

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def _extract_meta(html_text: str, name_or_prop: str) -> str:
    patterns = [
        rf'<meta\s+property=[\'"]{name_or_prop}[\'"]\s+content=[\'"](.*?)[\'"]',
        rf'<meta\s+content=[\'"](.*?)[\'"]\s+property=[\'"]{name_or_prop}[\'"]',
        rf'<meta\s+name=[\'"]{name_or_prop}[\'"]\s+content=[\'"](.*?)[\'"]',
        rf'<meta\s+content=[\'"](.*?)[\'"]\s+name=[\'"]{name_or_prop}[\'"]',
    ]
    for p in patterns:
        m = re.search(p, html_text, re.IGNORECASE | re.DOTALL)
        if m:
            return _clean_text(m.group(1))
    return ""

def _download_image(img_url: str, dest_path: Path) -> bool:
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) > 2000:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(data)
                return True
    except Exception as e:
        print(f"[ProductScraper] Failed to download {img_url}: {e}")
    return False

def _extract_slug_title(url: str) -> str:
    """Extracts human-readable product title directly from decoded URL path slug."""
    try:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path).strip('/')
        # E.g. Logitech-Wave-Keys-wireless-ergonomic-keyboard-(แป้นพิมพ์-TH-EN...)-i.158113227.22258251039
        parts = path.split('/')
        if not parts:
            return ""
        slug = parts[-1] or (parts[-2] if len(parts) > 1 else "")
        # Remove trailing shopee item ids like -i.123.456 or ?extraParams
        slug = re.sub(r'-i\.\d+\.\d+.*$', '', slug, flags=re.I)
        slug = re.sub(r'[\?#].*$', '', slug)
        # Replace hyphens with spaces
        title = slug.replace('-', ' ').strip()
        # If slug is too generic or empty, ignore
        if len(title) > 3 and not title.startswith("product"):
            return title
    except Exception:
        pass
    return ""

class ProductScraper:
    """Intelligent multi-tier scraper supporting both Long & Short Shopee/TikTok URLs."""

    @classmethod
    def scrape_url(cls, url: str) -> Dict[str, Any]:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        # 1. Resolve Short URL redirects (e.g. s.shopee.co.th, vt.tiktok.com)
        resolved_url = url
        try:
            req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(req, timeout=10) as resp:
                resolved_url = resp.geturl() or url
        except Exception as r_err:
            print(f"[ProductScraper] Redirect resolution note: {r_err}")

        platform = "shopee" if "shopee" in resolved_url.lower() else ("tiktok" if "tiktok" in resolved_url.lower() else "general")
        title = _extract_slug_title(resolved_url)
        description = ""
        price = ""
        images = []
        raw_text = title

        # 2. Try Direct Page Request
        try:
            req = urllib.request.Request(
                resolved_url,
                headers={"User-Agent": BROWSER_UA, "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_html = resp.read(600_000).decode("utf-8", errors="ignore")
                
                meta_title = _extract_meta(raw_html, "og:title") or _extract_meta(raw_html, "twitter:title")
                if meta_title and len(meta_title) > len(title):
                    title = meta_title

                description = _extract_meta(raw_html, "og:description") or _extract_meta(raw_html, "twitter:description")
                price = _extract_meta(raw_html, "product:price:amount") or _extract_meta(raw_html, "og:price:amount")
                
                og_img = _extract_meta(raw_html, "og:image") or _extract_meta(raw_html, "twitter:image")
                if og_img and og_img.startswith("http"):
                    images.append(og_img)

                img_matches = re.findall(r'<img[^>]+src=[\'"](https?://[^\'"]+\.(?:jpg|jpeg|png|webp)[^\'"]*)[\'"]', raw_html, re.I)
                for img in img_matches[:8]:
                    if img not in images and "icon" not in img.lower() and "logo" not in img.lower():
                        images.append(img)

                if description:
                    raw_text = f"{title}\n{description}"
        except Exception as e:
            print(f"[ProductScraper] Direct fetch blocked/failed ({e}), using proxy/slug extraction...")

        # 3. Fallback to Jina Reader Proxy if description is missing
        if not description or len(description) < 10:
            try:
                jina_url = f"https://r.jina.ai/{resolved_url}"
                jina_req = urllib.request.Request(
                    jina_url,
                    headers={"User-Agent": BROWSER_UA, "Accept": "text/plain", "X-No-Cache": "true"}
                )
                with urllib.request.urlopen(jina_req, timeout=10) as resp:
                    markdown_data = resp.read(200_000).decode("utf-8", errors="ignore")
                    
                    if markdown_data and len(markdown_data) > 50:
                        raw_text = markdown_data
                        h1_match = re.search(r'^#\s+(.+)$', markdown_data, re.M)
                        if h1_match and not title:
                            title = h1_match.group(1).strip()
                        
                        md_imgs = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', markdown_data)
                        for m_img in md_imgs:
                            if m_img not in images and "logo" not in m_img.lower() and "icon" not in m_img.lower():
                                images.append(m_img)
            except Exception as j_err:
                print(f"[ProductScraper] Jina Reader fallback note: {j_err}")

        # 4. Download images locally to INBOX_DIR / product_images
        downloaded_images = []
        clean_slug = re.sub(r'[^a-zA-Z0-9]', '_', title[:30]) or f"product_{int(time.time())}"
        img_dir = INBOX_DIR / "product_images" / clean_slug
        img_dir.mkdir(parents=True, exist_ok=True)

        for idx, img_url in enumerate(images[:6]):
            ext = ".jpg"
            if ".png" in img_url.lower(): ext = ".png"
            elif ".webp" in img_url.lower(): ext = ".webp"
            
            dest = img_dir / f"img_{idx+1}{ext}"
            if _download_image(img_url, dest):
                rel_path = str(dest.relative_to(PROJECT_ROOT)).replace("\\", "/")
                downloaded_images.append({
                    "url": img_url,
                    "local_path": str(dest),
                    "rel_path": rel_path,
                    "name": dest.name
                })

        # Ensure title fallback is clean
        display_title = title if title and len(title) > 3 else "สินค้า Shopee / TikTok Shop"

        return {
            "platform": platform,
            "url": resolved_url,
            "title": display_title,
            "description": description or f"สินค้าคุณภาพ {display_title} ตอบโจทย์การใช้งานจริง สเปกครบครัน",
            "price_note": price or "ราคาพิเศษในตะกร้า",
            "raw_text": raw_text or display_title,
            "images": downloaded_images,
            "image_count": len(downloaded_images)
        }

    @classmethod
    def generate_content_matrix(cls, product_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        title = product_data.get("title", "")
        desc = product_data.get("description", "")
        price = product_data.get("price_note", "")
        raw = product_data.get("raw_text", "")

        prompt = f"""
คุณเป็น Top TikTok Affiliate Creator มืออาชีพที่ทำยอดขายหลักล้าน
ช่วยวิเคราะห์ข้อมูลสินค้าด้านล่างนี้ แล้วแตกเป็น "4 มุมมองการป้ายยา (Content Angles)" ที่ดึงดูดใจและปิดการขายได้จริง

ข้อมูลสินค้า:
- ชื่อ/หัวข้อ: {title}
- รายละเอียด: {desc}
- ราคา/โปรโมชั่น: {price}
- ข้อมูลเพิ่มเติม: {raw[:1500]}

จงสร้างผลลัพธ์เป็น JSON Array ที่มี 4 Object ตาม 4 มุมมองนี้เป๊ะๆ:
1. "pain_point": ปัญหาก่อนใช้ (Problem / Agitation / Solution)
2. "viral_hype": ป้ายยาตัวแม่ TikTok ไวรัล (High Energy / TikTok Trend)
3. "deal_promo": คุ้มค่า / Flash Sale โปรลดกระแทกใจ (Urgency & Bargain)
4. "tech_pro": รีวิวฟังก์ชันเจาะลึก / สายไอที-ผู้เชี่ยวชาญ (Feature & Quality)

แต่ละ Object ใน JSON ต้องมีโครงสร้างดังนี้:
{{
  "angle_id": "pain_point",
  "angle_name": "😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน",
  "badge": "ขายดีอันดับ 1",
  "product_name": "ชื่อสินค้าที่กระชับ ไม่เกิน 30 ตัวอักษร",
  "hook_title": "พาดหัวเปิดคลิป 3 วินาทีแรก (มีอีโมจิ)",
  "pain_point": "ปัญหาหลักที่คนดูเจอ",
  "key_features": "จุดเด่น 3-4 ข้อที่ตอบโจทย์",
  "price_deal": "ข้อเสนอราคา/โปรโมชั่นและการเร่งรีบ",
  "ad_tone": "commercial_premium",
  "script_lines": [
    "บรรทัดที่ 1: Hook เปิดหัวกระแทกใจ",
    "บรรทัดที่ 2: ชี้ปัญหาที่ทุกคนเจอ",
    "บรรทัดที่ 3: เปิดตัวสินค้าและทางออก",
    "บรรทัดที่ 4: จุดเด่นและฟังก์ชันเทพ",
    "บรรทัดที่ 5: Call to Action ปิดการขายจิ้มตะกร้า"
  ],
  "tiktok_caption": "แคปชันพร้อมโพสต์ TikTok ความยาว 2-3 บรรทัด น่ากดซื้อ",
  "tiktok_hashtags": "#นายหน้าtiktok #รีวิวของดี #ของมันต้องมี #tiktokป้ายยา #พิกัดในตะกร้า"
}}

ตอบกลับเฉพาะ JSON array เท่านั้น ห้ามใส่คำเกริ่นนำหรือ markdown formatting อื่น
"""
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                response_text = resp.text or ""
                
                cleaned = re.sub(r'^```(?:json)?\s*', '', response_text.strip())
                cleaned = re.sub(r'\s*```$', '', cleaned).strip()
                
                angles = json.loads(cleaned)
                if isinstance(angles, list) and len(angles) > 0:
                    return angles
            except Exception as e:
                print(f"[ProductScraper] Gemini call failed ({e}), using fallback matrix...")

        # Robust Fallback Matrix
        return [
            {
                "angle_id": "pain_point",
                "angle_name": "😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน",
                "badge": "ยอดนิยม",
                "product_name": title[:30] or "สินค้าตัวนี้",
                "hook_title": f"🔥 ใครเจอปัญหานี้อยู่ หยุดดูด่วน! {title[:20]}",
                "pain_point": "ของเดิมพังง่าย ใช้ยาก ไม่ตอบโจทย์",
                "key_features": "ดีไซน์สวย ทนทาน ใช้งานง่าย เห็นผลจริง",
                "price_deal": "โปรพิเศษวันนี้ จิ้มตะกร้าซ้ายล่างเลย",
                "ad_tone": "commercial_premium",
                "script_lines": [
                    f"ทุกคน! ใครที่เบื่อกับปัญหาเดิมๆ ลองดูตัวนี้เลย",
                    f"นี่เลย {title[:25]} ตัวช่วยใหม่ล่าสุด",
                    "วัสดุพรีเมียม ใช้งานง่าย สะดวกสบายขึ้นเยอะ",
                    "ใครยังไม่มี ต้องรีบจัดแล้วนะ",
                    "พิกัดลดราคาพิเศษ จิ้มตะกร้าสีเหลืองซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"แก้ปัญหาเดิมๆ ได้จริง! {title[:30]} คุ้มค่ามาก พิกัดในตะกร้าซ้ายล่างน้า 👇",
                "tiktok_hashtags": "#รีวิวของดี #tiktokป้ายยา #ของใช้จำเป็น #พิกัดในตะกร้า #tiktokช้อปกันวันเงินออก"
            },
            {
                "angle_id": "viral_hype",
                "angle_name": "🔥 ป้ายยาตัวแม่ TikTok ไวรัล",
                "badge": "ไวรัลสุดๆ",
                "product_name": title[:30] or "ไอเทมตัวดัง",
                "hook_title": f"✨ เพิ่งได้ลองแล้วเข้าใจเลย ทำไมถึงแมสขนาดนี้!",
                "pain_point": "หาของดีที่คุ้มเงินยาก",
                "key_features": "กระแสแรงมากใน TikTok คุณภาพเกินราคา",
                "price_deal": "ของมีจำนวนจำกัด รีบกดก่อนหมด",
                "ad_tone": "commercial_hype",
                "script_lines": [
                    "แกรรร! ในที่สุดก็ได้ลองไอเทมตัวดังใน TikTok แล้ว",
                    f"ตัวนี้คือ {title[:25]} ที่เค้ารีวิวกันเพียบ",
                    "ของจริงคือสวยมาก ใช้งานดีแบบสิบเต็มสิบ",
                    "สมคำร่ำลือจริงๆ คุ้มเกินราคาไปมาก",
                    "รีบจิ้มตะกร้าด่วนๆ ก่อนของจะหมดน้า!"
                ],
                "tiktok_caption": f"ไม่แปลกใจทำไมคนใช้เยอะขนาดนี้! {title[:30]} ดีจริงไม่จกตา กดสั่งในตะกร้าได้เลย 🛒✨",
                "tiktok_hashtags": "#ของดีบอกต่อ #tiktokป้ายยา #fyp #รีวิวแน่น #พิกัดตะกร้าเหลือง"
            },
            {
                "angle_id": "deal_promo",
                "angle_name": "⚡ คุ้มค่า / Flash Sale ลดแหลก",
                "badge": "ดีลเด็ด",
                "product_name": title[:30] or "โปรแรงวันนี้",
                "hook_title": "⚡ Flash Sale วันนี้วันเดียว! ลดแรงกระแทกใจ",
                "pain_point": "กลัวซื้อราคาแพง ไม่ได้โปร",
                "key_features": "ลดพิเศษ แจกโค้ดส่งฟรี การันตีของแท้",
                "price_deal": f"{price or 'ลดพิเศษวันนี้'} ส่งฟรีถึงบ้าน",
                "ad_tone": "commercial_hype",
                "script_lines": [
                    "หยุดก่อน! วันนี้มีดีลลับ Flash Sale มาบอกต่อ",
                    f"{title[:25]} จัดโปรลดแรงที่สุดในรอบเดือน",
                    "ได้ของแท้ 100% แถมส่งฟรีถึงหน้าบ้าน",
                    "ราคานี้เฉพาะในไลฟ์และตะกร้านี้เท่านั้น",
                    "รีบกดสั่งในตะกร้าซ้ายล่างก่อนโปรจะหมดนะครับ"
                ],
                "tiktok_caption": f"⚡ ดีลลับลดแรงวันนี้วันเดียว! {title[:30]} ส่งฟรี กดเก็บคูปองในตะกร้าด่วน 🛍️",
                "tiktok_hashtags": "#flashsale #ลดราคาพิเศษ #ส่งฟรี #ช้อปปี้ถูกชัวร์ #tiktokช้อปปิ้ง"
            },
            {
                "angle_id": "tech_pro",
                "angle_name": "🎙️ รีวิวฟังก์ชันเจาะลึก (Tech & Pro)",
                "badge": "รีวิวละเอียด",
                "product_name": title[:30] or "สเปกจัดเต็ม",
                "hook_title": "🔍 รีวิวเจาะลึก ใช้งานจริง 7 วัน ดีจริงไหม?",
                "pain_point": "ต้องการข้อมูลความคุ้มค่าก่อนซื้อ",
                "key_features": "สเปกแท้ ทดสอบจริง วัสดุมาตรฐานสูง",
                "price_deal": "คุ้มค่ากับการลงทุนในระยะยาว",
                "ad_tone": "commercial_expert",
                "script_lines": [
                    "หลังจากที่ผมได้ทดลองใช้งานมา 1 สัปดาห์เต็มๆ",
                    f"นี่คือข้อดีของ {title[:25]} ที่น่าประทับใจ",
                    "ทั้งงานประกอบ สเปก และความเสถียร ทำได้ยอดเยี่ยม",
                    "ตอบโจทย์ทั้งสายใช้งานจริงและคนที่เน้นความคุ้มค่า",
                    "พิกัดของแท้พร้อมประกัน จิ้มตะกร้าซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"รีวิวจากการใช้งานจริง {title[:30]} สเปกครบ คุ้มค่ามาก เช็กราคาและสั่งซื้อในตะกร้าได้เลยครับ 📱",
                "tiktok_hashtags": "#รีวิวไอที #แกดเจ็ตน่าใช้ #เทคโนโลยี #ของแท้มีประกัน #พิกัดสินค้า"
            }
        ]

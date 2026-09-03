import re
import json
import os
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def _extract_meta(html: str, property_name: str) -> Optional[str]:
    """Extract content from meta tags by property or name."""
    pattern = rf'<meta[^>]+(?:property|name)=[\'"]{re.escape(property_name)}[\'"][^>]+content=[\'"]([^\'"]+)[\'"]'
    match = re.search(pattern, html, re.I)
    if match:
        return match.group(1).strip()
    pattern_alt = rf'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+(?:property|name)=[\'"]{re.escape(property_name)}[\'"]'
    match_alt = re.search(pattern_alt, html, re.I)
    if match_alt:
        return match_alt.group(1).strip()
    return None

def _extract_slug_title(url: str) -> str:
    """Extract human-readable product title from URL slug."""
    try:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path).strip('/')
        parts = path.split('/')
        if not parts:
            return ""
        slug = parts[-1] or (parts[-2] if len(parts) > 1 else "")
        slug = re.sub(r'-i\.\d+\.\d+.*$', '', slug, flags=re.I)
        slug = re.sub(r'[\?#].*$', '', slug)
        title = slug.replace('-', ' ').strip()
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

        resolved_url = url
        try:
            req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                resolved_url = resp.geturl() or url
        except Exception as r_err:
            print(f"[ProductScraper] Redirect resolution note: {r_err}")

        platform = "shopee" if "shopee" in resolved_url.lower() else ("tiktok" if "tiktok" in resolved_url.lower() else "general")
        title = _extract_slug_title(resolved_url)
        description = ""
        price = ""
        images = []
        raw_text = title

        try:
            req = urllib.request.Request(
                resolved_url,
                headers={"User-Agent": BROWSER_UA, "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
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
            print(f"[ProductScraper] Direct fetch note ({e}), using proxy/slug extraction...")

        clean_title = title.split("|")[0].split("- Shopee")[0].strip() or "สินค้าแนะนำ"

        return {
            "title": clean_title,
            "url": resolved_url,
            "platform": platform,
            "price_note": price or "ราคาพิเศษในตะกร้า",
            "description": description[:300] if description else "สินค้าคุณภาพยอดนิยม การันตีของแท้",
            "images": images,
            "raw_text": raw_text
        }

    @classmethod
    def generate_content_matrix(cls, product_data: Dict[str, Any], count: int = 10) -> List[Dict[str, Any]]:
        """Generates full 10-Angle Master Content Matrix in natural Thai spoken language."""
        title = product_data.get("title", "")
        desc = product_data.get("description", "")
        price = product_data.get("price_note", "")
        raw = product_data.get("raw_text", "")

        prompt = f"""
# Role & Objective
คุณคือ "ยอดนักขาย TikTok และครีเอเตอร์วิดีโอสั้นระดับท็อปของไทย" ที่เชี่ยวชาญด้านจิตวิทยาการโน้มน้าวใจ (Persuasive Copywriting & Neuromarketing)
ช่วยวิเคราะห์ข้อมูลสินค้าด้านล่างนี้ แล้วแตกเป็น "10 มุมมองการป้ายยา (Content Angles Master Matrix)" ที่ดึงดูดใจ ใช้ภาษาพูดธรรมชาติเหมือนเพื่อนสนิทมาป้ายยา และปิดการขายได้จริง

ข้อมูลสินค้า:
- ชื่อ/หัวข้อ: {title}
- รายละเอียด: {desc}
- ราคา/โปรโมชั่น: {price}
- ข้อมูลเพิ่มเติม: {raw[:1500]}

# กฎเหล็กในการเขียนบทพูด (Writing Guidelines):
1. **ห้ามใช้ภาษาเขียนทางการหรือภาษาโฆษณาทีวีโบราณ**: ห้ามใช้คำว่า "ท่านผู้มีเกียรติ", "นวัตกรรมล้ำสมัย", "ผลิตภัณฑ์นี้", "ตอบโจทย์ทุกไลฟ์สไตล์"
2. **ใช้ภาษาพูดธรรมชาติ (Spoken Thai)**: ใส่คำสร้อย จังหวะหายใจ และอารมณ์เหมือนเพื่อนสนิทมาป้ายยา เช่น "ทุกคน!", "คือมันดีมาก", "เนี่ยดูดิ", "รู้งี้ซื้อตั้งนานละ", "บอกเลยว่าโคตรคุ้ม"
3. **โครงสร้างสคริปต์ 5 ท่อนทรงพลัง (High-Converting Formula)**:
   - บรรทัดที่ 1 (Hook 3 วินาทีแรก): คำเปิดคลิปที่สะกดนิ้วให้หยุดดูทันที (Stop-Scroll) ชี้เป้าปัญหาหรือสร้างความอยากรู้อยากเห็น
   - บรรทัดที่ 2 (Pain Point / Agitation): ขยี้ความหงุดหงิดเดิมๆ ที่คนดูเคยเจอ ให้รู้สึกอินและพยักหน้าตาม
   - บรรทัดที่ 3 (The Solution / Product Intro): เปิดตัวสินค้าในฐานะ "ฮีโร่ผู้มาแก้ปัญหา"
   - บรรทัดที่ 4 (Core Benefit & Demonstration): บอกประโยชน์จริงที่คนดูจะได้รับ (ใช้งานจริงชีวิตสะดวกขึ้นยังไง)
   - บรรทัดที่ 5 (Call To Action & Urgency): กระตุ้นให้รีบกดตะกร้าซ้ายล่างทันทีก่อนหมดโปร
4. **กฎสำหรับ AI Voice Generation (TTS-Ready Script)**:
   - ห้ามใส่ Emoji ในบทพูดพากย์ (script_lines) — ใส่ได้เฉพาะ hook_title และ angle_name เท่านั้น
   - ตัวเลขสเปก ต้องเขียนเป็นคำไทยควบคู่ เช่น "ชาร์จเร็ว 66 วัตต์" ไม่ใช่ "ชาร์จเร็ว 66W"
   - ห้ามใช้คำย่อภาษาอังกฤษโดดๆ ในบทพูด เช่น ให้ใช้ "ยูเอสบีซี" แทน "USB-C", ใช้ "เวิร์คฟรอมโฮม" แทน "WFH"
   - ห้ามใส่ hashtag ในบทพูด (ใส่แยกใน tiktok_hashtags เท่านั้น)
   - ห้ามใส่จุดไข่ปลา หรือ "..." หรือ "…" ในบทพูดโดยเด็ดขาด ให้ใช้การเว้นวรรคภาษาไทยธรรมดา เพื่อให้ซับไตเติลอ่านง่าย สะอาดตา และไม่ติดจุดไข่ปลาไปบนหน้าจอ
5. **เทคนิค Seamless Loop (คลิปจบแล้ววนกลับมาเริ่มใหม่ได้เนียนกริบ เพิ่มยอดวิว x2)**:
   - บรรทัดที่ 5 (CTA ปิดการขาย): ปิดท้ายด้วยประโยคเชื่อมต่อแบบเปิด (Open Loop Connector) เช่น "รีบกดในตะกร้าด่วน แล้วจะเข้าใจว่า" หรือ "พิกัดในตะกร้าซ้ายล่าง รีบจัดแล้วจะรู้ว่าทำไม" เพื่อให้เมื่อคลิปวนลูปกลับมาเล่นบรรทัดที่ 1 จะฟังเชื่อมโยงกันเป็นเรื่องเดียวกันทันที!

จงสร้างผลลัพธ์เป็น JSON Array ที่มี {count} Object ตาม 10 มุมมองนี้:
1. "pain_point": 😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน (Problem / Agitation / Solution)
2. "unboxing": 🛍️ แกะกล่องว้าว / ของมันต้องมี (Unboxing & First Impression)
3. "stress_test": 🔬 โชว์ฟังก์ชันเจาะลึก / ทดสอบโหด (Feature Demo & Quality)
4. "fomo_deal": 🔥 FOMO โปรไฟลุก / คุ้มจนต้องแย่ง (Flash Deal & Urgency)
5. "comparison": 🆚 เทียบของเดิม vs ของใหม่ (Comparison Matrix)
6. "life_hack": 🤫 ทริกลึก / รู้งี้ซื้อนานแล้ว (Secret Trick & Life Hack)
7. "stop_scroll": ⚠️ เตือนภัยเชิงลบ / อย่าเพิ่งซื้อ! (Stop-Scroll Shock Hook)
8. "niche_target": 🧑‍💼 เจาะกลุ่มเฉพาะ สายออฟฟิศ/เกมเมอร์ (Target Audience Specific)
9. "longterm_review": ⭐ รีวิวเพื่อนเตือนเพื่อน ใช้จริง 3 เดือน (Real Experience)
10. "math_value": 💡 คำนวณความคุ้มค่าต่อวัน (Math & Value Breakdown)

แต่ละ Object ใน JSON ต้องมีโครงสร้างดังนี้:
{{
  "angle_id": "pain_point",
  "angle_name": "😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน",
  "badge": "ขายดีอันดับ 1",
  "product_name": "ชื่อสินค้าที่กระชับ ไม่เกิน 30 ตัวอักษร",
  "hook_title": "พาดหัวเปิดคลิป 3 วินาทีแรก (มีอีโมจิและคำกระแทกใจ)",
  "pain_point": "ปัญหาหลักที่คนดูเจอ",
  "key_features": "จุดเด่น 3-4 ข้อที่ตอบโจทย์",
  "price_deal": "ข้อเสนอราคา/โปรโมชั่นและการเร่งรีบ",
  "ad_tone": "commercial_premium",
  "script_lines": [
    "บรรทัดที่ 1: Hook เปิดหัวสะกดนิ้ว (มีคำสร้อย เช่น ทุกคน! / ดูนี่ด่วน!)",
    "บรรทัดที่ 2: ขยี้ปัญหาเดิมที่ทุกคนเจอ",
    "บรรทัดที่ 3: เปิดตัวสินค้าทางออก",
    "บรรทัดที่ 4: โชว์จุดเด่นและประโยชน์จริง",
    "บรรทัดที่ 5: ปิดการขายให้จิ้มตะกร้าซ้ายล่าง"
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
                    # Clean any stray ellipses from script_lines and hook_title
                    for a in angles:
                        if "script_lines" in a and isinstance(a["script_lines"], list):
                            a["script_lines"] = [
                                re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', line)).strip()
                                for line in a["script_lines"]
                            ]
                        if "hook_title" in a and isinstance(a["hook_title"], str):
                            a["hook_title"] = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', a["hook_title"])).strip()
                    # Add TTS-ready lines via sanitizer
                    from scripts.tts_sanitizer import TTSSanitizer
                    angles = TTSSanitizer.process_angles(angles[:count])
                    return angles
            except Exception as e:
                print(f"[ProductScraper] Gemini call failed ({e}), using fallback 10 matrix...")

        # Robust Fallback 10-Angle Matrix
        base_name = title[:30] or "สินค้าตัวนี้"
        return [
            {
                "angle_id": "pain_point",
                "angle_name": "😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน",
                "badge": "ยอดนิยม",
                "product_name": base_name,
                "hook_title": f"🔥 ใครเจอปัญหานี้อยู่ หยุดดูด่วน! {base_name}",
                "pain_point": "ของเดิมพังง่าย ใช้ยาก ไม่ตอบโจทย์",
                "key_features": "ดีไซน์สวย ทนทาน ใช้งานง่าย เห็นผลจริง",
                "price_deal": "โปรพิเศษวันนี้ จิ้มตะกร้าซ้ายล่างเลย",
                "ad_tone": "commercial_premium",
                "script_lines": [
                    "ทุกคน! ใครที่เบื่อกับปัญหาเดิมๆ ลองดูคลิปนี้ด่วน",
                    f"นี่เลย {base_name} ตัวช่วยใหม่ล่าสุด",
                    "วัสดุพรีเมียม ใช้งานง่าย สะดวกสบายขึ้นเยอะ",
                    "ใครยังไม่มี ต้องรีบจัดแล้วนะ",
                    "พิกัดลดราคาพิเศษ จิ้มตะกร้าสีเหลืองซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"แก้ปัญหาเดิมๆ ได้จริง! {base_name} คุ้มค่ามาก พิกัดในตะกร้าซ้ายล่างน้า 👇",
                "tiktok_hashtags": "#รีวิวของดี #tiktokป้ายยา #ของใช้จำเป็น #พิกัดในตะกร้า"
            },
            {
                "angle_id": "unboxing",
                "angle_name": "🛍️ แกะกล่องว้าว / ของมันต้องมี",
                "badge": "แกะกล่อง",
                "product_name": base_name,
                "hook_title": f"📦 แกะกล่องของที่รอมา 3 วัน... ตรงปกไหม?!",
                "pain_point": "กลัวซื้อมาแล้วไม่ตรงปก",
                "key_features": "งานเนียน สวยตรงปก แพ็กเกจพรีเมียม",
                "price_deal": "ราคาหลักร้อย คุ้มเกินราคา",
                "ad_tone": "commercial_hype",
                "script_lines": [
                    "แกรรร! ในที่สุดของที่สั่งไว้ก็มาส่งแล้ว",
                    f"ตัวนี้คือ {base_name} ที่คนรีวิวกันเพียบ",
                    "แกะกล่องออกมาคือว้าวมาก วัสดุดีเกินราคาไปเยอะ",
                    "สวยตรงปกไม่จกตา คุ้มค่าทุกบาทแน่นอน",
                    "รีบจิ้มตะกร้าด่วนๆ ก่อนของจะหมดน้า!"
                ],
                "tiktok_caption": f"แกะกล่องของจริง สวยตรงปกมาก! {base_name} พิกัดในตะกร้าซ้ายล่างเลย 🛒✨",
                "tiktok_hashtags": "#แกะกล่อง #ของดีบอกต่อ #tiktokป้ายยา #fyp"
            },
            {
                "angle_id": "stress_test",
                "angle_name": "🔬 โชว์ฟังก์ชันเจาะลึก / ทดสอบโหด",
                "badge": "สายสเปก",
                "product_name": base_name,
                "hook_title": f"⚡ ทดสอบให้ดูจะๆ ทนจริงไหม? {base_name}",
                "pain_point": "ของราคาถูกมักพังง่าย ไม่ทนทาน",
                "key_features": "โครงสร้างแข็งแรง ฟังก์ชันจัดเต็ม ใช้งานหนักได้",
                "price_deal": "รับประกันคุณภาพ มีของพร้อมส่ง",
                "ad_tone": "tech_minimal",
                "script_lines": [
                    "วันนี้จะมาเทสให้ดูแบบไม่ออมมือเลยว่าทนจริงไหม",
                    f"{base_name} ตัวนี้ใช้วัสดุเกรดพรีเมียมอย่างดี",
                    "ฟังก์ชันครบ ตอบโจทย์คนที่ชอบงานคุณภาพ",
                    "ใช้งานหนักแค่ไหนก็เอาอยู่ มั่นใจได้เลย",
                    "สนใจกดดูรายละเอียดในตะกร้าซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"ทดสอบความทนทานให้ดูแบบชัดๆ {base_name} คุณภาพเกินราคาแน่นอน 👇",
                "tiktok_hashtags": "#รีวิวเจาะลึก #ของแท้ #สายไอที #tiktokพาช้อป"
            },
            {
                "angle_id": "fomo_deal",
                "angle_name": "🔥 FOMO โปรไฟลุก / คุ้มจนต้องแย่ง",
                "badge": "ดีลเด็ด",
                "product_name": base_name,
                "hook_title": "⚡ Flash Sale วันนี้วันเดียว! ลดแรงกระแทกใจ",
                "pain_point": "กลัวซื้อราคาแพง ไม่ได้โปร",
                "key_features": "ลดพิเศษ แจกโค้ดส่งฟรี การันตีของแท้",
                "price_deal": f"{price or 'ลดพิเศษวันนี้'} ส่งฟรีถึงบ้าน",
                "ad_tone": "commercial_hype",
                "script_lines": [
                    "หยุดก่อน! วันนี้มีดีลลับ Flash Sale มาบอกต่อ",
                    f"{base_name} จัดโปรลดแรงที่สุดในรอบเดือน",
                    "ได้ของแท้ 100% แถมส่งฟรีถึงหน้าบ้าน",
                    "ราคานี้เฉพาะในตะกร้านี้เท่านั้น",
                    "รีบกดสั่งในตะกร้าซ้ายล่างก่อนโปรจะหมดนะครับ"
                ],
                "tiktok_caption": f"⚡ ดีลลับลดแรงวันนี้วันเดียว! {base_name} ส่งฟรี กดเก็บคูปองในตะกร้าด่วน 🛍️",
                "tiktok_hashtags": "#flashsale #ลดราคาพิเศษ #ส่งฟรี #ช้อปปี้ถูกชัวร์"
            },
            {
                "angle_id": "comparison",
                "angle_name": "🆚 เทียบของเดิม vs ของใหม่",
                "badge": "เปรียบเทียบ",
                "product_name": base_name,
                "hook_title": f"🆚 เทียบให้ดูชัดๆ แบบเดิม VS แบบใหม่ ต่างกันยังไง?",
                "pain_point": "ไม่แน่ใจว่าเปลี่ยนแล้วจะดีขึ้นจริงไหม",
                "key_features": "เร็วกว่า ใช้งานง่ายกว่า ไม่เกะกะ",
                "price_deal": "คุ้มกว่าซื้อของเดิมซ้ำๆ",
                "ad_tone": "commercial_premium",
                "script_lines": [
                    "ใครที่กำลังลังเลว่าจะเปลี่ยนดีไหม ดูคลิปนี้เลย",
                    "ฝั่งซ้ายคือแบบเดิมที่เคยใช้ ปัญหาเยอะ พังง่าย",
                    f"แต่ฝั่งขวาคือ {base_name} ชีวิตเปลี่ยนทันที",
                    "ใช้ง่ายกว่า ทนทานกว่า ไม่ต้องเสียเงินซื้อบ่อยๆ",
                    "อยากเปลี่ยนชีวิตให้ง่ายขึ้น จิ้มตะกร้าซ้ายล่างเลย!"
                ],
                "tiktok_caption": f"เทียบกันชัดๆ ทำไมต้องเปลี่ยนมาใช้ {base_name} ดูแล้วจะเข้าใจ! 👇",
                "tiktok_hashtags": "#เปรียบเทียบ #ของดีบอกต่อ #ชีวิตง่ายขึ้น #ป้ายยา"
            },
            {
                "angle_id": "life_hack",
                "angle_name": "🤫 ทริกลึก / รู้งี้ซื้อนานแล้ว",
                "badge": "Life Hack",
                "product_name": base_name,
                "hook_title": f"💡 เพิ่งรู้ว่ามีของแบบนี้ด้วย! รู้งี้ซื้อตั้งนานแล้ว",
                "pain_point": "เสียเวลาทำอะไรยากๆ มาตั้งนาน",
                "key_features": "ประหยัดเวลา ช่วยให้ชีวิตสะดวกขึ้น 10 เท่า",
                "price_deal": "ไอเทมลับราคาเบาๆ",
                "ad_tone": "commercial_hype",
                "script_lines": [
                    "ทุกคน! ใครชอบทริกช่วยให้ชีวิตง่ายขึ้น ดูนี่ด่วน",
                    f"นี่คือ {base_name} ไอเทมลับที่ช่วยประหยัดเวลาสุดๆ",
                    "แค่มีตัวนี้ติดไว้ อะไรๆ ก็สะดวกขึ้นเยอะมาก",
                    "ใช้แล้วจะพูดคำเดียวเลยว่า รู้งี้ซื้อตั้งนานแล้ว!",
                    "พิกัดไอเทมลับ จิ้มในตะกร้าซ้ายล่างได้เลยน้า"
                ],
                "tiktok_caption": f"ไอเทมลับที่ช่วยให้ชีวิตง่ายขึ้น 10 เท่า! {base_name} พิกัดตะกร้าซ้ายล่างเลย 💡",
                "tiktok_hashtags": "#lifehack #ไอเทมลับ #รู้งี้ซื้อนานแล้ว #ของมันต้องมี"
            },
            {
                "angle_id": "stop_scroll",
                "angle_name": "⚠️ เตือนภัยเชิงลบ / อย่าเพิ่งซื้อ!",
                "badge": "เตือนภัย",
                "product_name": base_name,
                "hook_title": f"⚠️ หยุดก่อน! อย่าเพิ่งซื้อ ถ้ายังไม่รู้ข้อนี้...",
                "pain_point": "กลัวโดนหลอก ซื้อของไม่มีคุณภาพ",
                "key_features": "เตือนให้เช็กของแท้ และข้อดีที่ไม่มีใครบอก",
                "price_deal": "ระวังของปลอม สั่งจากตะกร้าแท้ตรงนี้",
                "ad_tone": "commercial_premium",
                "script_lines": [
                    "หยุดเลื่อนก่อน! ใครกำลังจะซื้อของประเภทนี้ ฟังด่วน",
                    "ในตลาดมีของเลียนแบบเยอะมาก ใช้แป๊บเดียวพัง",
                    f"ถ้าจะเอาให้ชัวร์ ต้องเลือก {base_name} ตัวแท้เท่านั้น",
                    "คุณภาพการันตี วัสดุดี ใช้งานยาวๆ ไม่มีผิดหวัง",
                    "เพื่อความชัวร์ กดสั่งจากตะกร้าทางการซ้ายล่างตรงนี้ได้เลย!"
                ],
                "tiktok_caption": f"⚠️ เตือนแล้วนะ! เช็กให้ดีก่อนซื้อ {base_name} ของแท้กดในตะกร้าทางการเลย 👇",
                "tiktok_hashtags": "#เตือนภัย #ของแท้100 #tiktokป้ายยา #ระวังของปลอม"
            },
            {
                "angle_id": "niche_target",
                "angle_name": "🧑‍💼 เจาะกลุ่มเฉพาะ สายออฟฟิศ/เกมเมอร์",
                "badge": "ตรงกลุ่ม",
                "product_name": base_name,
                "hook_title": f"🧑‍💻 ไอเทมลับชาว WFH / เกมเมอร์ ที่ต้องมีติดโต๊ะ!",
                "pain_point": "โต๊ะรก นั่งทำงานนานๆ แล้วล้า",
                "key_features": "จัดโต๊ะคอมสวย สรีรศาสตร์ ใช้งานคล่องตัว",
                "price_deal": "เพิ่มประสิทธิภาพการทำงาน",
                "ad_tone": "tech_minimal",
                "script_lines": [
                    "ชาวออฟฟิศและสายจัดโต๊ะคอม ต้องดูคลิปนี้!",
                    f"นี่คือ {base_name} ไอเทมที่ช่วยให้โต๊ะทำงานดูโปรขึ้น",
                    "ใช้งานสะดวก คล่องตัว ช่วยให้ทำงานและเล่นเกมได้ฟินขึ้น",
                    "มีติดโต๊ะไว้ ได้ใช้งานทุกวันแน่นอน",
                    "พิกัดไอเทมจัดโต๊ะ จิ้มตะกร้าซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"ไอเทมที่ชาวจัดโต๊ะคอมและ WFH ต้องมี! {base_name} พิกัดในตะกร้าเลย 🖥️✨",
                "tiktok_hashtags": "#จัดโต๊ะคอม #wfh #เกมเมอร์ #สายออฟฟิศ #desksetup"
            },
            {
                "angle_id": "longterm_review",
                "angle_name": "⭐ รีวิวเพื่อนเตือนเพื่อน ใช้จริง 3 เดือน",
                "badge": "รีวิวพลีชีพ",
                "product_name": base_name,
                "hook_title": f"⭐ ใช้จริงมา 3 เดือนเต็ม... สรุปพังยัง? เล่าหมดเปลือก",
                "pain_point": "กลัวใช้ได้แค่ไม่กี่วันก็พัง",
                "key_features": "ผ่านการใช้งานจริงทุกวัน ทนทาน ไม่เสื่อม",
                "price_deal": "คุ้มค่าเงินในระยะยาว",
                "ad_tone": "commercial_premium",
                "script_lines": [
                    "มารีวิวแบบไม่อวย ใช้จริงมาครบ 3 เดือนเต็มแล้ว",
                    f"{base_name} ตัวนี้บอกตรงๆ ว่าตอนแรกไม่คิดว่าจะทนขนาดนี้",
                    "ใช้ทุกวันแบบสมบุกสมบัน ไม่มีงอแง ไม่มีพัง",
                    "เป็นหนึ่งในของที่ซื้อมาแล้วรู้สึกคุ้มเงินที่สุดในปีนี้",
                    "ใครกำลังเล็งอยู่ ไม่ต้องคิดเยอะ จิ้มตะกร้าซ้ายล่างได้เลย!"
                ],
                "tiktok_caption": f"รีวิวหลังใช้จริง 3 เดือน {base_name} ทนจริงไม่จกตา กดสั่งในตะกร้าได้เลย ⭐",
                "tiktok_hashtags": "#รีวิวใช้จริง #ไม่อวย #ของดีบอกต่อ #ใช้แล้วชอบ"
            },
            {
                "angle_id": "math_value",
                "angle_name": "💡 คำนวณความคุ้มค่าต่อวัน",
                "badge": "สุดคุ้ม",
                "product_name": base_name,
                "hook_title": f"💰 ราคาหลักร้อย แต่ใช้ได้ 3 ปี ตกวันละไม่ถึงบาท!",
                "pain_point": "คิดว่าสินค้าราคาสูง ไม่กล้าลงทุน",
                "key_features": "อายุการใช้งานยาวนาน ประหยัดค่าใช้จ่ายแฝง",
                "price_deal": "ประหยัดกว่าซื้อของถูกซ้ำๆ",
                "ad_tone": "commercial_hype",
                "script_lines": [
                    "มาคำนวณความคุ้มค่าให้ดู ว่าทำไมตัวนี้ถึงน่าลงทุน",
                    f"{base_name} ราคาแค่หลักร้อย แต่ใช้งานได้หลายปี",
                    "หารเฉลี่ยออกมาตกวันละไม่ถึงบาทเดียว",
                    "เทียบกับความสะดวกและสุขภาพที่ได้ คือโคตรคุ้ม!",
                    "อย่ารอช้า รีบกดสั่งในราคาโปรโมชันที่ตะกร้าซ้ายล่างเลยครับ"
                ],
                "tiktok_caption": f"คิดแบบนักคำนวณ {base_name} ตกวันละไม่กี่สตางค์แต่คุ้มสุดๆ พิกัดในตะกร้า 👇",
                "tiktok_hashtags": "#คุ้มค่า #ประหยัดเงิน #ของดีราคาถูก #tiktokป้ายยา"
            }
        ][:count]

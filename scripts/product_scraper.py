import re
import json
import os
import socket
import ipaddress
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

# Only these hosts (and their subdomains) are legitimate scrape targets --
# Shopee/TikTok product pages and the short-link domains their own "share"
# buttons produce. Everything else is refused before a single socket opens,
# so this doubles as the SSRF allowlist: a malicious or compromised link
# can't redirect the scraper into cloud metadata endpoints, the app's own
# API, or the local network no matter what host validation below says.
ALLOWED_SCRAPE_DOMAINS = (
    "shopee.co.th",
    "shp.ee",
    "tiktok.com",
)


def _hostname_allowed(hostname: str) -> bool:
    """True if `hostname` is, or is a subdomain of, an allowed scrape domain."""
    host = (hostname or "").lower().rstrip(".")
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in ALLOWED_SCRAPE_DOMAINS)


def _validate_scrape_url(url: str) -> None:
    """
    Rejects any URL that is not a plain http(s) request to an allowed
    domain resolving to a public, non-internal IP address.

    This app has no authentication and CORS is wide open, so any web page
    the user has open can hit this backend's endpoints. Without this check
    a "paste a product link" field is a full SSRF primitive: an attacker
    supplies http://169.254.169.254/... (cloud metadata / IAM credential
    theft once this is deployed), http://127.0.0.1:8000/... (the app's own
    API), or http://10.x/192.168.x/172.16-31.x (internal network scanning,
    with scraped title/price echoed back as an oracle). Raises ValueError
    on rejection so existing callers' `except ValueError` handling surfaces
    a clear message instead of the request silently going through.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}")

    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL is missing a hostname")

    if not _hostname_allowed(hostname):
        raise ValueError(f"Host '{hostname}' is not an allowed scrape target")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve host '{hostname}': {e}")

    if not addrinfo:
        raise ValueError(f"Could not resolve host '{hostname}'")

    for family, _type, _proto, _canon, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"Host '{hostname}' resolved to an invalid address")
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(
                f"Host '{hostname}' resolves to a non-public address ({ip_str}) and is refused"
            )


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Validates every redirect hop before following it.

    `urllib` follows redirects automatically by default and the caller only
    ever sees the final URL (`resp.geturl()`) -- so a link that starts on an
    allowed host can 302 to an internal address and urllib will happily
    fetch it with no further checks. Overriding `redirect_request` lets us
    re-run the same host/IP validation on every hop, and refuse (rather than
    silently drop) any hop that fails it.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_scrape_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_safe_opener(*handlers):
    return urllib.request.build_opener(_SafeRedirectHandler(), *handlers)


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
        _validate_scrape_url(url)

        resolved_url = url
        try:
            import http.cookiejar
            cookie_jar = http.cookiejar.CookieJar()
            opener = _build_safe_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": BROWSER_UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
                }
            )
            with opener.open(req, timeout=20) as resp:
                resolved_url = resp.geturl() or url
        except ValueError:
            # A redirect hop failed host/IP validation -- refuse the whole
            # request rather than silently falling back to the un-redirected
            # (and possibly still-attacker-controlled) original URL.
            raise
        except Exception as r_err:
            print(f"[ProductScraper] Redirect resolution note: {r_err}")

        # resolved_url may differ from the already-validated `url` (redirect
        # target); re-validate it since _SafeRedirectHandler only vets
        # intermediate hops, not the value ultimately returned by geturl().
        _validate_scrape_url(resolved_url)

        platform = "shopee" if "shopee" in resolved_url.lower() else ("tiktok" if "tiktok" in resolved_url.lower() else "general")
        title = _extract_slug_title(resolved_url)
        description = ""
        price = ""
        images = []
        raw_text = title

        try:
            req = urllib.request.Request(
                resolved_url,
                headers={
                    "User-Agent": BROWSER_UA,
                    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            )
            with _build_safe_opener().open(req, timeout=20) as resp:
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
คุณคือ "ยอดนักขาย TikTok และครีเอเตอร์สายรีวิวมือโปรระดับท็อปของไทย" ที่เชี่ยวชาญด้านจิตวิทยาการโน้มน้าวใจ (Persuasive Copywriting & Neuromarketing) และการแต่งบทพูดสำหรับ AI Voice Engine ให้พากย์ได้เป็นธรรมชาติ มีจังหวะหายใจเหมือนมนุษย์พูดจริง 100%
ช่วยวิเคราะห์ข้อมูลสินค้าด้านล่างนี้ แล้วแตกเป็น "10 มุมมองการป้ายยา (Content Angles Master Matrix)" ที่ดึงดูดใจ ใช้ภาษาพูดธรรมชาติเหมือนเพื่อนสนิทมาบอกต่อของดี มีจังหวะวรรคตอนที่น่าฟัง และปิดการขายได้จริง

ข้อมูลสินค้า:
- ชื่อ/หัวข้อ: {title}
- รายละเอียด: {desc}
- ราคา/โปรโมชั่น: {price}
- ข้อมูลเพิ่มเติม: {raw[:1500]}

# กฎเหล็กด้านจังหวะการพูด การเว้นวรรค และความไวรัล (Viral Cadence & Breath Pacing Standards):
1. **การเคาะเว้นวรรคแบ่งก้อนความคิดสร้างจังหวะหายใจ (Natural Thought Chunking & Breath Pacing - กฎสำคัญที่สุด)**:
   - ในแต่ละบรรทัด **ห้ามเขียนข้อความเป็นก้อนยาวติดกันเด็ดขาด!** เพราะจะทำให้เสียงพากย์ AI อ่านรวดเดียวโดยไม่หายใจ
   - ให้เคาะเว้นวรรค (1 Space) คั่นระหว่าง "ก้อนความคิด" (2-3 วรรคย่อย: ประเด็นหลัก - จุดเด่น - คำลงท้าย) เสมอ เพื่อให้เป็นจุดพักหายใจ (Micro-pause 100-150ms) สำหรับเสียงพากย์ AI และทำให้การตัดคำซับไตเติลบนหน้าจอสวยงาม
   - ตัวอย่างการเว้นวรรคที่ถูกต้อง:
     * "คีย์บอร์ดเพื่อสุขภาพตัวนี้ มีดีมากกว่าแค่ออกแบบสวยครับ สเปกเค้า จัดเต็มมาก"
     * "รองรับทั้ง Bluetooth และตัวรับสัญญาณ Logi Bolt สลับใช้งานได้ถึง 3 อุปกรณ์ พร้อมกันเลยครับ"
     * "แถมยังใช้งานได้ราบรื่น ทั้งบน Windows และ Mac สลับพิมพ์งานได้ไหลลื่น ไม่มีสะดุดเลยครับ"
     * "แบตเตอรี่อึดสุดขีด ใช้ได้นานสูงสุดถึง 36 เดือน ด้วยถ่าน AAA แค่ 2 ก้อน คุ้มมากครับ"
     * "สเปกจัดเต็มขนาดนี้ ราคาพิเศษสุดคุ้ม กดดูในตะกร้าสีเหลือง ซ้ายล่างตอนนี้ได้เลยครับ"

2. **ความยาวคลิปเป้าหมาย 30 - 38 วินาทีพอดี (Strict Duration Standard)**:
   - เมื่อพากย์ด้วยเสียงพากย์ AI (+15% speed) สคริปต์รวมทั้ง 5 ท่อนต้องมีความยาวประมาณ **70 - 85 คำ** (ประมาณ **280 - 350 ตัวอักษร**) เพื่อให้เวลาจบที่ 30 - 38 วินาทีกำลังพอดี
   - **ห้ามเขียนยืดยาวเกิน 40 วินาทีเด็ดขาด!** ตัดเนื้อหาที่เวิ่นเว้อออก เล่าตรงประเด็น กระชับ จังหวะเร็วแบบ Short-form TikTok

3. **น้ำเสียงและเพศของผู้พูด (Strict Male Persona 100%)**:
   - **ผู้พูดต้องเป็นผู้ชายเท่านั้น (Male Tone Only)**
   - ใช้สรรพนามและคำลงท้าย "ผม / ครับ / นะครับ" เท่านั้น
   - **ห้ามมีคำลงท้ายเพศหญิงโดยเด็ดขาด เช่น "ค่ะ", "นะคะ", "คะ", "จ้า", "น้า", "แกรรร", "หนู"**
   - ใช้น้ำเสียงจริงใจ มีพลัง เหมือนเพื่อนผู้ชายสายไอที/สายรีวิวมาบอกต่อของดี

4. **โครงสร้างสคริปต์ 5 ท่อนทรงพลัง สั้นกระชับ (5-Beat Viral Structure)**:
   - ท่อนที่ 1 (Hook สะกดนิ้ว 0-3 วิ, ~10-14 คำ): ประโยคเปิดคลิปดึงดูดคนที่เจอปัญหานี้ ชี้เป้าทันที
   - ท่อนที่ 2 (Pain Point / สเปกหลัก 4-9 วิ, ~14-18 คำ): ขยี้ปัญหาเดิมๆ หรือชูฟังก์ชันหลักที่แก้ปัญหา
   - ท่อนที่ 3 (Core Tech & Compatibility 10-15 วิ, ~14-18 คำ): เปิดตัวสินค้า ชูชื่อรุ่นภาษาอังกฤษทางการ ความง่ายในการเชื่อมต่อ
   - ท่อนที่ 4 (Real Feel & Endurance 16-22 วิ, ~16-20 คำ): จุดเด่นตอนใช้งานจริง สัมผัสดีไซน์ ความทนทาน แบตเตอรี่
   - ท่อนที่ 5 (High-Converting CTA 23-30 วิ, ~12-16 คำ): ชวนตัดสินใจกดสั่งซื้อในตะกร้าสีเหลืองซ้ายล่างทันที

5. **กฎภาษาและการเขียนคำเฉพาะ (Strict Official English Retention)**:
   - **ชื่อแบรนด์, ชื่อรุ่นสินค้า, และศัพท์เทคนิคเฉพาะทาง ต้องเขียนเป็นภาษาอังกฤษตามชื่อทางการเสมอ ห้ามแปลงหรือทับศัพท์เป็นภาษาไทยเด็ดขาด**:
     * ตัวอย่างที่ถูกต้อง: "Logitech Wave Keys", "Logi Bolt", "Bluetooth", "USB-C", "Type-C", "Wi-Fi", "iPad", "Mac", "Windows", "AAA", "ANC", "Ergonomic", "Memory Foam"
     * ตัวอย่างที่ผิด (ห้ามทำเด็ดขาด): "โลจิเทค เวฟ คีย์ส", "โลจิ โบลต์", "บลูทูธ", "ยูเอสบีซี", "ทริปเปิลเอ"
     * เหตุผล: คำบรรยายและซับไตเติลบนจอต้องแสดงเป็นภาษาอังกฤษทางการ สวยงาม น่าเชื่อถือ ตรงปก
   - **ตัวเลขและหน่วย**: เขียนเลขอารบิกคู่กับหน่วย "66 วัตต์", "36 เดือน", "ถ่าน AAA แค่ 2 ก้อน", "129 บาท"
   - ห้ามใส่ Emoji ในบทพูดพากย์ (script_lines) — ใส่ได้เฉพาะ hook_title และ angle_name
   - ห้ามใส่ hashtag ในบทพูด
   - ห้ามใส่จุดไข่ปลา หรือ "..." หรือ "…" ในบทพูดเด็ดขาด

6. **ภาษาพูดไทยแท้ธรรมชาติ ห้ามแต่งสำนวนแปลกๆ (Natural Spoken Thai Phrasing)**:
   - ห้ามประดิษฐ์คำแปลกๆ หรือสะกดตกหล่นเด็ดขาด เช่น:
     * ห้ามเขียน "หนะคอม" -> ต้องเขียน "หน้าคอม" หรือ "หน้าจอคอม"
     * ห้ามเขียน "รักสุขภาพข้อมือ" หรือ "รักสุขภาพข้อมือตัวเองด่วนๆ" -> ต้องเขียน "รักข้อมือตัวเอง" หรือ "อยากถนอมข้อมือ" หรือ "ไม่อยากทรมานข้อมือ"
     * ห้ามเขียน "ลดกระหน่ำด่วนๆ เร็วๆ" ซ้ำซ้อน -> ให้ใช้คำกระชับเช่น "ราคาพิเศษในตะกร้าสีเหลืองซ้ายล่างได้เลยครับ"
   - ใช้ภาษาพูดแบบเพื่อนสนิทสายไอทีป้ายยาเพื่อน สั้น กระชับ คมคาย ได้อารมณ์ และเป็นคำที่คนไทยพูดกันจริงๆ ในชีวิตประจำวัน

7. **กฎพิเศษกรณีดึงข้อมูลจาก URL (Shopee / TikTok Shop / เว็บไซต์)**:
   - หากรายละเอียดมีสั้น ให้ดึงความรู้สเปกจริงอย่างเป็นทางการ (Official Hardware Specs) มาเขียนให้ตรงความจริง 100% ห้ามมั่วสเปก

จงสร้างผลลัพธ์เป็น JSON Array ที่มี {count} Object ตาม 10 มุมมองนี้:
1. "pain_point": 😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน (Problem / Agitation / Solution)
2. "spec_review": ⚙️ รีวิวสเปกเจาะลึก / ฟังก์ชันจัดเต็ม (Deep Spec Review & Technical Features)
3. "unboxing": 🛍️ แกะกล่องว้าว / ของมันต้องมี (Unboxing & First Impression)
4. "fomo_deal": 🔥 FOMO โปรไฟลุก / คุ้มจนต้องแย่ง (Flash Deal & Urgency)
5. "comparison": 🆚 เทียบของเดิม vs ของใหม่ (Comparison Matrix)
6. "life_hack": 🤫 ทริกลึก / รู้งี้ซื้อนานแล้ว (Secret Trick & Life Hack)
7. "stop_scroll": ⚠️ เตือนภัยเชิงลบ / อย่าเพิ่งซื้อ! (Stop-Scroll Shock Hook)
8. "niche_target": 🧑‍💼 เจาะกลุ่มเฉพาะ สายออฟฟิศ/เกมเมอร์ (Target Audience Specific)
9. "longterm_review": ⭐ รีวิวเพื่อนเตือนเพื่อน ใช้จริง 3 เดือน (Real Experience)
10. "math_value": 💡 คำนวณความคุ้มค่าต่อวัน (Math & Value Breakdown)

แต่ละ Object ใน JSON ต้องมีโครงสร้างดังนี้ (คุมความยาวให้พากย์จบใน 30 - 38 วินาทีพอดี และเว้นวรรคก้อนความคิดใน script_lines):
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
    "ทุกคน ใครที่นั่งทำงานแล้วเริ่มปวดข้อมือร้าวถึงศอก ฟังทางนี้ด่วนเลยครับ",
    "นั่งพิมพ์ทั้งวัน ด้วยคีย์บอร์ดแบนๆ มือมันต้องเกร็ง ทรมานจนไม่อยากทำงานใช่ไหมครับ",
    "ผมบอกเลยว่าชีวิตเปลี่ยนแน่นอน พอได้มาลอง {{product_name}} คีย์บอร์ดเพื่อสุขภาพตัวใหม่ล่าสุด",
    "เค้าดีไซน์โค้งรูปคลื่น รับกับมือธรรมชาติ พร้อมเบาะรองข้อมือ Memory Foam นุ่มๆ พิมพ์สบายทั้งวันไม่เมื่อยเลยครับ",
    "รักข้อมือตัวเอง รีบกดสั่งราคาพิเศษ ในตะกร้าสีเหลือง ซ้ายล่างตอนนี้ได้เลยครับ"
  ],
  "tiktok_caption": "บอกลาอาการปวดข้อมือ! อัปเกรดชีวิตด้วย {{product_name}} คีย์บอร์ดเพื่อสุขภาพที่นุ่มสบายที่สุด พิกัดในตะกร้าเลย 👇",
  "tiktok_hashtags": "#นายหน้าtiktok #รีวิวของดี #ของมันต้องมี #tiktokป้ายยา #พิกัดในตะกร้า"
}}

ตอบกลับเฉพาะ JSON array เท่านั้น ห้ามใส่คำเกริ่นนำหรือ markdown formatting อื่น
"""
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            env_file = BASE_DIR / ".env"
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                resp = None
                for m_name in ["gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-3.5-flash-lite"]:
                    try:
                        print(f"[ProductScraper] Calling Gemini with model {m_name}...")
                        resp = client.models.generate_content(
                            model=m_name,
                            contents=prompt
                        )
                        if resp and resp.text:
                            print(f"[ProductScraper] Successfully received response from {m_name}")
                            break
                    except Exception as m_err:
                        print(f"[ProductScraper] Model {m_name} note: {m_err}")
                        continue
                response_text = (resp.text if resp else "") or ""
                
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

        # Robust Fallback 10-Angle Matrix (30-38s, strictly male tone)
        base_name = title[:30] or "สินค้าตัวนี้"
        from scripts.tts_sanitizer import TTSSanitizer
        fallback_angles = [
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
                    "ทุกคน ใครที่เบื่อกับปัญหาเดิมๆ ลองดูคลิปนี้ด่วนเลยครับ",
                    f"นี่เลย {base_name} ตัวช่วยใหม่ล่าสุด",
                    "วัสดุพรีเมียม ใช้งานง่าย สะดวกสบายขึ้นเยอะมาก",
                    "บอกเลยว่าช่วยประหยัดแรงและเวลาไปได้เยอะเลยครับ",
                    "พิกัดลดราคาพิเศษ จิ้มตะกร้าสีเหลืองซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"แก้ปัญหาเดิมๆ ได้จริง! {base_name} คุ้มค่ามาก พิกัดในตะกร้าซ้ายล่างเลยครับ 👇",
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
                    "ทุกคนครับ ในที่สุดของที่สั่งไว้ก็มาส่งแล้ว",
                    f"ตัวนี้คือ {base_name} ที่คนรีวิวกันเยอะมาก",
                    "แกะกล่องออกมาคือว้าวมาก วัสดุดีเกินราคาไปเยอะเลยครับ",
                    "สวยตรงปกไม่จกตา คุ้มค่าทุกบาทแน่นอน",
                    "รีบจิ้มตะกร้าสีเหลืองซ้ายล่างด่วนๆ ก่อนของจะหมดนะครับ"
                ],
                "tiktok_caption": f"แกะกล่องของจริง สวยตรงปกมาก! {base_name} พิกัดในตะกร้าซ้ายล่างเลยครับ 🛒✨",
                "tiktok_hashtags": "#แกะกล่อง #ของดีบอกต่อ #tiktokป้ายยา #fyp"
            },
            {
                "angle_id": "spec_review",
                "angle_name": "⚙️ รีวิวสเปกเจาะลึก / ฟังก์ชันจัดเต็ม",
                "badge": "เจาะลึกสเปก",
                "product_name": base_name,
                "hook_title": f"⚡ ทดสอบให้ดูจะๆ ทนจริงไหม? {base_name}",
                "pain_point": "ของราคาถูกมักพังง่าย ไม่ทนทาน",
                "key_features": "โครงสร้างแข็งแรง ฟังก์ชันจัดเต็ม ใช้งานหนักได้",
                "price_deal": "รับประกันคุณภาพ มีของพร้อมส่ง",
                "ad_tone": "tech_minimal",
                "script_lines": [
                    "วันนี้ผมจะมาเทสให้ดูแบบไม่ออมมือเลยว่าทนจริงไหม",
                    f"{base_name} ตัวนี้ใช้วัสดุเกรดพรีเมียมอย่างดี",
                    "ฟังก์ชันครบ ตอบโจทย์คนที่ชอบงานคุณภาพ",
                    "ใช้งานหนักแค่ไหนก็เอาอยู่ มั่นใจได้เลยครับ",
                    "สนใจกดดูรายละเอียดในตะกร้าซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"ทดสอบความทนทานให้ดูแบบชัดๆ {base_name} คุณภาพเกินราคาแน่นอนครับ 👇",
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
                    "หยุดก่อนครับ วันนี้มีดีลลับ Flash Sale มาบอกต่อ",
                    f"{base_name} จัดโปรลดแรงที่สุดในรอบเดือน",
                    "ได้ของแท้ 100% แถมส่งฟรีถึงหน้าบ้าน",
                    "ราคานี้เฉพาะในตะกร้านี้เท่านั้นนะครับ",
                    "รีบกดสั่งในตะกร้าซ้ายล่างก่อนโปรจะหมดนะครับ"
                ],
                "tiktok_caption": f"⚡ ดีลลับลดแรงวันนี้วันเดียว! {base_name} ส่งฟรี กดเก็บคูปองในตะกร้าด่วนครับ 🛍️",
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
                    "ใครที่กำลังลังเลว่าจะเปลี่ยนดีไหม ดูคลิปนี้เลยครับ",
                    "ฝั่งซ้ายคือแบบเดิมที่เคยใช้ ปัญหาเยอะ พังง่าย",
                    f"แต่ฝั่งขวาคือ {base_name} ชีวิตเปลี่ยนทันที",
                    "ใช้ง่ายกว่า ทนทานกว่า ไม่ต้องเสียเงินซื้อบ่อยๆ",
                    "อยากเปลี่ยนชีวิตให้ง่ายขึ้น จิ้มตะกร้าสีเหลืองซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"เทียบกันชัดๆ ทำไมต้องเปลี่ยนมาใช้ {base_name} ดูแล้วจะเข้าใจครับ! 👇",
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
                    "ทุกคน ใครชอบทริกช่วยให้ชีวิตง่ายขึ้น ดูนี่ด่วนเลยครับ",
                    f"นี่คือ {base_name} ไอเทมลับที่ช่วยประหยัดเวลาสุดๆ",
                    "แค่มีตัวนี้ติดไว้ อะไรๆ ก็สะดวกขึ้นเยอะมาก",
                    "ใช้แล้วจะพูดคำเดียวเลยว่า รู้งี้ซื้อตั้งนานแล้วครับ",
                    "พิกัดไอเทมลับ จิ้มในตะกร้าสีเหลืองซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"ไอเทมลับที่ช่วยให้ชีวิตง่ายขึ้น 10 เท่า! {base_name} พิกัดตะกร้าซ้ายล่างเลยครับ 💡",
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
                    "หยุดเลื่อนก่อนครับ ใครกำลังจะซื้อของประเภทนี้ ฟังด่วนเลย",
                    "ในตลาดมีของเลียนแบบเยอะมาก ใช้แป๊บเดียวพัง",
                    f"ถ้าจะเอาให้ชัวร์ ต้องเลือก {base_name} ตัวแท้เท่านั้น",
                    "คุณภาพการันตี วัสดุดี ใช้งานยาวๆ ไม่มีผิดหวังแน่นอนครับ",
                    "เพื่อความชัวร์ กดสั่งจากตะกร้าทางการซ้ายล่างตรงนี้ได้เลยครับ"
                ],
                "tiktok_caption": f"⚠️ เตือนแล้วนะครับ! เช็กให้ดีก่อนซื้อ {base_name} ของแท้กดในตะกร้าทางการเลยครับ 👇",
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
                    "ชาวออฟฟิศและสายจัดโต๊ะคอม ต้องดูคลิปนี้เลยครับ",
                    f"นี่คือ {base_name} ไอเทมที่ช่วยให้โต๊ะทำงานดูโปรขึ้น",
                    "ใช้งานสะดวก คล่องตัว ช่วยให้ทำงานและเล่นเกมได้ฟินขึ้น",
                    "มีติดโต๊ะไว้ ได้ใช้งานทุกวันแน่นอนครับ",
                    "พิกัดไอเทมจัดโต๊ะ จิ้มตะกร้าซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"ไอเทมที่ชาวจัดโต๊ะคอมและ WFH ต้องมี! {base_name} พิกัดในตะกร้าเลยครับ 🖥️✨",
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
                    "มารีวิวแบบไม่อวย ใช้จริงมาครบ 3 เดือนเต็มแล้วครับ",
                    f"{base_name} ตัวนี้บอกตรงๆ ว่าตอนแรกไม่คิดว่าจะทนขนาดนี้",
                    "ใช้ทุกวันแบบสมบุกสมบัน ไม่มีงอแง ไม่มีพังเลย",
                    "เป็นหนึ่งในของที่ซื้อมาแล้วรู้สึกคุ้มเงินที่สุดในปีนี้ครับ",
                    "ใครกำลังเล็งอยู่ ไม่ต้องคิดเยอะ จิ้มตะกร้าซ้ายล่างได้เลยครับ"
                ],
                "tiktok_caption": f"รีวิวหลังใช้จริง 3 เดือน {base_name} ทนจริงไม่จกตา กดสั่งในตะกร้าได้เลยครับ ⭐",
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
                    "มาคำนวณความคุ้มค่าให้ดู ว่าทำไมตัวนี้ถึงน่าลงทุนครับ",
                    f"{base_name} ราคาแค่หลักร้อย แต่ใช้งานได้หลายปี",
                    "หารเฉลี่ยออกมาตกวันละไม่ถึงบาทเดียว",
                    "เทียบกับความสะดวกและสุขภาพที่ได้ คือโคตรคุ้มเลยครับ",
                    "อย่ารอช้า รีบกดสั่งในราคาโปรโมชันที่ตะกร้าซ้ายล่างเลยครับ"
                ],
                "tiktok_caption": f"คิดแบบนักคำนวณ {base_name} ตกวันละไม่กี่สตางค์แต่คุ้มสุดๆ พิกัดในตะกร้าเลยครับ 👇",
                "tiktok_hashtags": "#คุ้มค่า #ประหยัดเงิน #ของดีราคาถูก #tiktokป้ายยา"
            }
        ]
        return TTSSanitizer.process_angles(fallback_angles[:count])

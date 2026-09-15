import re
import json
import os
import time
import html as html_lib
import socket
import ipaddress
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from typing import Dict, Any, List, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MAX_RENDERED_SOURCE_CHARS = 12000
MAX_RENDERED_DESCRIPTION_CHARS = 4000
MAX_PROMPT_SOURCE_CHARS = 6000
RENDERED_PAGE_WAIT_MS = 1800
RENDERED_PAGE_TIMEOUT_MS = 30000
RENDERED_CHALLENGE_WAIT_SECONDS = 60
RENDERED_PROFILE_DIR = BASE_DIR / "tools" / "tiktok_browser_profile"
RENDERED_SOURCE_FALLBACK = "สินค้าคุณภาพยอดนิยม การันตีของแท้"

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

# Target length per duration tier. The 5 core beats (Hook/Pain/Product/Feel/
# CTA) stay fixed at every tier -- what changes is how much room each beat
# gets, plus how many EXTRA_BEAT_BLOCKS get inserted between Product and CTA.
# word/char counts assume the same +15% TTS speed the original 30s rule was
# tuned for.
DURATION_SPECS = {
    "30s": {
        "label": "30 วินาที (สั้นกระชับ)",
        "seconds_range": "30 - 38 วินาที",
        "word_range": "70 - 85 คำ",
        "char_range": "280 - 350 ตัวอักษร",
        "max_seconds": "40 วินาที",
        "default_extra_beats": 0,
    },
    "60s": {
        "label": "60 วินาที (มาตรฐาน)",
        "seconds_range": "55 - 65 วินาที",
        "word_range": "140 - 165 คำ",
        "char_range": "560 - 660 ตัวอักษร",
        "max_seconds": "70 วินาที",
        "default_extra_beats": 2,
    },
    "90s": {
        "label": "90 วินาที (แอดวานซ์ ละเอียด)",
        "seconds_range": "85 - 95 วินาที",
        "word_range": "210 - 245 คำ",
        "char_range": "840 - 980 ตัวอักษร",
        "max_seconds": "100 วินาที",
        "default_extra_beats": 4,
    },
}
DEFAULT_DURATION = "30s"

# The 10 content angles the matrix normally picks from, in order. Shared
# between the "give me the full matrix" prompt (lists all of them) and a
# single-angle reroll's prompt (looks up just the one requested here) so
# the label/description text for a given angle_id can't drift between the
# two call sites.
ANGLE_CATALOG = {
    "pain_point": {"label": "😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน", "description": "Problem / Agitation / Solution"},
    "spec_review": {"label": "⚙️ รีวิวสเปกเจาะลึก / ฟังก์ชันจัดเต็ม", "description": "Deep Spec Review & Technical Features"},
    "unboxing": {"label": "🛍️ แกะกล่องว้าว / ของมันต้องมี", "description": "Unboxing & First Impression"},
    "fomo_deal": {"label": "🔥 FOMO โปรไฟลุก / คุ้มจนต้องแย่ง", "description": "Flash Deal & Urgency"},
    "comparison": {"label": "🆚 เทียบของเดิม vs ของใหม่", "description": "Comparison Matrix"},
    "life_hack": {"label": "🤫 ทริกลึก / รู้งี้ซื้อนานแล้ว", "description": "Secret Trick & Life Hack"},
    "stop_scroll": {"label": "⚠️ เตือนภัยเชิงลบ / อย่าเพิ่งซื้อ!", "description": "Stop-Scroll Shock Hook"},
    "niche_target": {"label": "🧑‍💼 เจาะกลุ่มเฉพาะ สายออฟฟิศ/เกมเมอร์", "description": "Target Audience Specific"},
    "longterm_review": {"label": "⭐ รีวิวเพื่อนเตือนเพื่อน ใช้จริง 3 เดือน", "description": "Real Experience"},
    "math_value": {"label": "💡 คำนวณความคุ้มค่าต่อวัน", "description": "Math & Value Breakdown"},
}

# Optional beats a caller can request (checkbox in the UI, or the default mix
# for 60s/90s when the caller doesn't specify which ones). Each entry is
# inserted as its own numbered beat between the core Product and CTA beats --
# the AI is told exactly what content belongs in it, so two different beats
# requested together don't collapse into the same paragraph.
EXTRA_BEAT_BLOCKS = {
    "spec_detail": {
        "label": "สเปก/สรรพคุณละเอียด",
        "instruction": (
            "เจาะสเปกเทคนิคแบบเป็นทางการให้ครบถ้วนกว่าเดิม (ตัวเลข หน่วยวัด มาตรฐานที่สินค้ามี) "
            "อธิบายว่าสเปกแต่ละอย่างส่งผลต่อการใช้งานจริงยังไง ไม่ใช่แค่ท่องสเปกเฉยๆ"
        ),
    },
    "comparison": {
        "label": "เปรียบเทียบของเดิม vs ของใหม่",
        "instruction": (
            "เทียบให้เห็นภาพชัดระหว่างของแบบเดิมที่คนส่วนใหญ่ใช้อยู่ กับสินค้านี้ "
            "ชี้จุดที่ต่างกันจริงและทำไมของใหม่ถึงคุ้มกว่า ไม่ใช่แค่บอกว่า \"ดีกว่า\" ลอยๆ"
        ),
    },
    "use_cases": {
        "label": "การใช้งานจริง/เคสตัวอย่างหลายสถานการณ์",
        "instruction": (
            "ยกตัวอย่างสถานการณ์การใช้งานจริงอย่างน้อย 2-3 สถานการณ์ที่ต่างกัน "
            "(เช่น ใช้ที่บ้าน ใช้นอกสถานที่ ใช้ตอนทำงาน) ให้คนดูเห็นภาพว่าตัวเองจะใช้ตอนไหนได้บ้าง"
        ),
    },
    "faq": {
        "label": "ตอบคำถามที่มักเจอ (FAQ) / ข้อกังวล",
        "instruction": (
            "หยิบข้อกังวลที่คนมักถามก่อนซื้อของแบบนี้ 1-2 ข้อ (เช่น เรื่องความทนทาน การรับประกัน ความเข้ากันได้) "
            "มาตอบให้หายกังวลตรงๆ แบบพูดคุยเป็นกันเอง ไม่ใช่ตอบทางการเกินไป"
        ),
    },
}

# Stable content labels shown as badges in the studio. These are derived by
# the app from the selected angle and extra beats rather than trusted from AI
# output, so a reroll cannot silently change what kind of content it is.
CONTENT_TYPE_CATALOG = {
    "problem_solution": {"label": "ปัญหา → ทางออก", "description": "เล่าปัญหาของผู้ชมและวิธีที่สินค้าช่วยแก้"},
    "specs": {"label": "สเปก/สรรพคุณ", "description": "บอกข้อมูลจำเพาะ ฟังก์ชัน และประโยชน์ของสินค้า"},
    "unboxing": {"label": "แกะกล่อง / First Impression", "description": "เปิดกล่องและเล่าความรู้สึกแรกที่เห็นหรือได้ลอง"},
    "promotion": {"label": "โปรโมชัน / ความคุ้มค่า", "description": "เน้นข้อเสนอ ราคา และเหตุผลที่ควรตัดสินใจตอนนี้"},
    "comparison": {"label": "เปรียบเทียบ", "description": "เทียบของเดิมกับของใหม่ให้เห็นความต่าง"},
    "tips": {"label": "ทริก / How-to", "description": "สอนวิธีใช้หรือทริกที่ทำให้ชีวิตสะดวกขึ้น"},
    "warning": {"label": "ข้อควรระวัง", "description": "ชี้จุดต้องเช็กและความเสี่ยงก่อนซื้อ"},
    "target_audience": {"label": "เจาะกลุ่มผู้ใช้", "description": "สื่อสารกับกลุ่มคนที่มีบริบทการใช้งานเฉพาะ"},
    "experience": {"label": "ประสบการณ์ใช้งานจริง", "description": "เล่าผลจากการใช้จริงและความคุ้มค่าในระยะยาว"},
    "use_cases": {"label": "การใช้งานจริง", "description": "ยกตัวอย่างการใช้ในหลายสถานการณ์"},
    "faq": {"label": "FAQ / ข้อกังวล", "description": "ตอบคำถามที่ผู้ชมมักสงสัยก่อนซื้อ"},
    "value": {"label": "คำนวณความคุ้มค่า", "description": "แจกแจงความคุ้มค่าเมื่อเทียบกับราคาและอายุการใช้งาน"},
}

ANGLE_CONTENT_TYPES = {
    "pain_point": ["problem_solution"],
    "spec_review": ["specs"],
    "unboxing": ["unboxing"],
    "fomo_deal": ["promotion"],
    "comparison": ["comparison"],
    "life_hack": ["tips"],
    "stop_scroll": ["warning"],
    "niche_target": ["target_audience"],
    "longterm_review": ["experience"],
    "math_value": ["value"],
}

EXTRA_BEAT_CONTENT_TYPES = {
    "spec_detail": "specs",
    "comparison": "comparison",
    "use_cases": "use_cases",
    "faq": "faq",
}


def content_types_for_angle(angle_id: Optional[str], extra_beats: Optional[List[str]] = None) -> List[str]:
    """Return stable, deduplicated content-type keys for an angle."""
    result = list(ANGLE_CONTENT_TYPES.get(angle_id or "", []))
    for beat in extra_beats or []:
        content_type = EXTRA_BEAT_CONTENT_TYPES.get(beat)
        if content_type and content_type not in result:
            result.append(content_type)
    return result


def apply_angle_content_metadata(
    angle: Dict[str, Any],
    *,
    angle_id: Optional[str] = None,
    extra_beats: Optional[List[str]] = None,
    preserve_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Attach canonical topic identity and deterministic content badges."""
    resolved_id = angle_id or angle.get("angle_id")
    target = ANGLE_CATALOG.get(resolved_id or "")
    if resolved_id:
        angle["angle_id"] = resolved_id
    if target:
        angle["angle_name"] = preserve_name or target["label"]
        angle["angle_description"] = target["description"]
    angle["content_types"] = content_types_for_angle(resolved_id, extra_beats)
    return angle


def _hostname_allowed(hostname: str) -> bool:
    """True if `hostname` is, or is a subdomain of, an allowed scrape domain."""
    host = (hostname or "").lower().rstrip(".")
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in ALLOWED_SCRAPE_DOMAINS)


def _validate_public_http_url(url: str, *, require_allowed_domain: bool) -> None:
    """
    Rejects any URL that is not a plain http(s) request resolving to a
    public, non-internal IP address. When require_allowed_domain is True,
    the host must also be (a subdomain of) ALLOWED_SCRAPE_DOMAINS.

    This app has no authentication and CORS is wide open, so any web page
    the user has open can hit this backend's endpoints. Without this check
    a URL field is a full SSRF primitive: an attacker supplies
    http://169.254.169.254/... (cloud metadata / IAM credential theft once
    this is deployed), http://127.0.0.1:8000/... (the app's own API), or
    http://10.x/192.168.x/172.16-31.x (internal network scanning, with the
    fetched content echoed back as an oracle). Raises ValueError on
    rejection so existing callers' `except ValueError` handling surfaces a
    clear message instead of the request silently going through.
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

    if require_allowed_domain and not _hostname_allowed(hostname):
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


def _validate_scrape_url(url: str) -> None:
    _validate_public_http_url(url, require_allowed_domain=True)


def _validate_image_url(url: str) -> None:
    """Same SSRF protections as _validate_scrape_url, minus the product-page
    domain allowlist -- scraped product images legitimately live on CDN
    hosts (e.g. *.ibyteimg.com, *.susercontent.com) distinct from the page
    domain, so that allowlist doesn't apply here."""
    _validate_public_http_url(url, require_allowed_domain=False)


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


class _SafeImageRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Same purpose as _SafeRedirectHandler but for image CDN fetches, which
    routinely redirect across hosts outside ALLOWED_SCRAPE_DOMAINS -- so each
    hop is checked with _validate_image_url instead."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_image_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_safe_opener(*handlers):
    return urllib.request.build_opener(_SafeRedirectHandler(), *handlers)


def _build_safe_image_opener(*handlers):
    return urllib.request.build_opener(_SafeImageRedirectHandler(), *handlers)


MAX_REFERENCE_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB cap per reference image


def _download_image_bytes(url: str) -> "tuple[bytes, str]":
    """Downloads a scraped product-image URL for Gemini vision input.

    Returns (data, mime_type). Raises ValueError/OSError on any failure --
    callers already wrap each reference image in try/except so one bad URL
    is skipped rather than failing the whole generation call.
    """
    _validate_image_url(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": BROWSER_UA,
        "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
    })
    with _build_safe_image_opener().open(req, timeout=15) as resp:
        content_type = (resp.headers.get_content_type() or "").lower()
        data = resp.read(MAX_REFERENCE_IMAGE_BYTES + 1)
    if len(data) > MAX_REFERENCE_IMAGE_BYTES:
        raise ValueError(f"Image at {url} exceeds {MAX_REFERENCE_IMAGE_BYTES} byte cap")

    mime_by_type = {
        "image/jpeg": "image/jpeg", "image/jpg": "image/jpeg",
        "image/png": "image/png", "image/webp": "image/webp",
        "image/heic": "image/heic", "image/heif": "image/heif",
    }
    mime = mime_by_type.get(content_type)
    if not mime:
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower().lstrip(".")
        mime = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp",
            "heic": "image/heic", "heif": "image/heif",
        }.get(ext, "image/jpeg")
    return data, mime


def _extract_meta(html: str, property_name: str) -> Optional[str]:
    """Extract content from meta tags by property or name."""
    pattern = rf'<meta[^>]+(?:property|name)=[\'"]{re.escape(property_name)}[\'"][^>]+content=[\'"]([^\'"]+)[\'"]'
    match = re.search(pattern, html, re.I)
    if match:
        return html_lib.unescape(match.group(1).strip())
    pattern_alt = rf'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+(?:property|name)=[\'"]{re.escape(property_name)}[\'"]'
    match_alt = re.search(pattern_alt, html, re.I)
    if match_alt:
        return html_lib.unescape(match_alt.group(1).strip())
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

def _normalise_rendered_text(value: str) -> str:
    """Collapse browser ``inner_text`` into bounded, useful source text."""
    lines = []
    previous = None
    bullet_pending = False
    for raw_line in (value or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line == "·":
            bullet_pending = True
            continue
        if bullet_pending:
            line = "· " + line
            bullet_pending = False
        if not line or line == previous:
            continue
        lines.append(line)
        previous = line
    return "\n".join(lines)[:MAX_RENDERED_SOURCE_CHARS]


def _source_text_without_duplicate(description: str, raw_text: str) -> str:
    """Keep raw-source lines that are not already represented by description.

    Product pages often expose the same description once as a dedicated field
    and once inside the full page text (sometimes preceded by the title). The
    full raw text remains persisted for inspection, but prompts and summaries
    should not feed the same paragraph to the model twice.
    """
    description_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in (description or "").splitlines()
        if line.strip()
    ]
    duplicate_lines = {line.casefold() for line in description_lines}
    raw_lines = []
    for line in (raw_text or "").splitlines():
        compact = re.sub(r"\s+", " ", line).strip()
        if compact and compact.casefold() not in duplicate_lines:
            raw_lines.append(compact)
    return "\n".join(raw_lines)


def _normalise_image_metadata(value: Any) -> Dict[str, Any]:
    """Keep the image extractor's response inside the product metadata shape."""
    if not isinstance(value, dict):
        raise ValueError("ผลอ่านจากรูปต้องเป็น JSON object")

    def text(key: str) -> str:
        raw = value.get(key, "")
        return str(raw).strip() if isinstance(raw, (str, int, float)) else ""

    def items(key: str) -> list:
        raw = value.get(key, [])
        if not isinstance(raw, list):
            return []
        return [item.strip() if isinstance(item, str) else item for item in raw if item not in (None, "")]

    return {
        "name": text("name"),
        "description": text("description"),
        "raw_text": text("raw_text"),
        "specs": items("specs"),
        "selling_points": items("selling_points"),
        "pain_points": items("pain_points"),
        "source_warning": text("source_warning"),
        "metadata_source": "vision_image",
    }


class _VisibleHTMLTextParser(HTMLParser):
    """Extract server-rendered text while ignoring scripts and style payloads."""

    _IGNORED_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._IGNORED_TAGS:
            self._ignored_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data):
        if not self._ignored_depth and data.strip():
            self.parts.append(data)


def _extract_html_product_text(raw_html: str) -> str:
    """Extract the product-description block from SSR HTML when available."""
    parser = _VisibleHTMLTextParser()
    try:
        parser.feed(raw_html or "")
        parser.close()
    except Exception:
        return ""
    text = _normalise_rendered_text("\n".join(parser.parts))
    marker_positions = [
        text.find(marker) for marker in (
            "Product description",
            "คำอธิบายสินค้า",
            "รายละเอียดสินค้า",
        ) if text.find(marker) >= 0
    ]
    if not marker_positions:
        return ""
    start = min(marker_positions)
    content = text[start:]
    for marker in ("View more", "ดูเพิ่มเติม"):
        end = content.find(marker)
        if end > 0:
            content = content[:end]
            break
    content = content.replace("Product description\n", "", 1)
    content = content.replace("คำอธิบายสินค้า\n", "", 1)
    content = content.replace("รายละเอียดสินค้า\n", "", 1)
    return content.strip()


def _extract_section(text: str, starts, ends) -> str:
    """Return a bounded section from normalized product source text."""
    start = -1
    for marker in starts:
        position = text.find(marker)
        if position >= 0 and (start < 0 or position < start):
            start = position + len(marker)
    if start < 0:
        return ""
    end_positions = [text.find(marker, start) for marker in ends]
    end_positions = [position for position in end_positions if position >= 0]
    end = min(end_positions) if end_positions else len(text)
    return text[start:end].strip()


def _looks_like_browser_challenge(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in (
        "verify to continue",
        "drag the puzzle",
        "security check",
        "ตรวจสอบความปลอดภัย",
    ))


def _scrape_rendered_page(url: str) -> Dict[str, Any]:
    """Read the post-JavaScript product page without bypassing its challenge.

    TikTok frequently serves a challenge to non-browser clients. We first try
    a normal headless Chrome page; when that challenge appears, we open the
    existing persistent Chrome profile so the user can complete it or use a
    saved session. No CAPTCHA/anti-bot bypass is attempted.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"warning": "ยังไม่ได้ติดตั้ง Playwright สำหรับอ่านหน้าเว็บที่ render ด้วย browser"}

    def read_page(page: Any) -> Dict[str, Any]:
        page.wait_for_timeout(RENDERED_PAGE_WAIT_MS)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        body_text = _normalise_rendered_text(page.locator("body").inner_text(timeout=5000))
        images = page.locator("img").evaluate_all(
            """imgs => imgs.map(img => img.currentSrc || img.src || '')
                .filter(src => /^https?:\\/\\//i.test(src))"""
        )
        return {
            "title": page.title().strip(),
            "raw_text": body_text,
            "images": images[:20],
            "challenge": _looks_like_browser_challenge(body_text),
        }

    with sync_playwright() as playwright:
        browser = None
        context = None
        try:
            try:
                browser = playwright.chromium.launch(headless=True, channel="chrome")
            except Exception:
                browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100}, locale="th-TH")
            page.goto(url, wait_until="domcontentloaded", timeout=RENDERED_PAGE_TIMEOUT_MS)
            snapshot = read_page(page)

            if snapshot["challenge"]:
                browser.close()
                browser = None
                try:
                    context = playwright.chromium.launch_persistent_context(
                        str(RENDERED_PROFILE_DIR),
                        channel="chrome",
                        headless=False,
                        args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                        viewport=None,
                    )
                except Exception:
                    context = playwright.chromium.launch_persistent_context(
                        str(RENDERED_PROFILE_DIR),
                        headless=False,
                        args=["--start-maximized"],
                        viewport=None,
                    )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=RENDERED_PAGE_TIMEOUT_MS)
                deadline = time.monotonic() + RENDERED_CHALLENGE_WAIT_SECONDS
                while time.monotonic() < deadline:
                    snapshot = read_page(page)
                    if not snapshot["challenge"] and len(snapshot["raw_text"]) >= 80:
                        break
                    page.wait_for_timeout(1500)
                if snapshot["challenge"]:
                    return {"warning": "TikTok ขอ Security Check จึงยังอ่านรายละเอียดหน้าเว็บไม่ได้"}

            if len(snapshot["raw_text"]) < 80:
                return {"warning": "หน้าเว็บ render แล้วแต่ไม่มีข้อความรายละเอียดที่อ่านได้"}
            return snapshot
        except Exception as exc:
            return {"warning": f"เปิด browser เพื่ออ่านรายละเอียดสินค้าไม่สำเร็จ ({exc})"}
        finally:
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()


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
        specs = []
        selling_points = []
        metadata_source = "slug_fallback"
        source_warning = ""

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

                meta_description = (
                    _extract_meta(raw_html, "og:description")
                    or _extract_meta(raw_html, "twitter:description")
                    or _extract_meta(raw_html, "description")
                )
                html_product_text = _extract_html_product_text(raw_html)
                description = html_product_text or meta_description
                price = _extract_meta(raw_html, "product:price:amount") or _extract_meta(raw_html, "og:price:amount")
                
                og_img = _extract_meta(raw_html, "og:image") or _extract_meta(raw_html, "twitter:image")
                if og_img and og_img.startswith("http"):
                    images.append(og_img)

                img_matches = re.findall(r'<img[^>]+src=[\'"](https?://[^\'"]+\.(?:jpg|jpeg|png|webp)[^\'"]*)[\'"]', raw_html, re.I)
                for img in img_matches[:8]:
                    if img not in images and "icon" not in img.lower() and "logo" not in img.lower():
                        images.append(img)

                if html_product_text:
                    selling_section = _extract_section(
                        html_product_text,
                        ("คุณสมบัติเด่นของ", "จุดเด่นพิเศษของ"),
                        ("ตัวเลือกสินค้า", "ข้อมูลทางเทคนิค", "ข้อควรระวัง"),
                    )
                    specs_section = _extract_section(
                        html_product_text,
                        ("ข้อมูลทางเทคนิค",),
                        ("ข้อควรระวัง", "#"),
                    )
                    selling_points = [
                        line.lstrip("· ").strip()
                        for line in selling_section.splitlines()
                        if line.strip("· ")
                    ]
                    specs = [
                        line.lstrip("· ").strip()
                        for line in specs_section.splitlines()
                        if line.strip("· ")
                    ]
                    raw_text = f"{title}\n{html_product_text}".strip()
                    metadata_source = "html_body"
                elif description:
                    raw_text = f"{title}\n{description}"
                    metadata_source = "html_meta"
        except Exception as e:
            print(f"[ProductScraper] Direct fetch note ({e}), using proxy/slug extraction...")

        # TikTok product descriptions are commonly injected into the DOM by
        # JavaScript, so urllib can still find images while seeing no product
        # copy at all. Try a real browser only when the shallow source did not
        # provide a usable description. The browser helper deliberately stops
        # at the site's own challenge instead of bypassing it.
        if platform == "tiktok" and not description:
            rendered = _scrape_rendered_page(resolved_url)
            rendered_text = rendered.get("raw_text", "")
            if rendered_text:
                rendered_title = rendered.get("title", "")
                if rendered_title and rendered_title.lower() not in {"security check", "verify to continue"}:
                    title = rendered_title
                raw_text = rendered_text
                description = rendered_text[:MAX_RENDERED_DESCRIPTION_CHARS]
                metadata_source = "browser_dom"
                for image in rendered.get("images", []):
                    if image not in images and len(images) < 20:
                        images.append(image)
            else:
                source_warning = rendered.get("warning", "")

        clean_title = title.split("|")[0].split("- Shopee")[0].strip() or "สินค้าแนะนำ"

        return {
            "title": clean_title,
            "url": resolved_url,
            "platform": platform,
            "price_note": price or "ราคาพิเศษในตะกร้า",
            "description": description[:MAX_RENDERED_DESCRIPTION_CHARS] if description else RENDERED_SOURCE_FALLBACK,
            "images": images,
            "specs": specs,
            "selling_points": selling_points,
            "raw_text": raw_text,
            "metadata_source": metadata_source,
            **({"source_warning": source_warning} if source_warning else {}),
        }

    @classmethod
    def extract_metadata_from_images(
        cls,
        image_paths: Optional[List[str]] = None,
        product_name: str = "",
    ) -> Dict[str, Any]:
        """Extract product facts from reference images without inventing claims."""
        paths = [path for path in (image_paths or []) if path][:8]
        if not paths:
            raise ValueError("ยังไม่มีรูปอ้างอิงให้อ่าน")

        from scripts.config import get_gemini_api_keys
        api_keys = get_gemini_api_keys()
        if not api_keys:
            raise RuntimeError("ยังไม่ได้ตั้งค่า GEMINI_API_KEY สำหรับอ่านข้อมูลจากรูป")
        api_key = api_keys[0]

        from scripts.quota import check_budget
        check_budget(task="content_matrix")
        prompt = f"""
คุณคือผู้ตรวจสอบข้อมูลสินค้าแบบระมัดระวัง อ่านเฉพาะสิ่งที่มองเห็นได้จริงจากรูปอ้างอิง
สินค้าเดิม (ถ้ามี): {product_name or 'ไม่ทราบชื่อ'}

ตอบเป็น JSON object เท่านั้น ห้ามใส่ markdown โดยมีโครงสร้าง:
{{
  "name": "ชื่อสินค้า/ซีรีส์ที่อ่านได้ ถ้าไม่ชัดให้ใช้ค่าว่าง",
  "description": "สรุปคำอธิบายและสรรพคุณจากข้อมูลที่อ่านได้จริง 1 ย่อหน้า",
  "raw_text": "ข้อความสำคัญที่อ่านได้จากรูป เรียงเป็นบรรทัด",
  "specs": ["สเปกพร้อมตัวเลขและหน่วยที่อ่านได้จริง"],
  "selling_points": ["จุดขายหรือคุณสมบัติที่เห็นชัดในรูป"],
  "pain_points": ["ปัญหาหรือกลุ่มผู้ใช้ที่รูปกล่าวถึง ถ้าไม่มีให้เป็น []"],
  "source_warning": "ระบุเฉพาะส่วนที่ตัวเล็ก/เบลอ/อ่านไม่แน่ใจ ถ้าไม่มีให้เป็นค่าว่าง"
}}

กฎความถูกต้อง:
- ห้ามเดาตัวเลข รุ่น วัสดุ หรือคุณสมบัติที่อ่านไม่ชัด
- ถ้ารูปมีหลายรุ่น ให้แยกเป็นรายการใน specs/selling_points และระบุชื่อรุ่นให้ชัด
- คงชื่อแบรนด์ รุ่น และศัพท์เทคนิคภาษาอังกฤษตามที่ปรากฏในรูป
- ห้ามใส่ข้อมูลจากความรู้ทั่วไปนอกภาพ
""".strip()

        from google import genai
        from google.genai import types
        image_parts = []
        for image_path in paths:
            try:
                if isinstance(image_path, str) and image_path.lower().startswith(("http://", "https://")):
                    data, mime = _download_image_bytes(image_path)
                else:
                    path = Path(image_path)
                    if not path.is_absolute():
                        path = BASE_DIR / path
                    data = path.read_bytes()
                    mime = {
                        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".png": "image/png", ".webp": "image/webp",
                        ".heic": "image/heic", ".heif": "image/heif",
                    }.get(path.suffix.lower(), "image/jpeg")
                image_parts.append(types.Part.from_bytes(data=data, mime_type=mime))
            except Exception as image_error:
                print(
                    f"[ProductScraper] Skipping unreadable metadata image {image_path}: "
                    f"{ascii(image_error)}"
                )

        if not image_parts:
            raise ValueError("อ่านไฟล์รูปอ้างอิงไม่ได้")

        client = genai.Client(api_key=api_key)
        response = None
        for model_name in ["gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-3.5-flash-lite"]:
            try:
                response = client.models.generate_content(model=model_name, contents=[prompt, *image_parts])
                if response and response.text:
                    break
            except Exception as model_error:
                print(
                    f"[ProductScraper] Image metadata model {model_name} note: "
                    f"{ascii(model_error)}"
                )
                if "429" in str(model_error) or "RESOURCE_EXHAUSTED" in str(model_error):
                    raise

        if not response or not response.text:
            raise RuntimeError("AI ไม่ส่งผลลัพธ์จากรูปกลับมา")
        cleaned = re.sub(r'^```(?:json)?\s*', '', response.text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()
        return _normalise_image_metadata(json.loads(cleaned))

    @classmethod
    def generate_content_matrix(
        cls,
        product_data: Dict[str, Any],
        count: int = 10,
        image_paths: Optional[List[str]] = None,
        duration: str = DEFAULT_DURATION,
        extra_beats: Optional[List[str]] = None,
        angle_id_override: Optional[str] = None,
        avoid_angles: Optional[List[str]] = None,
        batch_label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generates full 10-Angle Master Content Matrix in natural Thai spoken language.

        image_paths (product photos, spec-sheet or review screenshots) are
        sent to Gemini as actual image content alongside the prompt -- not
        just used for a thumbnail -- so specs/features the user only has as a
        screenshot (no URL, no typed description) still reach the model.

        duration selects a DURATION_SPECS tier ("30s"/"60s"/"90s") -- every
        tier keeps the same 5 core beats (Hook/Pain/Product/Feel/CTA), only
        the target length and the number of inserted extra beats change.

        extra_beats is a list of EXTRA_BEAT_BLOCKS keys to insert between the
        core Product and CTA beats. None means "use this tier's default mix"
        (DURATION_SPECS[duration]["default_extra_beats"] beats, chosen in
        EXTRA_BEAT_BLOCKS order) -- pass an explicit list (including []) to
        override that, e.g. from a UI checkbox selection.

        angle_id_override, when set to one of ANGLE_CATALOG's keys, asks for
        exactly that one angle back (a script reroll) instead of the normal
        "pick from the full 10-angle catalog" behavior -- count is ignored
        in that case (always exactly 1 result).
        """
        title = product_data.get("title", "")
        desc = product_data.get("description", "")
        price = product_data.get("price_note", "")
        raw = product_data.get("raw_text", "")
        raw_without_duplicate = _source_text_without_duplicate(desc, raw)
        specs = product_data.get("specs", [])
        selling_points = product_data.get("selling_points", [])
        pain_points = product_data.get("pain_points", [])
        structured_source = "\n".join(
            value for value in (
                f"สเปก: {specs}" if specs else "",
                f"จุดขาย: {selling_points}" if selling_points else "",
                f"Pain points: {pain_points}" if pain_points else "",
            ) if value
        )

        spec = DURATION_SPECS.get(duration, DURATION_SPECS[DEFAULT_DURATION])
        if extra_beats is None:
            n = spec["default_extra_beats"]
            extra_beats = list(EXTRA_BEAT_BLOCKS.keys())[:n]
        active_beats = [EXTRA_BEAT_BLOCKS[b] for b in extra_beats if b in EXTRA_BEAT_BLOCKS]

        next_rule_num = 8
        if image_paths:
            image_rule = (
                f"\n{next_rule_num}. **ภาพที่แนบมาด้วย (Reference Images)**:\n"
                "   - ผู้ใช้แนบภาพหน้าจอสินค้า/สเปกชีท/รีวิวมาด้วย ให้อ่านสรรพคุณ สเปก จุดเด่น และรายละเอียดจากภาพเหล่านั้นโดยตรง\n"
                "   - หากข้อมูลในภาพขัดแย้งกับข้อความด้านบน ให้ยึดข้อมูลในภาพเป็นหลัก เพราะเป็นข้อมูลจริงจากสินค้า\n"
            )
            next_rule_num += 1
        else:
            image_rule = ""

        beat_count = 5 + len(active_beats)
        _example_core = [
            "ทุกคน ใครที่นั่งทำงานแล้วเริ่มปวดข้อมือร้าวถึงศอก ฟังทางนี้ด่วนเลยครับ",
            "นั่งพิมพ์ทั้งวัน ด้วยคีย์บอร์ดแบนๆ มือมันต้องเกร็ง ทรมานจนไม่อยากทำงานใช่ไหมครับ",
            "ผมบอกเลยว่าชีวิตเปลี่ยนแน่นอน พอได้มาลอง {{product_name}} คีย์บอร์ดเพื่อสุขภาพตัวใหม่ล่าสุด",
        ]
        _example_extra = [
            f"(ตัวอย่างท่อนเสริม \"{b['label']}\" — พูดตามเนื้อหาจริงของสินค้านี้ ไม่ใช่ก๊อปประโยคนี้ไปเฉยๆ)"
            for b in active_beats
        ]
        _example_tail = [
            "เค้าดีไซน์โค้งรูปคลื่น รับกับมือธรรมชาติ พร้อมเบาะรองข้อมือ Memory Foam นุ่มๆ พิมพ์สบายทั้งวันไม่เมื่อยเลยครับ",
            "รักข้อมือตัวเอง รีบกดสั่งราคาพิเศษ ในตะกร้าสีเหลือง ซ้ายล่างตอนนี้ได้เลยครับ",
        ]
        example_script_lines_json = json.dumps(
            _example_core + _example_extra + _example_tail, ensure_ascii=False, indent=4
        )

        if active_beats:
            extra_beat_rule_num = next_rule_num
            extra_beat_rule = (
                f"\n{extra_beat_rule_num}. **ท่อนเสริมที่ต้องแทรกระหว่างท่อนที่ 3 (เปิดตัวสินค้า) กับท่อนสุดท้าย (CTA) "
                f"รวม {len(active_beats)} ท่อน (Extra Content Beats)**:\n"
                + "\n".join(
                    f"   - {b['label']}: {b['instruction']}"
                    for b in active_beats
                )
                + "\n   - แต่ละท่อนเสริมนับเป็นท่อนพูดของตัวเองในลิสต์ script_lines "
                  "(ไม่ใช่ยัดรวมเข้าไปในท่อนอื่น) เรียงต่อกันอย่างเป็นธรรมชาติ ไม่ใช่แค่แปะต่อกันดื้อๆ\n"
            )
            beat_structure_ref = f"4/{extra_beat_rule_num}"
        else:
            extra_beat_rule = ""
            beat_structure_ref = "4"

        if angle_id_override:
            target = ANGLE_CATALOG.get(angle_id_override)
            if target is None:
                raise ValueError(f"ไม่รู้จัก angle_id '{angle_id_override}'")
            angle_list_section = (
                f'จงสร้างผลลัพธ์เป็น JSON Array ที่มี Object เดียวเท่านั้น '
                f'สำหรับมุม "{angle_id_override}": {target["label"]} ({target["description"]}) '
                f"เขียนสคริปต์ใหม่ทั้งหมดสำหรับมุมนี้โดยเฉพาะ ห้ามสร้างมุมอื่น "
                f"ห้ามเปลี่ยน angle_id หรือ angle_name เพราะเป็นหัวข้อเดิมของผู้ใช้"
            )
        else:
            catalog_lines = "\n".join(
                f'{i}. "{aid}": {a["label"]} ({a["description"]})'
                for i, (aid, a) in enumerate(ANGLE_CATALOG.items(), 1)
            )
            angle_list_section = (
                f"จงสร้างผลลัพธ์เป็น JSON Array ที่มี {count} Object ตาม 10 มุมมองนี้:\n{catalog_lines}"
            )

        avoid_section = ""
        if avoid_angles:
            clean_avoids = [a.strip() for a in avoid_angles if a and a.strip()]
            if clean_avoids:
                avoid_list_str = "\n".join(f"   - {item}" for item in clean_avoids)
                avoid_section = (
                    f"\n# ข้อกำหนดพิเศษสำหรับ {batch_label or 'ล็อตใหม่'} (ต้องคิดมุมใหม่ไม่ซ้ำเดิม):\n"
                    f"สินค้านี้เคยสร้างสคริปต์ในมุมมองและประเด็นเหล่านี้ไปแล้ว:\n{avoid_list_str}\n"
                    f"- **ห้ามคิดมุมและประเด็นซ้ำกับรายการด้านบน**: กรุณาคิดมุมมองการขายใหม่ แง่มุมการใช้งานใหม่ หรือข้อกังวลใหม่ที่ไม่ซ้ำ เพื่อให้ได้เนื้อหาที่สดใหม่ 100%\n"
                )

        prompt = f"""
# Role & Objective
คุณคือ "ยอดนักขาย TikTok และครีเอเตอร์สายรีวิวมือโปรระดับท็อปของไทย" ที่เชี่ยวชาญด้านจิตวิทยาการโน้มน้าวใจ (Persuasive Copywriting & Neuromarketing) และการแต่งบทพูดสำหรับ AI Voice Engine ให้พากย์ได้เป็นธรรมชาติ มีจังหวะหายใจเหมือนมนุษย์พูดจริง 100%
ช่วยวิเคราะห์ข้อมูลสินค้าด้านล่างนี้ แล้วแตกเป็น "10 มุมมองการป้ายยา (Content Angles Master Matrix)" ที่ดึงดูดใจ ใช้ภาษาพูดธรรมชาติเหมือนเพื่อนสนิทมาบอกต่อของดี มีจังหวะวรรคตอนที่น่าฟัง และปิดการขายได้จริง

ข้อมูลสินค้า:
- ชื่อ/หัวข้อ: {title}
- รายละเอียด: {desc}
- ราคา/โปรโมชั่น: {price}
- ข้อมูลสกัดเพิ่มเติม: {structured_source}
- ข้อมูลต้นฉบับจากแหล่งข้อมูล (เฉพาะส่วนที่ไม่ซ้ำกับรายละเอียด): {raw_without_duplicate[:MAX_PROMPT_SOURCE_CHARS]}
{avoid_section}
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

2. **ความยาวคลิปเป้าหมาย {spec["seconds_range"]}พอดี (Strict Duration Standard)**:
   - เมื่อพากย์ด้วยเสียงพากย์ AI (+15% speed) สคริปต์รวมทั้ง {beat_count} ท่อนต้องมีความยาวประมาณ **{spec["word_range"]}** (ประมาณ **{spec["char_range"]}**) เพื่อให้เวลาจบที่ {spec["seconds_range"]}กำลังพอดี
   - **ห้ามเขียนยืดยาวเกิน {spec["max_seconds"]}เด็ดขาด!** ตัดเนื้อหาที่เวิ่นเว้อออก เล่าตรงประเด็น กระชับ ได้ใจความ ไม่ใส่มากเกินความจำเป็น

3. **น้ำเสียงและเพศของผู้พูด (Strict Male Persona 100%)**:
   - **ผู้พูดต้องเป็นผู้ชายเท่านั้น (Male Tone Only)**
   - ใช้สรรพนามและคำลงท้าย "ผม / ครับ / นะครับ" เท่านั้น
   - **ห้ามมีคำลงท้ายเพศหญิงโดยเด็ดขาด เช่น "ค่ะ", "นะคะ", "คะ", "จ้า", "น้า", "แกรรร", "หนู"**
   - ใช้น้ำเสียงจริงใจ มีพลัง เหมือนเพื่อนผู้ชายสายไอที/สายรีวิวมาบอกต่อของดี

4. **โครงสร้างสคริปต์ {beat_count} ท่อนทรงพลัง (Core 5-Beat + ท่อนเสริม)**:
   - ท่อนที่ 1 (Hook สะกดนิ้ว, ~10-14 คำ): ประโยคเปิดคลิปดึงดูดคนที่เจอปัญหานี้ ชี้เป้าทันที
   - ท่อนที่ 2 (Pain Point / สเปกหลัก, ~14-18 คำ): ขยี้ปัญหาเดิมๆ หรือชูฟังก์ชันหลักที่แก้ปัญหา
   - ท่อนที่ 3 (Core Tech & Compatibility, ~14-18 คำ): เปิดตัวสินค้า ชูชื่อรุ่นภาษาอังกฤษทางการ ความง่ายในการเชื่อมต่อ
   {"- (ท่อนเสริมแทรกตรงนี้ ดูกฎข้อ 9 ด้านล่าง)" if active_beats else ""}
   - ท่อนถัดมา (Real Feel & Endurance, ~16-20 คำ): จุดเด่นตอนใช้งานจริง สัมผัสดีไซน์ ความทนทาน แบตเตอรี่
   - ท่อนสุดท้าย (High-Converting CTA, ~12-16 คำ): ชวนตัดสินใจกดสั่งซื้อในตะกร้าสีเหลืองซ้ายล่างทันที

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
{image_rule}{extra_beat_rule}
{angle_list_section}

กฎการคงหัวข้อและประเภทเนื้อหา:
- ถ้าเป็นการสร้างใหม่เฉพาะมุม (มี angle_id ระบุไว้) ให้คง angle_id และ angle_name ตามที่ระบบกำหนดไว้ทุกประการ
- ท่อนเสริมเป็นเนื้อหาย่อยภายในหัวข้อเดิม ไม่ใช่หัวข้อใหม่ และห้ามเปลี่ยนมุมเพราะเลือกท่อนเสริม
- ระบบจะคำนวณ angle_description และ content_types จากหัวข้อกับท่อนเสริมหลัง AI ตอบกลับ ให้ส่งคีย์เดิมกลับมาได้แต่ห้ามใช้เพื่อเปลี่ยนความหมายของหัวข้อ

แต่ละ Object ใน JSON ต้องมีโครงสร้างดังนี้ (script_lines ต้องมีทั้งหมด {beat_count} ท่อนตามกฎข้อ {beat_structure_ref}, คุมความยาวให้พากย์จบใน {spec["seconds_range"]}พอดี และเว้นวรรคก้อนความคิดในแต่ละท่อน):
{{
  "angle_id": "{angle_id_override or "pain_point"}",
  "angle_name": "{ANGLE_CATALOG[angle_id_override]["label"] if angle_id_override else "😫 ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน"}",
  "angle_description": "คำอธิบายประเภทของมุมมองเนื้อหา",
  "content_types": [],
  "badge": "ขายดีอันดับ 1",
  "product_name": "ชื่อสินค้าที่กระชับ ไม่เกิน 30 ตัวอักษร",
  "hook_title": "พาดหัวเปิดคลิป 3 วินาทีแรก (มีอีโมจิและคำกระแทกใจ)",
  "pain_point": "ปัญหาหลักที่คนดูเจอ",
  "key_features": "จุดเด่น 3-4 ข้อที่ตอบโจทย์",
  "price_deal": "ข้อเสนอราคา/โปรโมชั่นและการเร่งรีบ",
  "ad_tone": "commercial_hype",
  "script_lines": {example_script_lines_json},
  "tiktok_caption": "บอกลาอาการปวดข้อมือ! อัปเกรดชีวิตด้วย {{product_name}} คีย์บอร์ดเพื่อสุขภาพที่นุ่มสบายที่สุด พิกัดในตะกร้าเลย 👇",
  "tiktok_hashtags": "#นายหน้าtiktok #รีวิวของดี #ของมันต้องมี #tiktokป้ายยา #พิกัดในตะกร้า"
}}

ตอบกลับเฉพาะ JSON array เท่านั้น ห้ามใส่คำเกริ่นนำหรือ markdown formatting อื่น
"""
        from scripts.config import get_gemini_api_keys
        api_keys = get_gemini_api_keys()
        api_key = api_keys[0] if api_keys else ""
        if api_key:
            # Pre-flight budget check. This calls Gemini directly rather than
            # through ai_bridge, so without its own gate the daily cap cannot
            # apply here -- and the except below folds every failure into the
            # template fallback, which would report a cap as a scrape miss.
            from scripts.quota import check_budget
            check_budget(task="content_matrix")

            try:
                from google import genai
                from google.genai import types

                # Reference screenshots ride alongside the prompt as actual
                # image content -- not just a thumbnail -- so the model reads
                # specs/features straight off a screenshot even when there's
                # no URL or typed description to scrape them from. A file
                # that's since moved or is unreadable is skipped rather than
                # failing the whole request; the text prompt still carries.
                image_parts = []
                for img_path in (image_paths or []):
                    try:
                        if isinstance(img_path, str) and img_path.lower().startswith(("http://", "https://")):
                            data, mime = _download_image_bytes(img_path)
                            image_parts.append(types.Part.from_bytes(data=data, mime_type=mime))
                            continue
                        p = Path(img_path)
                        if not p.is_absolute():
                            p = BASE_DIR / p
                        ext = p.suffix.lower().lstrip(".")
                        mime = {
                            "jpg": "image/jpeg", "jpeg": "image/jpeg",
                            "png": "image/png", "webp": "image/webp",
                            "heic": "image/heic", "heif": "image/heif",
                        }.get(ext, "image/jpeg")
                        image_parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime))
                    except Exception as img_err:
                        print(f"[ProductScraper] Skipping unreadable reference image {img_path}: {img_err}")

                contents = [prompt, *image_parts] if image_parts else prompt

                client = genai.Client(api_key=api_key)
                resp = None
                for m_name in ["gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-3.5-flash-lite"]:
                    try:
                        print(f"[ProductScraper] Calling Gemini with model {m_name}...")
                        resp = client.models.generate_content(
                            model=m_name,
                            contents=contents
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
                    for angle in angles:
                        apply_angle_content_metadata(
                            angle,
                            angle_id=angle_id_override or angle.get("angle_id"),
                            extra_beats=extra_beats,
                        )
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
                "ad_tone": "commercial_hype",
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
                "ad_tone": "commercial_hype",
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
                "ad_tone": "commercial_hype",
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
                "ad_tone": "commercial_hype",
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
                "ad_tone": "commercial_hype",
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
                "ad_tone": "commercial_hype",
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
        fallback_selection = fallback_angles
        if angle_id_override:
            fallback_selection = [
                angle for angle in fallback_angles
                if angle.get("angle_id") == angle_id_override
            ]
        angles = TTSSanitizer.process_angles(fallback_selection[:count])
        for angle in angles:
            apply_angle_content_metadata(
                angle,
                angle_id=angle_id_override or angle.get("angle_id"),
                extra_beats=extra_beats,
            )
        return angles

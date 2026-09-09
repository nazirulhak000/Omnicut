"""
tools/download_myinstants_sfx.py
=================================
Download all sound effects from https://www.myinstants.com/en/index/th/
into 02_Assets/SFX/ without deleting or overwriting existing files.

Usage:
    python tools/download_myinstants_sfx.py

Safety rules:
- Existing files in 02_Assets/SFX/ will NOT be deleted or overwritten
- New files from myinstants get prefix "mi_" to keep them separate
- If name collides (even with mi_ prefix), skip it
- Delay between requests to avoid hammering the server
"""

import io
import re
import sys
import time
import pathlib
import logging
import argparse
import urllib.request
import urllib.error
import urllib.parse
from html.parser import HTMLParser

# Fix Windows terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── paths ────────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
SFX_DIR = ROOT / "02_Assets" / "SFX"

BASE_URL = "https://www.myinstants.com"
INDEX_URL = "https://www.myinstants.com/en/index/th/?page={page}"
MEDIA_BASE = "https://www.myinstants.com/media/sounds/"

REQUEST_DELAY = 0.3   # seconds between each file download
PAGE_DELAY = 1.0      # seconds between page fetches
MAX_PAGES = 60        # maximum pages to try

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
}

# ─── logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


# ─── HTML parser ──────────────────────────────────────────────────────────────
class InstantParser(HTMLParser):
    """Parse the myinstants page and extract sound file paths from button onclick."""

    def __init__(self):
        super().__init__()
        self.sounds: list[dict] = []   # [{"name": str, "src": str}]
        self._current_name: str | None = None
        self._in_instant_div = False
        self._in_button = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Sound button: <button class="instant-button" onclick="play('/media/sounds/foo.mp3')">
        if tag == "button":
            onclick = attrs_dict.get("onclick", "")
            # Extract path from play('...') or similar
            match = re.search(r"['\"](/media/sounds/[^'\"]+)['\"]", onclick)
            if match:
                src_path = match.group(1)
                self._current_src = src_path
                self._in_button = True

        # Name typically in <b class="instant-name"> or similar span/div
        if tag in ("b", "span") and "instant-name" in attrs_dict.get("class", ""):
            self._in_name = True

    def handle_data(self, data):
        pass  # We collect name from a separate pass

    def handle_endtag(self, tag):
        if tag == "button":
            self._in_button = False


class FullPageParser(HTMLParser):
    """More robust parser that extracts all (name, sound_path) pairs."""

    def __init__(self):
        super().__init__()
        self.entries: list[dict] = []
        self._pending_src: str | None = None
        self._collect_name = False
        self._name_buf = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")

        # Button with onclick referencing media/sounds
        if tag == "button":
            onclick = attrs_dict.get("onclick", "")
            match = re.search(r"['\"](/media/sounds/[^'\"]+)['\"]", onclick)
            if match:
                self._pending_src = match.group(1)

        # Name element (try various class patterns used by myinstants)
        if tag in ("b", "span", "div", "p"):
            if any(k in classes for k in ("instant-name", "name", "instant-title")):
                self._collect_name = True
                self._name_buf = ""

    def handle_data(self, data):
        if self._collect_name:
            self._name_buf += data

    def handle_endtag(self, tag):
        if self._collect_name and tag in ("b", "span", "div", "p"):
            self._collect_name = False
            name = self._name_buf.strip()
            if name and self._pending_src:
                self.entries.append({"name": name, "src": self._pending_src})
                self._pending_src = None
            self._name_buf = ""


# ─── helpers ──────────────────────────────────────────────────────────────────

def fetch_page(url: str, retries: int = 3) -> str:
    """Fetch a URL and return HTML text."""
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            log.warning("HTTP %s สำหรับ %s (ครั้งที่ %d/%d)", e.code, url, attempt, retries)
            if e.code in (404, 410):
                return ""
            time.sleep(2 ** attempt)
        except Exception as e:
            log.warning("ข้อผิดพลาด: %s สำหรับ %s (ครั้งที่ %d/%d)", e, url, attempt, retries)
            time.sleep(2 ** attempt)
    return ""


def extract_sounds_from_html(html: str) -> list[dict]:
    """Extract list of {name, src} from a myinstants index page HTML."""
    entries: list[dict] = []

    # Pattern from myinstants HTML:
    # onclick="play('/media/sounds/FILENAME.mp3', 'loader-ID', 'slug-ID')"
    # Note: inside onclick="" the inner quotes are escaped as \'
    # Both forms need to be matched: ' and \'

    # Extract the first argument (sound path) from play(...)
    # Handles: play('/path/file.mp3', ...) and play(\'...\', ...)
    onclick_matches = re.findall(
        r"""onclick="play\(\\'(/media/sounds/[^'\\]+)\\'|onclick="play\('(/media/sounds/[^']+)'""",
        html,
    )
    # Each match is a tuple (esc_group, plain_group), take whichever is non-empty
    src_list = [g1 or g2 for g1, g2 in onclick_matches if g1 or g2]

    # Extract sound names from the instant-link anchor title or button title
    # e.g. title="Play vine-boom sound" or from the <a> text
    name_matches = re.findall(
        r'title="Play ([^"]+) sound"',
        html,
    )

    # Also try getting names from the instant-link href text
    if not name_matches:
        # <a href="/en/instant/vine-boom-sound-70972/" class="instant-link ...">vine boom</a>
        name_matches = re.findall(
            r'class="instant-link[^"]*">[^<]+<',
            html,
        )
        name_matches = [m.split(">")[1].rstrip("<").strip() for m in name_matches]

    # Pair them up
    for i, src in enumerate(src_list):
        if i < len(name_matches):
            name = name_matches[i].strip()
        else:
            # Fall back to filename stem
            name = pathlib.Path(src).stem.replace("-", " ").replace("_", " ")
        entries.append({"name": name, "src": src})

    if entries:
        return entries

    # Method 2: fallback — broader regex
    sounds_raw = re.findall(r"/media/sounds/([a-zA-Z0-9_\-%\.]+\.mp3)", html)
    unique_srcs = list(dict.fromkeys(sounds_raw))
    for s in unique_srcs:
        entries.append({"name": s.replace("-", " ").replace("_", " ").rsplit(".", 1)[0],
                        "src": f"/media/sounds/{s}"})

    return entries


def safe_filename(src_path: str) -> str:
    """
    แปลง /media/sounds/foo.mp3 → mi_foo.mp3
    ใช้ prefix mi_ เพื่อไม่ชนกับไฟล์เดิม
    """
    base = pathlib.Path(src_path).name  # e.g. "vine-boom.mp3"
    return f"mi_{base}"


def download_sound(src_path: str, dest_dir: pathlib.Path, dry_run: bool = False) -> bool:
    """
    Download a single sound.  Returns True if downloaded, False if skipped/error.
    """
    filename = safe_filename(src_path)
    dest = dest_dir / filename

    if dest.exists():
        log.debug("ข้าม (มีอยู่แล้ว): %s", filename)
        return False

    url = f"{BASE_URL}{src_path}"

    if dry_run:
        log.info("[DRY-RUN] จะโหลด: %s → %s", url, filename)
        return True

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.write_bytes(data)
        log.info("โหลดแล้ว: %s (%.1f KB)", filename, len(data) / 1024)
        return True
    except urllib.error.HTTPError as e:
        log.warning("HTTP %s: %s", e.code, url)
        return False
    except Exception as e:
        log.warning("ข้อผิดพลาด %s: %s", url, e)
        return False


def check_originals_intact(sfx_dir: pathlib.Path, original_names: list[str]) -> bool:
    """ตรวจสอบว่าไฟล์เสียงเดิมยังครบ"""
    missing = [n for n in original_names if not (sfx_dir / n).exists()]
    if missing:
        log.error("❌ ไฟล์เสียงเดิมหาย: %s", missing)
        return False
    log.info("✅ ไฟล์เสียงเดิมครบทุกไฟล์ (%d ไฟล์)", len(original_names))
    return True


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="โหลดเสียงเอฟเฟกต์ทั้งหมดจาก myinstants.com/en/index/th/"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="แสดงเฉพาะรายการที่จะโหลด ไม่บันทึกไฟล์จริง",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="เริ่มจากหน้าที่ (default: 1)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=MAX_PAGES,
        help=f"หยุดที่หน้า (default: {MAX_PAGES})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY,
        help=f"หน่วงเวลาระหว่างไฟล์ วินาที (default: {REQUEST_DELAY})",
    )
    args = parser.parse_args()

    SFX_DIR.mkdir(parents=True, exist_ok=True)

    # บันทึกชื่อไฟล์เดิมทั้งหมดก่อนเริ่ม (เพื่อตรวจ gate ทีหลัง)
    original_files = [f.name for f in SFX_DIR.iterdir() if f.is_file()]
    log.info("ไฟล์เสียงเดิม: %d ไฟล์", len(original_files))

    total_downloaded = 0
    total_skipped = 0
    total_sounds_found = 0
    empty_pages = 0

    log.info("=" * 60)
    log.info("เริ่มโหลดเสียงจาก myinstants.com/en/index/th/")
    log.info("โฟลเดอร์ปลายทาง: %s", SFX_DIR)
    log.info("หน้า: %d–%d", args.start_page, args.end_page)
    log.info("=" * 60)

    for page in range(args.start_page, args.end_page + 1):
        url = INDEX_URL.format(page=page)
        log.info("── หน้า %d: %s", page, url)

        html = fetch_page(url)
        if not html:
            log.warning("ดึงหน้า %d ไม่ได้ ข้ามไป", page)
            empty_pages += 1
            if empty_pages >= 3:
                log.info("หน้าว่างติดต่อกัน 3 หน้า หยุดการโหลด")
                break
            time.sleep(PAGE_DELAY)
            continue

        sounds = extract_sounds_from_html(html)

        if not sounds:
            log.info("หน้า %d: ไม่พบเสียง (อาจเป็นหน้าสุดท้าย)", page)
            empty_pages += 1
            if empty_pages >= 3:
                log.info("หน้าว่างติดต่อกัน 3 หน้า หยุดการโหลด")
                break
            time.sleep(PAGE_DELAY)
            continue

        empty_pages = 0  # reset counter เมื่อพบเสียง
        total_sounds_found += len(sounds)
        log.info("พบ %d เสียงในหน้า %d", len(sounds), page)

        for i, sound in enumerate(sounds, 1):
            ok = download_sound(sound["src"], SFX_DIR, dry_run=args.dry_run)
            if ok:
                total_downloaded += 1
            else:
                total_skipped += 1
            time.sleep(args.delay)

        time.sleep(PAGE_DELAY)

    # ─── สรุปผล ─────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("สรุปผลการโหลด:")
    log.info("  พบเสียงทั้งหมด:    %d", total_sounds_found)
    log.info("  โหลดสำเร็จ:        %d", total_downloaded)
    log.info("  ข้าม (มีอยู่แล้ว): %d", total_skipped)

    # ตรวจ gate: ไฟล์เดิมยังครบ
    intact = check_originals_intact(SFX_DIR, original_files)

    # นับไฟล์ทั้งหมดหลังโหลด
    all_files_after = list(SFX_DIR.iterdir())
    log.info("  ไฟล์ทั้งหมดใน SFX/ ตอนนี้: %d ไฟล์", len(all_files_after))

    if not intact:
        log.error("❌ GATE FAIL: ไฟล์เดิมหาย!")
        sys.exit(1)

    if total_downloaded == 0 and total_skipped == 0:
        log.error("❌ GATE FAIL: ไม่ได้โหลดหรือพบเสียงใดเลย")
        sys.exit(1)

    log.info("✅ เสร็จสมบูรณ์!")


if __name__ == "__main__":
    main()

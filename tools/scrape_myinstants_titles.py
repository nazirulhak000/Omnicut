"""
tools/scrape_myinstants_titles.py
=================================
Scrape the actual display names (Thai/English) of all sound buttons from
https://www.myinstants.com/en/index/th/ (pages 1 to 50) and merge them into
02_Assets/asset_metadata.json as "label_th" and "label" so the UI displays
the friendly human-readable titles instead of raw filenames.
"""

import json
import logging
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

# Fix Windows terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
METADATA_PATH = ROOT / "02_Assets" / "asset_metadata.json"

INDEX_URL = "https://www.myinstants.com/en/index/th/?page={page}"
MAX_PAGES = 50
DELAY_BETWEEN_PAGES = 0.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def fetch_page(page: int, retries: int = 3) -> str:
    url = INDEX_URL.format(page=page)
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                log.info("Page %d returned %s (end of pages)", page, e.code)
                return ""
            log.warning("HTTP %s on page %d (attempt %d/%d)", e.code, page, attempt, retries)
            time.sleep(1.5 * attempt)
        except Exception as e:
            log.warning("Error on page %d: %s (attempt %d/%d)", page, e, attempt, retries)
            time.sleep(1.5 * attempt)
    return ""


def parse_page_titles(html: str) -> dict[str, str]:
    """
    Returns mapping of {asset_id: display_title}
    where asset_id is e.g. "mi_vine-boom" (stem of mi_vine-boom.mp3).
    """
    results: dict[str, str] = {}
    blocks = re.findall(r'<div class="instant.*?</div>\s*</div>', html, re.DOTALL)
    for b in blocks:
        m_sound = re.search(r"/media/sounds/([a-zA-Z0-9_\-\.%]+\.mp3)", b)
        m_title = re.search(r'class="instant-link[^"]*"[^>]*>(.*?)</a>', b, re.DOTALL)
        if m_sound and m_title:
            sound_filename = m_sound.group(1)
            # Remove extension for asset_id
            sound_stem = pathlib.Path(sound_filename).stem
            asset_id = f"mi_{sound_stem}"
            
            # Clean title
            raw_title = m_title.group(1)
            # Strip any inner tags, html entities
            clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()
            clean_title = clean_title.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
            
            if asset_id and clean_title:
                results[asset_id] = clean_title
    return results


def main():
    log.info("Starting title scraping from Myinstants Thailand (1 to %d pages)...", MAX_PAGES)
    
    # Load existing metadata
    existing_meta = {}
    if METADATA_PATH.exists():
        try:
            existing_meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Could not read existing metadata: %s", e)
            existing_meta = {}

    total_scraped = 0
    new_titles = 0

    for page in range(1, MAX_PAGES + 1):
        html = fetch_page(page)
        if not html:
            log.info("Finished fetching at page %d", page)
            break
            
        page_titles = parse_page_titles(html)
        if not page_titles:
            log.info("No sound items found on page %d, ending.", page)
            break
            
        for asset_id, title in page_titles.items():
            total_scraped += 1
            if asset_id not in existing_meta:
                existing_meta[asset_id] = {}
            if existing_meta[asset_id].get("label_th") != title:
                existing_meta[asset_id]["label_th"] = title
                existing_meta[asset_id]["label"] = title
                new_titles += 1
                
        log.info("Page %2d: found %2d sounds (cumulative scraped: %d, updated: %d)", page, len(page_titles), total_scraped, new_titles)
        time.sleep(DELAY_BETWEEN_PAGES)

    # Save metadata back
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(existing_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Saved metadata to %s (Total assets in metadata: %d)", METADATA_PATH, len(existing_meta))


if __name__ == "__main__":
    main()

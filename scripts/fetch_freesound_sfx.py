"""
Fetch CC0 sound effects from Freesound to fill gaps in 02_Assets/SFX/.

Standalone CLI, not imported by the pipeline -- run by hand occasionally,
matching the project's "no automated scraping/harvesting" stance (the same
one that keeps ai_bridge.py's product-fetch endpoint to og:/oEmbed only).
Freesound's search API takes a plain Token key; downloading an *original*
file needs OAuth2 (a redirect-based user login flow), which is overkill for
an occasional batch pull -- this uses the "preview" mp3 (~128kbps) instead,
plenty for a short SFX layered under a voiceover, and fetchable with the
same Token that authenticates the search.

Filters to CC0 only. Freesound also serves CC-BY (attribution required) and
CC-BY-NC (no commercial use -- would have to be excluded for this tool
regardless), but CC0 needs no attribution tracking at all, which is the
simplest and safest choice for a commercial-use asset library.

Setup:
    1. Create a free Freesound account, then request an API credential at
       https://freesound.org/apiv2/apply
    2. Add to .env:  FREESOUND_API_KEY=<your key>
    3. Run:  python -m scripts.fetch_freesound_sfx
       (optionally: --query "cash register" --limit 3, to pull one term ad hoc)

Every downloaded file is hash-checked against what's already in SFX/ before
saving, named sfx_<slug>.mp3, and the registry is rebuilt at the end so the
new sounds are immediately selectable -- no separate step.
"""

import os
import re
import sys
import json
import hashlib
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ai_bridge import _load_env_file
from scripts.config import SFX_DIR
from scripts.asset_registry import AssetRegistry

_load_env_file()

API_BASE = "https://freesound.org/apiv2"
CC0_LICENSE = "Creative Commons 0"
MAX_DURATION_S = 8.0  # SFX, not music beds -- reject anything longer

# Search terms filling gaps against the categories already in SFX/
# (notification/bell, UI-click, commerce, reaction, transition, celebratory,
# packaging) -- these eight are missing entirely.
DEFAULT_QUERIES = [
    "applause",
    "wrong answer buzzer",
    "drum roll suspense",
    "level up game",
    "countdown beep",
    "swipe card",
    "error alert",
    "success chime",
]
DEFAULT_LIMIT_PER_QUERY = 2


class FreesoundFetchError(Exception):
    pass


def _api_key() -> str:
    key = os.environ.get("FREESOUND_API_KEY", "").strip()
    if not key:
        raise FreesoundFetchError(
            "ไม่พบ FREESOUND_API_KEY — สมัครฟรีที่ https://freesound.org/apiv2/apply "
            "แล้วใส่ใน .env เป็น FREESOUND_API_KEY=<key>"
        )
    return key


def _get_json(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    params = {**params, "token": _api_key()}
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "capcut-asset-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:40] or "sound"


def _existing_hashes() -> Dict[str, Path]:
    """MD5 of every SFX file already on disk, to skip re-downloading a duplicate."""
    hashes = {}
    for path in list(SFX_DIR.glob("*.wav")) + list(SFX_DIR.glob("*.mp3")):
        hashes[hashlib.md5(path.read_bytes()).hexdigest()] = path
    return hashes


def search_cc0_sounds(query: str, limit: int) -> List[Dict[str, Any]]:
    """CC0-only, short clips, best-rated first."""
    data = _get_json("/search/text/", {
        "query": query,
        "filter": f'license:"{CC0_LICENSE}" duration:[0.1 TO {MAX_DURATION_S}]',
        "sort": "rating_desc",
        "fields": "id,name,previews,license,duration,username,url",
        "page_size": limit,
    })
    return data.get("results", [])[:limit]


def download_sound(sound: Dict[str, Any], existing_hashes: Dict[str, Path]) -> Optional[Path]:
    """Save one sound's HQ preview as sfx_<slug>.mp3, skipping an exact duplicate."""
    preview_url = (sound.get("previews") or {}).get("preview-hq-mp3")
    if not preview_url:
        print(f"   skip '{sound.get('name')}': no preview URL in response")
        return None

    request = urllib.request.Request(preview_url, headers={"User-Agent": "capcut-asset-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()

    content_hash = hashlib.md5(content).hexdigest()
    if content_hash in existing_hashes:
        print(f"   skip '{sound.get('name')}': already have this exact file ({existing_hashes[content_hash].name})")
        return None

    slug = _slugify(sound.get("name", "sound"))
    dest = SFX_DIR / f"sfx_{slug}.mp3"
    suffix = 2
    while dest.exists():
        dest = SFX_DIR / f"sfx_{slug}_{suffix}.mp3"
        suffix += 1

    dest.write_bytes(content)
    existing_hashes[content_hash] = dest
    return dest


def record_metadata(dest: Path, sound: Dict[str, Any]) -> None:
    """CC0 needs no attribution, but the source is worth keeping for provenance."""
    from scripts.asset_registry import METADATA_PATH

    metadata = {}
    if METADATA_PATH.exists():
        try:
            metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metadata = {}

    metadata[dest.stem] = {
        "source": "freesound",
        "source_url": sound.get("url", ""),
        "license": sound.get("license", CC0_LICENSE),
        "category": "misc",
    }

    tmp = METADATA_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(METADATA_PATH)


def run(queries: List[str], limit_per_query: int) -> List[Path]:
    existing_hashes = _existing_hashes()
    downloaded = []

    for query in queries:
        print(f"\n🔎 '{query}'")
        try:
            results = search_cc0_sounds(query, limit_per_query)
        except Exception as e:
            print(f"   search failed: {e}")
            continue

        if not results:
            print("   no CC0 results found")
            continue

        for sound in results:
            try:
                dest = download_sound(sound, existing_hashes)
            except Exception as e:
                print(f"   download failed for '{sound.get('name')}': {e}")
                continue
            if dest:
                record_metadata(dest, sound)
                downloaded.append(dest)
                print(f"   ✓ saved {dest.name}  (by {sound.get('username')}, CC0)")

    if downloaded:
        AssetRegistry.rebuild()
        print(f"\n✅ {len(downloaded)} new SFX added, registry rebuilt.")
    else:
        print("\nNo new files downloaded.")

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Fetch CC0 sound effects from Freesound")
    parser.add_argument("--query", action="append", help="Search term (repeatable). Defaults to a curated gap-filling list.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT_PER_QUERY, help="Max results per query")
    args = parser.parse_args()

    queries = args.query if args.query else DEFAULT_QUERIES
    run(queries, args.limit)


if __name__ == "__main__":
    main()

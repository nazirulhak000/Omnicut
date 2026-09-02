"""
Fetch CC0 background-music loops from Freesound to replace/expand
02_Assets/Music/ -- the 7 tracks there today (bgm_cyber_phonk.wav etc.) are
procedurally synthesized by build_assets.py (numpy sine/kick/snare formulas),
not real production audio.

Mirrors scripts/fetch_freesound_sfx.py's auth/dedup/metadata machinery
(imported directly, not duplicated) but tuned for music instead of short
SFX: no upper duration cap (SFXManager.mix_audio_track already
`-stream_loop`s the BGM to fill any clip length, so a 15s loop and a 90s
track both work fine), and a `bgm_<slug>.mp3` naming convention.

Also fetches `avg_rating` and `num_downloads` for every result -- there is
no way to actually listen to a track from here, so picking "the best one"
has to lean on Freesound's own community signal plus a manual tags/
description check (the same content-verification step that caught 7 bad
SFX matches earlier), not a guess from the filename.

Setup: same FREESOUND_API_KEY as fetch_freesound_sfx.py (see that file's
docstring for how to get one).

Usage:
    python -m scripts.fetch_freesound_bgm --query "tech house energetic" --limit 3
    python -m scripts.fetch_freesound_bgm            # runs the default IT/tech query set
"""

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

from tools.fetch_freesound_sfx import _api_key, _get_json, _slugify, CC0_LICENSE
from scripts.config import MUSIC_DIR
from scripts.asset_registry import AssetRegistry, METADATA_PATH

# Genres/moods that fit a fast-paced IT/gadget review + TikTok Shop channel:
# confident, modern, energetic enough for quick cuts, but not so busy it
# fights the voiceover for attention.
DEFAULT_QUERIES = [
    "tech house energetic",
    "corporate technology upbeat",
    "hype trap beat",
    "synthwave loop energetic",
    "electronic drive loop",
]
DEFAULT_LIMIT_PER_QUERY = 3
MIN_DURATION_S = 8.0  # below this it reads as an SFX hit, not a music bed


def search_cc0_music(query: str, limit: int) -> List[Dict[str, Any]]:
    """CC0-only, real music-length clips, best-rated first."""
    data = _get_json("/search/text/", {
        "query": query,
        "filter": f'license:"{CC0_LICENSE}" duration:[{MIN_DURATION_S} TO *] tag:music',
        "sort": "rating_desc",
        "fields": "id,name,previews,license,duration,username,url,avg_rating,num_downloads,num_ratings,tags",
        "page_size": limit,
    })
    return data.get("results", [])[:limit]


def _existing_hashes() -> Dict[str, Path]:
    hashes = {}
    for path in list(MUSIC_DIR.glob("*.wav")) + list(MUSIC_DIR.glob("*.mp3")):
        hashes[hashlib.md5(path.read_bytes()).hexdigest()] = path
    return hashes


def download_track(sound: Dict[str, Any], existing_hashes: Dict[str, Path]) -> Optional[Path]:
    """Save one track's HQ preview as bgm_<slug>.mp3, skipping an exact duplicate."""
    preview_url = (sound.get("previews") or {}).get("preview-hq-mp3")
    if not preview_url:
        print(f"   skip '{sound.get('name')}': no preview URL in response")
        return None

    # No custom User-Agent -- Freesound returns HTTP 500 for one (confirmed
    # the hard way while building fetch_freesound_sfx.py).
    with urllib.request.urlopen(preview_url, timeout=30) as response:
        content = response.read()

    content_hash = hashlib.md5(content).hexdigest()
    if content_hash in existing_hashes:
        print(f"   skip '{sound.get('name')}': already have this exact file ({existing_hashes[content_hash].name})")
        return None

    slug = _slugify(sound.get("name", "track"))
    dest = MUSIC_DIR / f"bgm_{slug}.mp3"
    suffix = 2
    while dest.exists():
        dest = MUSIC_DIR / f"bgm_{slug}_{suffix}.mp3"
        suffix += 1

    dest.write_bytes(content)
    existing_hashes[content_hash] = dest
    return dest


def record_metadata(dest: Path, sound: Dict[str, Any]) -> None:
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
        "avg_rating": sound.get("avg_rating"),
        "num_ratings": sound.get("num_ratings"),
        "num_downloads": sound.get("num_downloads"),
        "duration": sound.get("duration"),
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
            results = search_cc0_music(query, limit_per_query)
        except Exception as e:
            print(f"   search failed: {e}")
            continue

        if not results:
            print("   no CC0 results found")
            continue

        for sound in results:
            try:
                dest = download_track(sound, existing_hashes)
            except Exception as e:
                print(f"   download failed for '{sound.get('name')}': {e}")
                continue
            if dest:
                record_metadata(dest, sound)
                downloaded.append(dest)
                rating = sound.get("avg_rating")
                downloads = sound.get("num_downloads")
                print(f"   ✓ saved {dest.name}  (by {sound.get('username')}, "
                      f"rating {rating}/5 over {sound.get('num_ratings')} votes, {downloads} downloads)")

    if downloaded:
        AssetRegistry.rebuild()
        print(f"\n✅ {len(downloaded)} new BGM tracks added, registry rebuilt.")
    else:
        print("\nNo new files downloaded.")

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Fetch CC0 background music from Freesound")
    parser.add_argument("--query", action="append", help="Search term (repeatable). Defaults to a curated IT/tech-vertical list.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT_PER_QUERY, help="Max results per query")
    args = parser.parse_args()

    queries = args.query if args.query else DEFAULT_QUERIES
    run(queries, args.limit)


if __name__ == "__main__":
    main()

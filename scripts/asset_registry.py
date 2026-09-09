"""
Asset registry -- the single place SFX, BGM, fonts, LUTs and stickers get
discovered from, replacing the hardcoded dicts/arrays this project had
scattered across sfx_manager.py, subtitle_engine.py, and the frontend.

02_Assets/ has real variety on disk (27 SFX, 7 BGM tracks, 20 fonts across
8+ families, 4 LUTs, 8 stickers) but almost none of it was ever reachable
from the render pipeline -- someone would have had to hand-edit a Python
dict every time a new file showed up. This scans the actual directories,
so a file dropped in (by upload or a future download script) becomes
usable the moment the registry is rebuilt, with no code change.

Mirrors the load/save/require pattern already established in
project_manifest.py rather than inventing a new one.
"""

import json
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import ASSETS_DIR, FONTS_DIR, SFX_DIR, MUSIC_DIR, STICKERS_DIR, LUTS_DIR, EFFECTS_DIR

REGISTRY_PATH = ASSETS_DIR / "asset_registry.json"
METADATA_PATH = ASSETS_DIR / "asset_metadata.json"
REGISTRY_VERSION = 1

# Every SFX name that used to be the *entire* usable set. Kept as synonyms
# pointing at their now-confirmed-identical canonical files, so a
# project.json manifest from before this registry existed (one that says
# e.g. "sfx": "boom") keeps resolving to the same audio it always did.
# Verified by MD5 during the asset audit -- these are true duplicates, not
# an assumption.
LEGACY_SFX_ALIASES = {
    "whoosh": "sfx_whoosh_fast",
    "pop": "sfx_pop_bubble",
    "ding": "sfx_bell_ding",
    "cash": "sfx_cash_register",
    "boom": "sfx_vine_boom",
}

_FALLBACK_SFX_CATEGORY = "misc"


class AssetRegistry:
    """Discovers what's actually in 02_Assets/ and caches the result."""

    # ------------------------------------------------------------------
    # Metadata (the one hand-editable file)
    # ------------------------------------------------------------------
    @classmethod
    def _load_metadata(cls) -> Dict[str, Dict[str, Any]]:
        """
        Optional hand-authored fields keyed by asset id (filename stem):
        SFX/BGM category or mood tags, sticker color hints, attribution for
        anything pulled from an external source. Missing entirely, or missing
        a given id, is fine -- everything gets a sensible default so dropping
        a file in and rendering works with zero required editing.
        """
        if not METADATA_PATH.exists():
            return {}
        try:
            data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # File info (same shape api_server.py's get_file_info() already returns,
    # so nothing downstream that already renders this shape needs to change)
    # ------------------------------------------------------------------
    @staticmethod
    def _file_info(path: Path) -> Dict[str, Any]:
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path),
            "rel_path": str(path.relative_to(ASSETS_DIR.parent)).replace("\\", "/"),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": stat.st_mtime,
        }

    @staticmethod
    def _font_family(path: Path) -> str:
        """Real embedded family name, not a guess from the filename."""
        try:
            from fontTools.ttLib import TTFont
            font = TTFont(path, fontNumber=0, lazy=True)
            name_table = font["name"]
            # getDebugName is forgiving about which platform/encoding record
            # actually exists; 16 = "Typographic Family", 1 = "Family".
            family = name_table.getDebugName(16) or name_table.getDebugName(1)
            return family.strip() if family else path.stem
        except Exception:
            return path.stem

    # ------------------------------------------------------------------
    # Category scanners
    # ------------------------------------------------------------------
    @classmethod
    def _scan_sfx(cls, metadata: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        entries = []
        raw_files = list(SFX_DIR.rglob("*.wav")) + list(SFX_DIR.rglob("*.mp3"))
        for path in sorted(raw_files, key=lambda p: (p.parent != SFX_DIR, p.parent.name, p.name)):
            asset_id = path.stem
            meta = metadata.get(asset_id, {})
            entry = cls._file_info(path)
            entry["id"] = asset_id
            
            # If inside a subfolder under SFX_DIR, use subfolder name as category
            if path.parent != SFX_DIR:
                subfolder_category = path.parent.name
            else:
                subfolder_category = _FALLBACK_SFX_CATEGORY
                
            entry["category"] = meta.get("category") or subfolder_category
            entry["label_th"] = meta.get("label_th", "")
            entry["label"] = meta.get("label") or meta.get("label_th") or path.stem
            entry["audio_url"] = f"/api/media/{entry['rel_path']}"
            entry["starred"] = bool(meta.get("starred", False))
            entries.append(entry)
        return entries

    @classmethod
    def _scan_bgm(cls, metadata: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        entries = []
        for path in sorted(MUSIC_DIR.glob("*.wav")) + sorted(MUSIC_DIR.glob("*.mp3")):
            asset_id = path.stem
            meta = metadata.get(asset_id, {})
            entry = cls._file_info(path)
            entry["id"] = asset_id
            entry["mood"] = meta.get("mood", "")
            entry["label_th"] = meta.get("label_th", "")
            entry["label"] = meta.get("label") or meta.get("label_th") or path.stem
            entry["audio_url"] = f"/api/media/{entry['rel_path']}"
            entry["starred"] = bool(meta.get("starred", False))
            entries.append(entry)
        return entries

    @classmethod
    def _scan_fonts(cls) -> List[Dict[str, Any]]:
        entries = []
        for path in sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf")):
            entry = cls._file_info(path)
            entry["id"] = path.stem
            entry["family"] = cls._font_family(path)
            entries.append(entry)
        return entries

    @classmethod
    def _scan_stickers(cls) -> List[Dict[str, Any]]:
        entries = []
        seen_stems = set()
        candidate_dirs = [STICKERS_DIR, ASSETS_DIR / "Stickers"]
        for s_dir in candidate_dirs:
            if not s_dir.exists():
                continue
            globs = list(s_dir.glob("*.png")) + list(s_dir.glob("*.webp")) + list(s_dir.glob("*.jpg"))
            for path in sorted(globs):
                if path.stem in seen_stems:
                    continue
                seen_stems.add(path.stem)
                entry = cls._file_info(path)
                entry["id"] = path.stem
                entry["img_url"] = f"/api/media/{entry['rel_path']}"
                entries.append(entry)
        return entries

    @classmethod
    def _scan_luts(cls) -> List[Dict[str, Any]]:
        entries = []
        for path in sorted(LUTS_DIR.glob("*.cube")):
            entry = cls._file_info(path)
            entry["id"] = path.stem
            entries.append(entry)
        return entries

    @classmethod
    def _scan_effects(cls, metadata: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Video overlay effects (transparent .webm/.mov) -- checkmarks, warnings,
        arrows etc, converted from free Lottie/GIF previews for use as cutaway
        overlays in review clips."""
        entries = []
        raw_files = list(EFFECTS_DIR.glob("*.webm")) + list(EFFECTS_DIR.glob("*.mov"))
        for path in sorted(raw_files):
            asset_id = path.stem
            meta = metadata.get(asset_id, {})
            entry = cls._file_info(path)
            entry["id"] = asset_id
            entry["category"] = meta.get("category", "other")
            entry["label_th"] = meta.get("label_th", "")
            entry["label"] = meta.get("label") or meta.get("label_th") or path.stem
            entry["video_url"] = f"/api/media/{entry['rel_path']}"
            entry["starred"] = bool(meta.get("starred", False))
            entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    # Build / cache
    # ------------------------------------------------------------------
    @classmethod
    def rebuild(cls) -> Dict[str, Any]:
        """Scan every category fresh and write the cache."""
        metadata = cls._load_metadata()
        registry = {
            "registry_version": REGISTRY_VERSION,
            "sfx": cls._scan_sfx(metadata),
            "bgm": cls._scan_bgm(metadata),
            "fonts": cls._scan_fonts(),
            "stickers": cls._scan_stickers(),
            "luts": cls._scan_luts(),
            "effects": cls._scan_effects(metadata),
        }
        registry["counts"] = {k: len(v) for k, v in registry.items() if isinstance(v, list)}

        tmp = REGISTRY_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(REGISTRY_PATH)
        return registry

    @classmethod
    def _cache_is_fresh(cls) -> bool:
        if not REGISTRY_PATH.exists():
            return False
        cache_mtime = REGISTRY_PATH.stat().st_mtime
        watched_dirs = [SFX_DIR, MUSIC_DIR, FONTS_DIR, STICKERS_DIR, ASSETS_DIR / "Stickers", LUTS_DIR, EFFECTS_DIR]
        if METADATA_PATH.exists() and METADATA_PATH.stat().st_mtime > cache_mtime:
            return False
        for directory in watched_dirs:
            if not directory.exists():
                continue
            for entry in directory.rglob("*"):
                if entry.is_file() and entry.stat().st_mtime > cache_mtime:
                    return False
        return True

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """Cached scan, self-healing the moment any asset file changes."""
        if cls._cache_is_fresh():
            try:
                data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "sfx" in data:
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return cls.rebuild()

    # ------------------------------------------------------------------
    # Typed accessors
    # ------------------------------------------------------------------
    @classmethod
    def sfx(cls) -> List[Dict[str, Any]]:
        return cls.load()["sfx"]

    @classmethod
    def bgm(cls) -> List[Dict[str, Any]]:
        return cls.load()["bgm"]

    @classmethod
    def fonts(cls) -> List[Dict[str, Any]]:
        return cls.load()["fonts"]

    @classmethod
    def stickers(cls) -> List[Dict[str, Any]]:
        return cls.load()["stickers"]

    @classmethod
    def luts(cls) -> List[Dict[str, Any]]:
        return cls.load()["luts"]

    @classmethod
    def effects(cls) -> List[Dict[str, Any]]:
        return cls.load()["effects"]

    # ------------------------------------------------------------------
    # SFX name resolution (used by SFXManager)
    # ------------------------------------------------------------------
    @classmethod
    def resolve_sfx_path(cls, name: str) -> Optional[Path]:
        """
        A cue's `sfx` tag -> real file path, or None if unknown.

        Accepts either a legacy short name ("boom") or a full registry id
        ("sfx_vine_boom") so old and new callers both work.
        """
        if not name:
            return None
        canonical = LEGACY_SFX_ALIASES.get(name, name)
        for entry in cls.sfx():
            if entry["id"] == canonical:
                return Path(entry["path"])
        return None

    @classmethod
    def resolve_lut_path(cls, name: str) -> Optional[Path]:
        """
        A stored `lut_name` -> real .cube path, or None if unknown.

        Accepts either the filename ("lut_warm_cozy_lifestyle.cube") or the
        registry id ("lut_warm_cozy_lifestyle"). The Filter picker sends the
        id, so the old `LUTS_DIR / lut_name` never found the file and every
        grade was skipped silently -- the picker appeared to do nothing.
        """
        if not name:
            return None
        direct = LUTS_DIR / name
        if direct.exists():
            return direct
        for entry in cls.luts():
            if entry.get("id") == name or entry.get("name") == name:
                path = Path(entry["path"])
                if path.exists():
                    return path
        return None

    @classmethod
    def set_starred(cls, asset_id: str, starred: bool) -> Dict[str, Any]:
        """Toggle the starred flag for one asset id, persisted to asset_metadata.json."""
        metadata = cls._load_metadata()
        entry = metadata.setdefault(asset_id, {})
        entry["starred"] = bool(starred)
        tmp = METADATA_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(METADATA_PATH)
        return cls.rebuild()

    @classmethod
    def sfx_name_list(cls) -> List[str]:
        """Every playable SFX name, canonical ids plus the legacy short aliases, for prompt-building."""
        ids = [e["id"] for e in cls.sfx()]
        return sorted(set(ids) | set(LEGACY_SFX_ALIASES.keys()))


if __name__ == "__main__":
    reg = AssetRegistry.rebuild()
    print(json.dumps(reg["counts"], ensure_ascii=False, indent=2))

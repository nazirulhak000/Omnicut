"""Asset Deduplication Engine — Reclaims disk space by identifying duplicate assets.

Scans `00_Inbox/` and `01_Raw/` for identical media files resulting from repeated mobile syncs.
Multi-tier detection:
1. File size bucketing (O(1) quick filter)
2. Partial quick hash (first 64KB + last 64KB)
3. Full SHA-256 hash verification (100% precision)

Determines master copy (oldest creation/modification time) and duplicate candidates.
Safely reclaims disk space by removing duplicates or sending to `.trash`.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR, INBOX_DIR, RAW_DIR, ARCHIVE_DIR

MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp3", ".wav", ".aac", ".m4a"
}

TRASH_DIR = ARCHIVE_DIR / ".trash"
_DEDUP_LOCK = threading.Lock()


class AssetDedupEngine:
    """Detects and safely cleans duplicate media assets across inbox and raw folders."""

    @classmethod
    def scan_duplicates(
        cls,
        search_dirs: Optional[List[Path]] = None,
        min_file_size_bytes: int = 1024,
    ) -> Dict[str, Any]:
        """Scans specified directories and returns groups of duplicate media assets."""
        with _DEDUP_LOCK:
            target_dirs = search_dirs or [INBOX_DIR, RAW_DIR]
            candidates_by_size: Dict[int, List[Path]] = {}
            total_scanned = 0

            # Step 1: Collect files by size
            for d in target_dirs:
                if not d.exists():
                    continue
                for root, _, files in os.walk(d):
                    for fname in files:
                        p = Path(root) / fname
                        if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS:
                            try:
                                sz = p.stat().st_size
                                if sz >= min_file_size_bytes:
                                    total_scanned += 1
                                    candidates_by_size.setdefault(sz, []).append(p)
                            except OSError:
                                continue

            # Step 2 & 3: Multi-tier hash check for sizes with > 1 candidate
            duplicate_groups: List[Dict[str, Any]] = []
            reclaimable_bytes = 0

            for sz, files in candidates_by_size.items():
                if len(files) < 2:
                    continue

                # Group by quick hash
                by_quick_hash: Dict[str, List[Path]] = {}
                for f in files:
                    qh = cls._quick_hash(f)
                    if qh:
                        by_quick_hash.setdefault(qh, []).append(f)

                # For matching quick hashes, verify full SHA-256
                for qh, matching_quick in by_quick_hash.items():
                    if len(matching_quick) < 2:
                        continue

                    by_full_hash: Dict[str, List[Path]] = {}
                    for f in matching_quick:
                        fh = cls._full_sha256(f)
                        if fh:
                            by_full_hash.setdefault(fh, []).append(f)

                    for full_h, matched_files in by_full_hash.items():
                        if len(matched_files) < 2:
                            continue

                        # Sort: Oldest file is original/master
                        sorted_files = sorted(
                            matched_files,
                            key=lambda p: (p.stat().st_mtime, len(str(p)))
                        )
                        original = sorted_files[0]
                        duplicates = sorted_files[1:]

                        dup_items = []
                        for dup in duplicates:
                            rel_path = dup.relative_to(BASE_DIR).as_posix() if dup.is_relative_to(BASE_DIR) else str(dup)
                            dup_items.append({
                                "file_name": dup.name,
                                "relative_path": rel_path,
                                "full_path": str(dup.resolve()),
                                "size_bytes": sz,
                                "size_mb": round(sz / (1024 * 1024), 2),
                                "modified_at": dup.stat().st_mtime,
                            })
                            reclaimable_bytes += sz

                        orig_rel = original.relative_to(BASE_DIR).as_posix() if original.is_relative_to(BASE_DIR) else str(original)
                        duplicate_groups.append({
                            "hash": full_h,
                            "size_bytes": sz,
                            "size_mb": round(sz / (1024 * 1024), 2),
                            "original": {
                                "file_name": original.name,
                                "relative_path": orig_rel,
                                "full_path": str(original.resolve()),
                                "modified_at": original.stat().st_mtime,
                            },
                            "duplicates": dup_items,
                            "duplicate_count": len(dup_items),
                            "group_reclaimable_bytes": sz * len(dup_items),
                            "group_reclaimable_mb": round((sz * len(dup_items)) / (1024 * 1024), 2),
                        })

            return {
                "total_scanned_files": total_scanned,
                "duplicate_groups_count": len(duplicate_groups),
                "total_duplicate_files": sum(g["duplicate_count"] for g in duplicate_groups),
                "reclaimable_bytes": reclaimable_bytes,
                "reclaimable_mb": round(reclaimable_bytes / (1024 * 1024), 2),
                "reclaimable_gb": round(reclaimable_bytes / (1024 * 1024 * 1024), 2),
                "groups": duplicate_groups,
            }

    @classmethod
    def clean_duplicates(
        cls,
        duplicate_paths: List[str],
        move_to_trash: bool = True,
    ) -> Dict[str, Any]:
        """Safely cleans the specified duplicate file paths.

        A file is only removed when at least one other byte-identical copy
        (verified by full SHA-256, living in INBOX/RAW and NOT part of this
        same request) survives. Unique files and groups whose every copy was
        requested are refused: they are reported in `errors` / `skipped` and
        nothing from that group is touched. Relative inputs resolve against
        BASE_DIR. The same rules apply with move_to_trash=False.
        """
        with _DEDUP_LOCK:
            cleaned_count = 0
            freed_bytes = 0
            errors: List[str] = []
            skipped: List[str] = []

            inbox_root = INBOX_DIR.resolve()
            raw_root = RAW_DIR.resolve()

            # Step 1: resolve + sandbox-check every requested path (de-duplicated).
            requested: Dict[Path, str] = {}
            for path_str in duplicate_paths:
                raw_p = Path(path_str)
                if not raw_p.is_absolute():
                    raw_p = BASE_DIR / raw_p
                p = raw_p.resolve()
                # Security sanity checks: must be within INBOX_DIR or RAW_DIR
                if not (p.is_relative_to(inbox_root) or p.is_relative_to(raw_root)):
                    errors.append(f"Security: Path outside allowed directories: '{path_str}'")
                    continue
                if not p.exists() or not p.is_file():
                    continue
                requested.setdefault(p, path_str)

            if not requested:
                return cls._clean_result(cleaned_count, freed_bytes, errors, skipped)

            # Step 2: hash the requested files and group them by content.
            by_hash: Dict[str, List[Path]] = {}
            for p in requested:
                digest = cls._full_sha256(p)
                if digest is None:
                    errors.append(f"Failed hashing '{p.name}': cannot read file")
                    skipped.append(requested[p])
                    continue
                by_hash.setdefault(digest, []).append(p)

            if not by_hash:
                return cls._clean_result(cleaned_count, freed_bytes, errors, skipped)

            if move_to_trash:
                TRASH_DIR.mkdir(parents=True, exist_ok=True)

            # Step 3: per content group, require a surviving copy outside the request.
            for digest, group in by_hash.items():
                survivors = cls._find_surviving_copies(digest, group, set(requested))
                if not survivors:
                    for p in group:
                        errors.append(
                            f"Safety: no other identical copy would remain, refusing to delete '{requested[p]}'"
                        )
                        skipped.append(requested[p])
                    continue

                for p in group:
                    # Re-verify (sha256) a survivor right before each deletion.
                    survivors = [s for s in survivors if s.is_file() and cls._full_sha256(s) == digest]
                    if not survivors:
                        errors.append(
                            f"Safety: identical copy disappeared, refusing to delete '{requested[p]}'"
                        )
                        skipped.append(requested[p])
                        continue

                    try:
                        file_sz = p.stat().st_size
                        if move_to_trash:
                            target = TRASH_DIR / p.name
                            # Handle duplicate filenames in trash
                            counter = 1
                            while target.exists():
                                target = TRASH_DIR / f"{p.stem}_{counter}{p.suffix}"
                                counter += 1
                            p.rename(target)
                        else:
                            p.unlink()

                        cleaned_count += 1
                        freed_bytes += file_sz
                    except Exception as e:
                        errors.append(f"Failed cleaning '{p.name}': {str(e)}")

            return cls._clean_result(cleaned_count, freed_bytes, errors, skipped)

    @staticmethod
    def _clean_result(
        cleaned_count: int, freed_bytes: int, errors: List[str], skipped: List[str]
    ) -> Dict[str, Any]:
        return {
            "status": "ok",
            "cleaned_count": cleaned_count,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "errors": errors,
            "skipped": skipped,
        }

    @classmethod
    def _find_surviving_copies(
        cls, digest: str, group: List[Path], requested: set,
    ) -> List[Path]:
        """Other copies in INBOX/RAW with the same SHA-256 that are not being deleted."""
        sizes = set()
        for p in group:
            try:
                sizes.add(p.stat().st_size)
            except OSError:
                continue

        survivors: List[Path] = []
        seen: set = set()
        for d in (INBOX_DIR, RAW_DIR):
            if not d.exists():
                continue
            for root, _, files in os.walk(d):
                for fname in files:
                    cand = Path(root) / fname
                    try:
                        resolved = cand.resolve()
                        if resolved in requested or resolved in seen or not resolved.is_file():
                            continue
                        if resolved.stat().st_size not in sizes:
                            continue
                    except OSError:
                        continue
                    seen.add(resolved)
                    if cls._full_sha256(resolved) == digest:
                        survivors.append(resolved)
        return survivors

    @staticmethod
    def _quick_hash(p: Path) -> Optional[str]:
        """Computes quick partial hash of file (head 64KB + tail 64KB)."""
        try:
            sz = p.stat().st_size
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                if sz <= 131072:
                    hasher.update(f.read())
                else:
                    hasher.update(f.read(65536))
                    f.seek(-65536, os.SEEK_END)
                    hasher.update(f.read(65536))
            return hasher.hexdigest()
        except OSError:
            return None

    @staticmethod
    def _full_sha256(p: Path) -> Optional[str]:
        """Computes full SHA-256 hash of file."""
        try:
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return None

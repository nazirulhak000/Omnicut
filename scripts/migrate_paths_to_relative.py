"""
One-time (but idempotent, re-run-safe) migration: rewrite absolute
filesystem paths already stored in _Docs/products.json into BASE_DIR-relative
ones, per SAAS_READINESS_PLAN.md P0 item 4.

Fields rewritten, per product/angle:
  - angle.video_url               (string or None)
  - angle.selected_videos[]       (list of strings)
  - angle.selected_video          (string or None -- mirrors selected_videos[0])
  - video.path                    (kept absolute -- see note below)
  - video.rel_path                (made genuinely relative -- it used to be
                                    a duplicate of the absolute `path`)

Why `video.path` stays absolute
--------------------------------
scripts/api_videos.py (a file this task is not allowed to touch --
another developer is editing it right now) does exact string comparisons
like `v.get("path") == str(some_absolute_path)` when renaming or
batch-deleting raw footage. Rewriting `path` to a relative string here
would silently break those comparisons forever (they'd never match again)
with no code change on this end to fix it. So this script leaves `path`
exactly as it is and only fixes `rel_path` to be a real BASE_DIR-relative
value instead of a second absolute copy.

What is NOT rewritten
----------------------
A path outside BASE_DIR (a different machine's absolute root, or anything
under CAPCUT_DRAFT_DIR under %LOCALAPPDATA%) is left completely untouched --
see scripts/path_utils.py's to_relative()/to_absolute() for why: there is no
way to rebase it onto this machine's BASE_DIR without guessing, so the
existing "file not found" handling downstream is left to report it rather
than this script silently mangling the value.

Safety
------
- Idempotent: a path already relative is a no-op (to_relative() returns it
  normalized-slashes-only); running this script N times produces the same
  result as running it once.
- Only ever rewrites a value when to_relative() actually changes it AND the
  resulting relative path, resolved back via to_absolute(), points at the
  exact same file the original absolute path did (a belt-and-suspenders
  round-trip check -- see `_safe_to_relative` below). If that check fails
  for any reason, the original value is left untouched and reported.
- Never touches _Docs/products.json directly -- it goes through
  ProductStore._load()/_save() exactly like backfill_product_codes.py does,
  so the SQLite store (the actual source of truth per scripts/db.py) and
  the JSON mirror both get updated together, atomically, the same way every
  other write in this app happens.

Usage
-----
    python -m scripts.migrate_paths_to_relative
    python -m scripts.migrate_paths_to_relative --dry-run
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple

from scripts import product_store as ps
from scripts.product_store import ProductStore

# Go through product_store's own _to_relative/_to_absolute (not path_utils
# directly) so this migration honors the same BASE_DIR product_store itself
# would use -- tests monkeypatch `product_store.BASE_DIR`, and this keeps
# the migration script consistent with that instead of silently reading
# path_utils' own separate BASE_DIR import.
to_relative = ps._to_relative
to_absolute = ps._to_absolute


def _safe_to_relative(value: Optional[str]) -> Tuple[Optional[str], bool]:
    """Returns (new_value, changed). Falls back to the original value,
    unchanged, if the round-trip (to_relative -> to_absolute) would not
    resolve back to the exact same absolute path -- better to leave an
    unconvertible path alone than risk silently pointing it at the wrong
    file."""
    if not value:
        return value, False

    relative = to_relative(value)
    if relative == value:
        return value, False  # already relative, or genuinely outside BASE_DIR

    try:
        original_abs = to_absolute(value)
        roundtrip_abs = to_absolute(relative)
        if original_abs is not None and roundtrip_abs is not None and str(original_abs) == str(roundtrip_abs):
            return relative, True
    except Exception:
        pass

    return value, False


def _migrate_product(product: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Mutates `product` in place. Returns (changed, notes)."""
    changed = False
    notes: List[str] = []

    for angle in product.get("angles", []) or []:
        video_url = angle.get("video_url")
        new_url, url_changed = _safe_to_relative(video_url)
        if url_changed:
            angle["video_url"] = new_url
            changed = True

        original_selected_videos = angle.get("selected_videos")
        original_first = original_selected_videos[0] if original_selected_videos else None
        # selected_video mirrors selected_videos[0] elsewhere in ProductStore
        # (see update_angle_videos/set_default_videos_for_all_angles) -- note
        # whether that mirror held BEFORE this angle's fields are touched
        # below, so it can be kept in sync afterwards.
        selected_video = angle.get("selected_video")
        mirrors_first = bool(original_selected_videos) and selected_video == original_first

        if isinstance(original_selected_videos, list):
            new_list = []
            list_changed = False
            for v in original_selected_videos:
                new_v, v_changed = _safe_to_relative(v)
                new_list.append(new_v)
                list_changed = list_changed or v_changed
            if list_changed:
                angle["selected_videos"] = new_list
                changed = True
                if mirrors_first:
                    angle["selected_video"] = new_list[0] if new_list else None
                    selected_video = angle["selected_video"]  # already migrated

        if selected_video and not mirrors_first:
            new_sv, sv_changed = _safe_to_relative(selected_video)
            if sv_changed:
                angle["selected_video"] = new_sv
                changed = True

    for video in product.get("videos", []) or []:
        # `path` is deliberately left untouched -- see module docstring.
        rel_path = video.get("rel_path")
        new_rel, rel_changed = _safe_to_relative(rel_path)
        if rel_changed:
            video["rel_path"] = new_rel
            changed = True
        elif rel_path and video.get("path") and rel_path == video.get("path"):
            # The historical bug: rel_path was a verbatim copy of the
            # absolute `path`, and _safe_to_relative() above only rewrites
            # when to_relative() changes the value from what to_relative
            # itself would already return unchanged. Handle this exact case
            # explicitly: rel_path currently equals the absolute path, so
            # convert it directly (path itself is left alone).
            candidate = to_relative(rel_path)
            if candidate != rel_path:
                original_abs = to_absolute(rel_path)
                roundtrip_abs = to_absolute(candidate)
                if original_abs is not None and roundtrip_abs is not None and str(original_abs) == str(roundtrip_abs):
                    video["rel_path"] = candidate
                    changed = True
                else:
                    notes.append(
                        f"video rel_path could not be safely rebased (round-trip mismatch): {rel_path!r}"
                    )
            # else: already relative, or genuinely outside BASE_DIR -- leave it.

    return changed, notes


def migrate(dry_run: bool = False) -> int:
    """Returns 0 on success (including "nothing to do")."""
    # Maintenance over every channel: one transaction, only changed rows are
    # rewritten (never a whole-table replace), channel_id is never touched.
    def _apply(product):
        changed, notes = _migrate_product(product)
        return changed, [f"{product.get('id')}: {n}" for n in notes]

    results = ProductStore.apply_to_each_product(_apply, all_channels=True, dry_run=True)
    print(f"Loaded {len(results)} product(s) from the store.")

    total_changed = sum(1 for changed, _ in results if changed)
    all_notes: List[str] = [note for _, notes in results for note in notes]

    print(f"{total_changed} product(s) have at least one path field rewritten to relative.")
    if all_notes:
        print(f"\n{len(all_notes)} path value(s) could not be safely converted (left unchanged):")
        for note in all_notes:
            print(f"  - {note}")

    if dry_run:
        print("\n--dry-run: not saving. Re-run without --dry-run to persist these changes.")
        return 0

    if total_changed:
        ProductStore.apply_to_each_product(_apply, all_channels=True)
        print("\nSaved.")
    else:
        print("\nNothing to save -- every path field was already relative (or safely left as-is).")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Only report what would change, do not save.")
    args = parser.parse_args()
    sys.exit(migrate(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

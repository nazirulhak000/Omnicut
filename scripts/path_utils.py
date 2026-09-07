"""
Store-relative path convention, shared by every record that persists a
filesystem path (ProductStore videos/angles, ProjectManifest, AssetRegistry).

Why
---
_Docs/products.json (and project.json) used to hold absolute Windows paths
baked in at write time, e.g. "D:\\Winona\\Programmer\\Capcut\\01_Raw\\...".
scripts/config.py already computes BASE_DIR dynamically from wherever the
repo happens to live, so the CODE is portable -- moving the project,
renaming the folder, or running in a container only broke because the DATA
kept an absolute path from the machine it was written on. It is also a hard
blocker for ever moving media to object storage, which has no notion of
"the app's working directory" to resolve a relative path against.

`media_service.get_file_info()` already established the convention this
module generalizes: store paths relative to BASE_DIR, forward slashes,
resolve back to absolute only at the point something needs to touch disk.

Convention
----------
- On WRITE: `to_relative()` turns a path into a BASE_DIR-relative POSIX
  string whenever the path is actually inside BASE_DIR. A path outside
  BASE_DIR (a different machine's absolute root, or CAPCUT_DRAFT_DIR, which
  legitimately lives outside the repo under %LOCALAPPDATA%) is returned
  unchanged -- there is nothing meaningful to rebase it against, and
  silently rewriting it would risk pointing at the wrong file. This mirrors
  the one other place in the codebase that already had to make this exact
  call: scripts/api_videos.py's `/api/media/{file_path:path}` route accepts
  either an absolute path or one relative to BASE_DIR/CAPCUT_DRAFT_DIR.
- On READ: `to_absolute()` accepts whatever shape is already stored --
  BASE_DIR-relative (the new convention), absolute-and-inside-BASE_DIR
  (old data, or data not yet migrated), or absolute-and-outside-BASE_DIR
  (a foreign root, e.g. a record written on another machine, or a
  CAPCUT_DRAFT_DIR path). The foreign-root case is passed through
  unresolved and unchanged: it cannot be rebased onto this machine's
  BASE_DIR without guessing, so the existing not-found handling downstream
  (`Path.exists()` returning False, or the 403/404 the media route already
  raises) is left to report it rather than this module raising or silently
  mangling the value.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from scripts.config import BASE_DIR

try:
    from scripts.config import CAPCUT_DRAFT_DIR
except ImportError:  # pragma: no cover - config always defines this today
    CAPCUT_DRAFT_DIR = None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def to_relative(path: object, base_dir: Optional[Path] = None) -> Optional[str]:
    """Normalize a path-shaped value for storage.

    Returns a BASE_DIR-relative, forward-slash string when `path` resolves
    inside `base_dir` (default: the real BASE_DIR). A value already relative
    is returned as a normalized forward-slash string as-is (assumed already
    relative to base_dir -- it is not re-resolved against the current
    working directory, since callers may run from anywhere).

    A path outside base_dir (including one that fails to resolve at all,
    e.g. a different drive letter on Windows) is returned UNCHANGED --
    there is no meaningful way to rebase it, per the module docstring.

    None / empty input passes through as None / "" unchanged so call sites
    that do `field = to_relative(field) if field else None` do not need a
    separate guard.
    """
    if path is None:
        return None
    text = str(path).strip()
    if not text:
        return text

    root = (base_dir or BASE_DIR).resolve()
    candidate = Path(text)

    if not candidate.is_absolute():
        # Already relative (new convention, or a bare filename). Just
        # normalize slash direction -- do not touch cwd or existence.
        return text.replace("\\", "/")

    try:
        resolved = candidate.resolve()
    except (OSError, ValueError):
        return text  # cannot even resolve it -- pass through unchanged

    if _is_within(resolved, root):
        return str(resolved.relative_to(root)).replace("\\", "/")

    # Outside BASE_DIR entirely (foreign machine root, CAPCUT_DRAFT_DIR,
    # etc). Nothing to rebase against -- keep as absolute.
    return text.replace("\\", "/") if len(Path(text).parts) else text


def to_absolute(path: object, base_dir: Optional[Path] = None) -> Optional[Path]:
    """Resolve a stored path-shaped value back to an absolute Path for disk
    access (open(), exists(), ffmpeg, etc).

    Handles all three shapes a record can hold today:
      - BASE_DIR-relative (new convention)              -> base_dir / path
      - absolute, inside base_dir (old, un-migrated data) -> Path(path) as-is
      - absolute, outside base_dir (foreign root, or
        CAPCUT_DRAFT_DIR)                                 -> Path(path) as-is,
        unchanged -- callers get the existing not-found/access-denied
        handling instead of a guess.

    None / empty input returns None.
    """
    if path is None:
        return None
    text = str(path).strip()
    if not text:
        return None

    root = (base_dir or BASE_DIR).resolve()
    candidate = Path(text)

    if candidate.is_absolute():
        return candidate

    return root / text


def is_probably_relative(path: object) -> bool:
    """True if `path` looks like it is already in the BASE_DIR-relative
    convention (not an absolute filesystem path). Used by call sites that
    want to avoid re-normalizing a value that is already correct."""
    if not path:
        return False
    return not Path(str(path)).is_absolute()

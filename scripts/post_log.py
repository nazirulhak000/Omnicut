"""
Post log — the feedback loop.

Every clip that actually goes live gets a row here, and 48 hours later the
numbers get filled in by hand. Without this the angle picker is guessing
forever; with it, the app can tell which angles and hooks earn clicks.

Storage is SQLite (see scripts/db.py) behind the exact same _load()/_save()
contract this module always had, mirrored out to a plain JSON file so it
stays readable, hand-editable, and diffable as a backup. The mirror file
lives at LOG_PATH, same path as before.
"""

import json
import re
import uuid
import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR
from scripts.channel_ownership import OWNER_KEY, StoreScope, owner_for_new_record, resolve_store_scope
from scripts.db import DocumentTable

LOG_PATH = BASE_DIR / "_Docs" / "post_log.json"
METRICS_DUE_HOURS = 48

METRIC_FIELDS = (
    "views", "likes", "comments", "shares", "cart_clicks", "orders", "commission_thb",
    # Retention (Q6, optional): seconds and a 0-1 fraction. Present only when
    # the Studio export / manual entry carried them; never defaulted to 0.
    "avg_watch_time_sec", "completion_rate",
)
# Metrics stored as float; every other METRIC_FIELDS entry is an int count.
FLOAT_METRIC_FIELDS = ("commission_thb", "avg_watch_time_sec", "completion_rate")
COUNT_METRIC_FIELDS = ("views", "likes", "comments", "shares")
RETENTION_METRIC_FIELDS = ("avg_watch_time_sec", "completion_rate")

# Style dimensions a post row may carry (copied from the export registry at
# mark-posted time) and that style_performance() can group by.
STYLE_GROUP_FIELDS = ("style_preset", "hook_style", "story_format")
DEFAULT_STORY_FORMAT = "classic"

# Every metrics write appends a point-in-time snapshot to `metrics_history`
# (the latest numbers still live in `metrics`). A snapshot only counts as a
# "measured" result once the post was at least METRICS_DUE_HOURS old when it
# was captured -- a 1-hour sync is not a 48-hour number.
METRICS_HISTORY_CAP = 30

# Clip names that carry no identity (fallbacks used when a clip is unknown);
# never used as a de-duplication key.
_GENERIC_CLIP_NAMES = {"", "clip.mp4", "video.mp4"}


def _parse_dt(value: Any) -> Optional[datetime.datetime]:
    """ISO string -> naive local datetime (post_log stores naive local time).

    Offset-aware values are converted to local time so comparisons against
    datetime.now() never raise on mixed naive/aware input.
    """
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _age_hours(posted_at: Any, at: Optional[datetime.datetime]) -> Optional[float]:
    posted = _parse_dt(posted_at)
    if posted is None or at is None:
        return None
    return round(max(0.0, (at - posted).total_seconds() / 3600.0), 2)


_DURATION_UNIT_RE = re.compile(r"(seconds?|secs?|sec|s|วินาที|วิ\.?)$")
_MIN_SEC_RE = re.compile(r"^(?:(\d+(?:\.\d+)?)\s*(?:m|min|mins|นาที))?\s*(?:(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds?|วินาที|วิ\.?))?$")


def parse_watch_time_sec(value: Any) -> Optional[float]:
    """Average watch time -> seconds (float >= 0) or None.

    Accepts numbers, ``"12.5"``, ``"12.5s"``, ``"12.5 วินาที"``, ``"0:12"``,
    ``"1:02:03"`` and ``"1m 5s"`` (TikTok Studio / CSV variants).
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text = str(value).strip().lower().replace(",", "")
        if not text:
            return None
        try:
            if ":" in text:
                parts = [float(part) for part in text.split(":")]
                if len(parts) > 3:
                    return None
                seconds = 0.0
                for part in parts:
                    seconds = seconds * 60 + part
            else:
                compact = text.replace(" ", "")
                try:
                    seconds = float(_DURATION_UNIT_RE.sub("", compact))
                except ValueError:
                    match = _MIN_SEC_RE.match(text)
                    if not match or not any(match.groups()):
                        return None
                    seconds = float(match.group(1) or 0) * 60 + float(match.group(2) or 0)
        except ValueError:
            return None
    if seconds != seconds or seconds in (float("inf"), float("-inf")) or seconds < 0:
        return None
    return round(seconds, 2)


def parse_completion_rate(value: Any) -> Optional[float]:
    """Completion / "watched full video" -> fraction 0..1 or None.

    ``"45.3%"`` -> 0.453; a bare number <= 1 is already a fraction; a bare
    number in (1, 100] is read as a percentage.  Anything else -> None.
    """
    if value is None or isinstance(value, bool):
        return None
    percent = False
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace(",", ".").replace(" ", "")
        if text.endswith("%"):
            percent, text = True, text[:-1]
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    if number != number or number < 0:
        return None
    if percent or number > 1:
        if number > 100:
            return None
        number /= 100.0
    return round(number, 4)


def _clean_duration(value: Any) -> Optional[float]:
    """Positive clip duration in seconds (0.01 s) or None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds != seconds or seconds == float("inf") or seconds <= 0:
        return None
    return round(seconds, 2)


def _median(values: List[float]) -> Optional[float]:
    ordered = sorted(values)
    if not ordered:
        return None
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _mean(values: List[float]) -> Optional[float]:
    return (sum(values) / len(values)) if values else None


def _row_metrics(row: Dict[str, Any]) -> Dict[str, Any]:
    """Metrics carried by one Studio row: int counts + optional retention."""
    metrics: Dict[str, Any] = {
        k: row.get(k) for k in COUNT_METRIC_FIELDS
        if isinstance(row.get(k), int) and not isinstance(row.get(k), bool)
    }
    watch = parse_watch_time_sec(row.get("avg_watch_time_sec"))
    if watch is not None:
        metrics["avg_watch_time_sec"] = watch
    rate = parse_completion_rate(row.get("completion_rate"))
    if rate is not None:
        metrics["completion_rate"] = rate
    return metrics


def _clip_name(value: Any) -> str:
    """Basename of a clip path, casefolded; '' for generic placeholder names."""
    name = Path(str(value or "").replace("\\", "/")).name.casefold()
    return "" if name in _GENERIC_CLIP_NAMES else name


def _snapshot_is_mature(snapshot: Dict[str, Any]) -> bool:
    age = snapshot.get("age_hours")
    if isinstance(age, (int, float)):
        return age >= METRICS_DUE_HOURS
    # Age unknown: only a seeded legacy snapshot (measured before history
    # existed) is trusted; anything else cannot be proven to be a 48h number.
    return bool(snapshot.get("legacy"))


def _record_metrics(post: Dict[str, Any], new_metrics: Dict[str, Any], now_dt: datetime.datetime) -> None:
    """Set the post's latest `metrics` and append a `metrics_history` snapshot."""
    history = [h for h in (post.get("metrics_history") or []) if isinstance(h, dict)]
    if not history and post.get("metrics"):
        # Legacy row measured before history existed: seed one snapshot from
        # the old numbers so the first new sync does not erase their meaning.
        filled = post.get("metrics_filled_at")
        age = _age_hours(post.get("posted_at"), _parse_dt(filled))
        seed = {"metrics": dict(post["metrics"]), "captured_at": filled, "age_hours": age}
        if age is None:
            seed["legacy"] = True
        history.append(seed)
    post["metrics"] = new_metrics
    post["metrics_filled_at"] = now_dt.isoformat(timespec="seconds")
    history.append({
        "metrics": dict(new_metrics),
        "captured_at": post["metrics_filled_at"],
        "age_hours": _age_hours(post.get("posted_at"), now_dt),
    })
    while len(history) > METRICS_HISTORY_CAP:
        # Drop the oldest entry, but pin the earliest mature snapshot: it is
        # the closest thing to the "48h number" analytics rely on.
        pinned = next((i for i, h in enumerate(history) if _snapshot_is_mature(h)), None)
        history.pop(1 if pinned == 0 else 0)
    post["metrics_history"] = history


def mature_metrics(post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The metrics analytics may trust for one post, or None.

    - With `metrics_history`: the EARLIEST snapshot captured when the post was
      >= 48h old (earliest = most comparable across posts; later snapshots
      keep drifting upward). No such snapshot -> None (not measured yet).
    - Legacy row without history: the latest `metrics`, as before.
    """
    history = post.get("metrics_history")
    if isinstance(history, list) and history:
        for snap in history:
            if isinstance(snap, dict) and snap.get("metrics") and _snapshot_is_mature(snap):
                return snap["metrics"]
        return None
    return post.get("metrics") or None


def _log_db_path() -> Path:
    # Same sqlite file ProductStore uses (BASE_DIR/_Docs/store.db), different
    # table -- both stores' JSON mirrors already live side by side in _Docs/.
    return LOG_PATH.parent / "store.db"


def _log_json_path() -> Path:
    # Read LOG_PATH dynamically (not captured at import time) so tests that
    # monkeypatch scripts.post_log.LOG_PATH keep working.
    return LOG_PATH


_TABLE = DocumentTable("posts", _log_db_path, _log_json_path)


class PostLog:
    """Append-only record of posted clips plus their measured results.

    Channel ownership (multi-channel P2.2, ADR §12/§13): every row carries a
    top-level ``channel_id`` (rows without it are legacy = ``main`` in compat
    mode only).  Public methods take keyword ``channel_id``/``all_channels``
    like ``ProductStore``; ``None`` keeps the old unscoped behaviour in
    compat mode and fails closed (422) in strict mode.  Idempotency, the
    legacy basename fallback and fuzzy matching only ever look at rows of
    the request's channel, and a basename fallback never guesses: it matches
    only when exactly one row qualifies.
    """

    # ------------------------------------------------------------------
    # Storage (internal full-table access -- all channels)
    # ------------------------------------------------------------------
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def _save(cls, posts: List[Dict[str, Any]]) -> None:
        _TABLE.save(posts)

    @classmethod
    def _mutate(cls):
        """See ProductStore._mutate() -- same fix, same reasoning: hold one
        SQLite transaction across the read-modify-write instead of loading
        outside any lock."""
        return _TABLE.mutate()

    @staticmethod
    def _scope(channel_id: Optional[str] = None, all_channels: bool = False) -> StoreScope:
        return resolve_store_scope(channel_id, all_channels=all_channels)

    @classmethod
    @contextmanager
    def _scoped_mutate(cls, scope: StoreScope):
        """Scoped calls -> ``DocumentTable.scoped_mutate`` (other channels'
        rows never exposed nor written); unscoped -> the old ``cls._mutate()``."""
        if scope.unscoped:
            with cls._mutate() as posts:
                yield posts
            return
        with _TABLE.scoped_mutate(scope.channel_id, include_legacy=scope.include_legacy) as posts:
            yield posts

    @classmethod
    def _scoped_load(cls, scope: StoreScope) -> List[Dict[str, Any]]:
        rows = cls._load()
        if scope.unscoped:
            return rows
        return [row for row in rows if scope.owns(row)]

    @classmethod
    def owner_of(cls, post_id: str) -> tuple[bool, Optional[str]]:
        """``(exists, channel_id)`` across ALL channels (system read for 404 guards)."""
        for post in cls._load():
            if post.get("id") == post_id:
                return True, post.get(OWNER_KEY)
        return False, None

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------
    @classmethod
    def add_post(
        cls,
        product_name: str,
        clip_file: str,
        platform: str = "tiktok",
        product_url: str = "",
        angle_key: str = "",
        angle_title: str = "",
        hook: str = "",
        caption: str = "",
        hashtags: Optional[List[str]] = None,
        posted_at: Optional[str] = None,
        style_preset: str = "",
        hook_color: str = "",
        product_id: str = "",
        scheduled_at: str = "",
        export_id: str = "",
        source: str = "",
        hook_style: str = "",
        story_format: str = "",
        duration_sec: Optional[float] = None,
        hook_text: str = "",
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Record that a clip went live. Returns the stored row.

        The trailing keyword fields are optional and only written when given,
        so rows created by older callers keep their exact old shape (plus the
        server-stamped ``channel_id`` owner).
        """
        now = datetime.datetime.now()
        scope = cls._scope(channel_id, all_channels)
        owner = owner_for_new_record(scope)

        # _mutate() holds one SQLite transaction across the read-modify-write
        # (P0 item 1 / plan step 2) -- two concurrent add_post() calls used to
        # both read the same posts list outside any lock and could silently
        # drop one row on save; the id used to collide too (see the uuid4
        # below -- was f"{timestamp}_{len(posts)+1}", which two posts added
        # in the same second at the same list length would share).
        with cls._scoped_mutate(scope) as posts:
            post = {
                "id": uuid.uuid4().hex,
                OWNER_KEY: owner,
                "product_name": product_name,
                "product_url": product_url,
                "angle_key": angle_key,
                "angle_title": angle_title,
                "hook": hook,
                "clip_file": clip_file,
                "platform": platform,
                "caption": caption,
                "hashtags": hashtags or [],
                "posted_at": posted_at or now.isoformat(timespec="seconds"),
                "metrics": None,
                "metrics_filled_at": None,
            }
            extras = {
                "style_preset": style_preset, "hook_color": hook_color, "product_id": product_id,
                "scheduled_at": scheduled_at, "export_id": export_id, "source": source,
                "hook_style": hook_style, "story_format": story_format,
                "duration_sec": _clean_duration(duration_sec), "hook_text": (hook_text or "")[:200],
            }
            post.update({k: v for k, v in extras.items() if v})
            posts.append(post)
            return post

    @classmethod
    def register_posted_export(
        cls,
        product_name: str,
        clip_file: str,
        export_id: str = "",
        product_id: str = "",
        angle_key: str = "",
        angle_title: str = "",
        hook: str = "",
        style_preset: str = "",
        hook_color: str = "",
        caption: str = "",
        hashtags: Optional[List[str]] = None,
        scheduled_at: str = "",
        posted_at: Optional[str] = None,
        hook_style: str = "",
        story_format: str = "",
        duration_sec: Optional[float] = None,
        hook_text: str = "",
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Idempotently log one posted export (called from mark-posted).

        Returns the stored row, or ``None`` when the legacy basename fallback
        was ambiguous (nothing written -- see :meth:`record_posted_export`,
        which returns the full result for callers that report it).
        """
        return cls.record_posted_export(
            product_name=product_name, clip_file=clip_file, export_id=export_id, product_id=product_id,
            angle_key=angle_key, angle_title=angle_title, hook=hook, style_preset=style_preset,
            hook_color=hook_color, caption=caption, hashtags=hashtags, scheduled_at=scheduled_at,
            posted_at=posted_at, hook_style=hook_style, story_format=story_format,
            duration_sec=duration_sec, hook_text=hook_text,
            channel_id=channel_id, all_channels=all_channels,
        )["post"]

    @classmethod
    def record_posted_export(
        cls,
        product_name: str,
        clip_file: str,
        export_id: str = "",
        product_id: str = "",
        angle_key: str = "",
        angle_title: str = "",
        hook: str = "",
        style_preset: str = "",
        hook_color: str = "",
        caption: str = "",
        hashtags: Optional[List[str]] = None,
        scheduled_at: str = "",
        posted_at: Optional[str] = None,
        hook_style: str = "",
        story_format: str = "",
        duration_sec: Optional[float] = None,
        hook_text: str = "",
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Idempotently log one posted export; returns ``{"status", "post", "candidate_post_ids"}``.

        Idempotency key = (channel, export identity):

        1. a row of this channel with the same ``export_id`` -> enrich it
           (``status="matched_export"``);
        2. else the legacy basename fallback, within this channel only: rows
           with the same clip basename that carry no (other) ``export_id``.
           Exactly one -> enrich it (``"matched_legacy"``); two or more ->
           ``"ambiguous"``: NOTHING is written, ``post`` is ``None`` and
           ``candidate_post_ids`` lists the rows the caller must report.
           Generic names (``clip.mp4`` ...) never take part;
        3. else create a new row stamped with the scope owner (``"created"``).

        An existing row is enriched (only empty fields are filled), never
        duplicated or overwritten -- the same key upsert_tiktok_stats'
        auto-register and attach_manual use, so a later stats sync merges into
        THIS row instead of creating a second one.
        """
        wanted = {
            "product_name": product_name, "product_id": product_id, "angle_key": angle_key,
            "angle_title": angle_title or hook, "hook": hook, "style_preset": style_preset,
            "hook_color": hook_color, "caption": caption, "scheduled_at": scheduled_at,
            "export_id": export_id,
            # Q6 style metadata (optional; only non-empty values are written).
            "hook_style": hook_style, "story_format": story_format,
            "duration_sec": _clean_duration(duration_sec), "hook_text": (hook_text or "")[:200],
        }
        name = _clip_name(clip_file)
        scope = cls._scope(channel_id, all_channels)

        def enrich(post: Dict[str, Any]) -> None:
            for key, value in wanted.items():
                if value and not post.get(key):
                    post[key] = value
            if hashtags and not post.get("hashtags"):
                post["hashtags"] = list(hashtags)

        with cls._scoped_mutate(scope) as posts:
            if export_id:
                by_export = next((post for post in posts if post.get("export_id") == export_id), None)
                if by_export is not None:
                    enrich(by_export)
                    return {"status": "matched_export", "post": by_export, "candidate_post_ids": [by_export.get("id")]}
            if name:
                candidates = [
                    post for post in posts
                    if _clip_name(post.get("clip_file")) == name
                    and (not export_id or not post.get("export_id"))
                ]
                if len(candidates) == 1:
                    enrich(candidates[0])
                    return {"status": "matched_legacy", "post": candidates[0], "candidate_post_ids": [candidates[0].get("id")]}
                if len(candidates) > 1:
                    return {
                        "status": "ambiguous",
                        "post": None,
                        "candidate_post_ids": sorted(str(post.get("id")) for post in candidates),
                    }
            owner = owner_for_new_record(scope)
            post = {
                "id": uuid.uuid4().hex,
                OWNER_KEY: owner,
                "product_name": product_name,
                "product_url": "",
                "angle_key": angle_key,
                "angle_title": angle_title or hook,
                "hook": hook,
                "clip_file": clip_file,
                "platform": "tiktok",
                "caption": caption,
                "hashtags": list(hashtags or []),
                "posted_at": posted_at or datetime.datetime.now().isoformat(timespec="seconds"),
                "metrics": None,
                "metrics_filled_at": None,
                "source": "mark_posted",
            }
            post.update({k: v for k, v in wanted.items() if v and k not in post})
            posts.append(post)
            return {"status": "created", "post": post, "candidate_post_ids": [post["id"]]}

    @classmethod
    def update_metrics(
        cls,
        post_id: str,
        metrics: Dict[str, Any],
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Fill in the 48-hour numbers for one post (a post of another channel = not found)."""
        with cls._scoped_mutate(cls._scope(channel_id, all_channels)) as posts:
            for post in posts:
                if post["id"] == post_id:
                    clean = {}
                    for field in METRIC_FIELDS:
                        raw = metrics.get(field)
                        if raw in (None, ""):
                            continue
                        if field == "avg_watch_time_sec":
                            value = parse_watch_time_sec(raw)
                        elif field == "completion_rate":
                            value = parse_completion_rate(raw)
                        else:
                            try:
                                value = float(raw) if field in FLOAT_METRIC_FIELDS else int(raw)
                            except (TypeError, ValueError):
                                value = None
                        if value is None:
                            raise ValueError(f"ค่า '{field}' ต้องเป็นตัวเลข (ได้: {raw!r})")
                        clean[field] = value

                    now_dt = datetime.datetime.now()
                    if clean:
                        _record_metrics(post, clean, now_dt)
                    else:
                        post["metrics"] = clean
                        post["metrics_filled_at"] = now_dt.isoformat(timespec="seconds")
                    return post

            raise ValueError(f"ไม่พบโพสต์ id '{post_id}'")

    @classmethod
    def upsert_tiktok_stats(
        cls,
        rows: List[Dict[str, Any]],
        register_missing: bool = False,
        clip_candidates: Optional[List[Dict[str, Any]]] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Merge scraped TikTok Studio rows into the post log.

        Scoped (P2.2): video-id, fuzzy and clip-basename matching only see
        posts of ``channel_id``; registered posts are stamped with it.  The
        clip-basename link to an existing post requires exactly one eligible
        post -- with two or more the Studio row stays ``unmatched`` (carrying
        ``ambiguous_post_ids``) instead of guessing or registering a duplicate.

        Match priority: tiktok_video_id exact > clip title+duration fuzzy.
        With register_missing=True, a row that matches nothing is checked
        against `clip_candidates` (exported clips from the product store)
        and, on a hit, a NEW post is registered automatically -- the numbers
        were real, the clip was just never marked posted in OmniCut. Rows
        that match nothing at all stay `unmatched` for manual review instead
        of inventing new posts silently.
        """
        matched, updated, registered = 0, 0, 0
        unmatched = []
        now_dt = datetime.datetime.now()
        now = now_dt.isoformat(timespec="seconds")
        scope = cls._scope(channel_id, all_channels)
        # Owner for auto-registered posts; resolved lazily so a maintenance
        # (all_channels) run that only updates existing rows still works.
        new_owner: List[str] = []

        def new_post_owner() -> str:
            if not new_owner:
                new_owner.append(owner_for_new_record(scope))
            return new_owner[0]

        with cls._scoped_mutate(scope) as posts:
            by_video_id = {p.get("tiktok_video_id"): p for p in posts if p.get("tiktok_video_id")}
            # One post may be claimed by ONE Studio row per run: two rows with
            # similar captions (same product, different clips) used to
            # fuzzy-match the same target and the later row's metrics silently
            # overwrote the first row's real numbers (Lift 59 -> 370 bug).
            claimed: Dict[str, str] = {}
            claimed_cand_keys: set = set()
            for row_idx, row in enumerate(rows):
                video_id = (row.get("video_id") or "").strip() if isinstance(row.get("video_id"), str) else row.get("video_id")
                claim = str(video_id or f"row#{row_idx}")
                ambiguous_ids: List[str] = []
                metrics = _row_metrics(row)
                target = by_video_id.get(video_id) if video_id else None
                if target is None and row.get("title"):
                    fuzzy = cls._fuzzy_match(posts, row)
                    if fuzzy is not None:
                        stored_vid = str(fuzzy.get("tiktok_video_id") or "")
                        owner = claimed.get(str(fuzzy.get("id")))
                        if (not stored_vid or not video_id or stored_vid == str(video_id)) and owner in (None, claim):
                            target = fuzzy
                        # else: this post already belongs to another Studio
                        # video (stored video id or claimed earlier this run) --
                        # fall through to candidate registration / unmatched
                        # instead of overwriting that video's metrics.
                if target is None and register_missing and clip_candidates:
                    best_cand = None
                    best_cand_score = 0
                    for cand in clip_candidates:
                        ckey = (cand.get("clip_file"), cand.get("product_name"), cand.get("angle_title"))
                        if ckey in claimed_cand_keys:
                            continue
                        score = cls._candidate_score(row, cand)
                        if score >= 4 and score > best_cand_score:
                            best_cand, best_cand_score = cand, score

                    if best_cand is not None:
                        cand = best_cand
                        ckey = (cand.get("clip_file"), cand.get("product_name"), cand.get("angle_title"))
                        posted_at = cls._parse_studio_posted_at(row.get("posted_text")) or now
                        # A post for this very clip may already exist (e.g.
                        # logged by mark-posted but the Studio title was too
                        # different to fuzzy-match). Link to it instead of
                        # registering a duplicate; same key as register_posted_export.
                        # Only an UNAMBIGUOUS hit links (P2.2): two eligible
                        # posts with this basename -> leave the row unmatched.
                        cand_name = _clip_name(cand.get("clip_file"))
                        eligible = []
                        if cand_name:
                            for post in posts:
                                if _clip_name(post.get("clip_file")) != cand_name:
                                    continue
                                stored_vid = str(post.get("tiktok_video_id") or "")
                                if stored_vid and video_id and stored_vid != str(video_id):
                                    continue
                                if claimed.get(str(post.get("id"))) not in (None, claim):
                                    continue
                                eligible.append(post)
                        if len(eligible) > 1:
                            ambiguous_ids = sorted(str(post.get("id")) for post in eligible)
                        elif eligible:
                            claimed_cand_keys.add(ckey)
                            target = eligible[0]
                        else:
                            claimed_cand_keys.add(ckey)
                            # Append here -- never call add_post() inside this
                            # mutate (nested _mutate on the same table would
                            # fight the open SQLite transaction).
                            new_post = {
                                "id": uuid.uuid4().hex,
                                OWNER_KEY: new_post_owner(),
                                "product_name": str(cand.get("product_name") or ""),
                                "product_url": "",
                                "angle_key": str(cand.get("angle_key") or ""),
                                "angle_title": str(cand.get("angle_title") or cand.get("hook_title") or ""),
                                "hook": str(cand.get("hook_title") or ""),
                                "clip_file": str(cand.get("clip_file") or "clip.mp4"),
                                "platform": "tiktok",
                                "caption": str(cand.get("caption") or row.get("title") or "")[:200],
                                "hashtags": [],
                                "posted_at": posted_at,
                                "metrics": None,
                                "metrics_filled_at": None,
                                "source": "tiktok_stats_auto",
                            }
                            posts.append(new_post)
                            target = new_post
                            registered += 1
                if target is None:
                    unmatched_row = dict(row)
                    unmatched_row["video_id"] = video_id
                    if ambiguous_ids:
                        unmatched_row["ambiguous_post_ids"] = ambiguous_ids
                    unmatched.append(unmatched_row)
                    continue
                matched += 1
                claimed[str(target.get("id"))] = claim
                if video_id and not target.get("tiktok_video_id"):
                    target["tiktok_video_id"] = video_id
                    by_video_id[video_id] = target
                if row.get("video_url") and not target.get("tiktok_url"):
                    target["tiktok_url"] = row.get("video_url")
                target["tiktok_synced_at"] = now
                if metrics:
                    merged = dict(target.get("metrics") or {})
                    merged.update(metrics)
                    _record_metrics(target, merged, now_dt)
                    updated += 1
        return {"matched": matched, "updated": updated, "registered": registered, "unmatched": unmatched, "total": len(rows)}

    @classmethod
    def attach_manual(
        cls,
        row: Dict[str, Any],
        post_id: Optional[str] = None,
        candidate: Optional[Dict[str, Any]] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Attach a hand-matched Studio row (from TikTokPending) to a post.

        Either post_id targets an existing post, or candidate (a library
        clip from _export_clip_candidates) attaches to the post already
        holding that clip_file/hook or registers a new post -- exactly the
        auto-register path but chosen by a human, so no score threshold
        applies.

        Scoped (P2.2): ``post_id`` / clip / hook only resolve inside the
        channel (another channel's post = not found).  A candidate match must
        be unambiguous: an exact clip-file match is tried first (generic names
        such as ``clip.mp4`` never match), then the hook; two or more hits
        raise ``ValueError`` asking for an explicit ``post_id`` instead of
        guessing.
        """
        if post_id is None and candidate is None:
            raise ValueError("ต้องระบุ post_id หรือ candidate อย่างใดอย่างหนึ่ง")
        now_dt = datetime.datetime.now()
        now = now_dt.isoformat(timespec="seconds")
        metrics = _row_metrics(row)
        video_id = (row.get("video_id") or "").strip() if isinstance(row.get("video_id"), str) else row.get("video_id")
        scope = cls._scope(channel_id, all_channels)
        with cls._scoped_mutate(scope) as posts:
            target = None
            if post_id is not None:
                for post in posts:
                    if post.get("id") == post_id:
                        target = post
                        break
                if target is None:
                    raise ValueError(f"ไม่พบโพสต์ id '{post_id}'")
            else:
                cand_clip = str(candidate.get("clip_file") or "")
                cand_hook = str(candidate.get("hook_title") or "").lower()
                clip_hits = [
                    post for post in posts
                    if cand_clip and _clip_name(cand_clip) and str(post.get("clip_file") or "") == cand_clip
                ]
                hook_hits = [
                    post for post in posts
                    if cand_hook and str(post.get("hook") or "").lower() == cand_hook
                ]
                for hits in (clip_hits, hook_hits):
                    if len(hits) > 1:
                        raise ValueError(
                            "พบโพสต์ที่ตรงกับคลิปนี้มากกว่า 1 รายการ "
                            f"({', '.join(sorted(str(p.get('id')) for p in hits))}) กรุณาเลือกโพสต์ด้วย post_id"
                        )
                    if hits:
                        target = hits[0]
                        break
                if target is None:
                    target = {
                        "id": uuid.uuid4().hex,
                        OWNER_KEY: owner_for_new_record(scope),
                        "product_name": str(candidate.get("product_name") or ""),
                        "product_url": "",
                        "angle_key": str(candidate.get("angle_key") or ""),
                        "angle_title": str(candidate.get("angle_title") or candidate.get("hook_title") or ""),
                        "hook": str(candidate.get("hook_title") or ""),
                        "clip_file": cand_clip or "clip.mp4",
                        "platform": "tiktok",
                        "caption": str(row.get("title") or "")[:200],
                        "hashtags": [],
                        "posted_at": cls._parse_studio_posted_at(row.get("posted_text")) or now,
                        "metrics": None,
                        "metrics_filled_at": None,
                        "source": "tiktok_stats_manual",
                    }
                    posts.append(target)
            if video_id and not target.get("tiktok_video_id"):
                target["tiktok_video_id"] = video_id
            if row.get("video_url") and not target.get("tiktok_url"):
                target["tiktok_url"] = row.get("video_url")
            target["tiktok_synced_at"] = now
            parsed = cls._parse_studio_posted_at(row.get("posted_text"))
            if parsed and not target.get("posted_at"):
                target["posted_at"] = parsed
            if metrics:
                merged = dict(target.get("metrics") or {})
                merged.update(metrics)
                _record_metrics(target, merged, now_dt)
            return target

    _THAI_MONTHS = {
        "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
        "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
    }

    @staticmethod
    def _normalize_title(text: Any) -> str:
        """Lowercase + strip #hashtags/emoji/symbols -- words and spaces only.

        Studio captions carry tags/emoji the OmniCut side never stores, so
        both sides must be normalized before any title comparison.
        """
        s = str(text or "").lower()
        s = re.sub(r"#\S+", " ", s)
        s = re.sub(r"[^\w\s\u0E00-\u0E7F]+", " ", s, flags=re.UNICODE)
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def _title_tokens(cls, text: Any) -> set:
        return {t for t in cls._normalize_title(text).split() if len(t) >= 2}

    @classmethod
    def _parse_studio_posted_at(cls, text: Any) -> Optional[str]:
        """'11 ส.ค. 9:30 PM' -> '2026-08-11T21:30:00' (Thai abbreviated month)."""
        s = str(text or "").strip()
        if not s:
            return None
        m = re.match(r"(\d{1,2})\s+([^\s\d]+)\s+(\d{1,2}):(\d{2})\s*(AM|PM)?", s, re.IGNORECASE)
        if not m:
            return None
        day = int(m.group(1))
        month = cls._THAI_MONTHS.get(m.group(2))
        if month is None:
            for abbr, num in cls._THAI_MONTHS.items():
                if m.group(2).startswith(abbr[:2]):
                    month = num
                    break
        if month is None:
            return None
        hour = int(m.group(3))
        minute = int(m.group(4))
        ampm = (m.group(5) or "").upper()
        if ampm == "PM" and hour < 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0
        now = datetime.datetime.now()
        year = now.year
        if month - now.month > 1:
            # Studio shows no year: a month far ahead of "now" belongs to
            # last year (e.g. ธ.ค. rows synced in ม.ค.).
            year -= 1
        try:
            return datetime.datetime(year, month, day, hour, minute).isoformat(timespec="seconds")
        except ValueError:
            return None

    @classmethod
    def _score_against_haystack(cls, title: str, haystack: str) -> int:
        """Normalized token-overlap score: shared words + brand-word bonus +
        12-char prefix containment bonus + exact phrase bonus. Zero means "no relation at all"."""
        row_tokens = cls._title_tokens(title)
        if not row_tokens:
            return 0
        hay_tokens = cls._title_tokens(haystack)
        shared = row_tokens & hay_tokens
        if not shared:
            return 0
        score = len(shared) + sum(2 for t in shared if len(t) >= 4)
        # Brand/model bonus: English words or alphanumeric models with length >= 3
        # (e.g. basike, orashare, bluewow, essager, logitech, hf04, x120, 100w)
        score += sum(3 for t in shared if any(c.isascii() and c.isalpha() for c in t) and len(t) >= 3)
        prefix = cls._normalize_title(title)[:12]
        if prefix and prefix in cls._normalize_title(haystack):
            score += 3
        norm_title = cls._normalize_title(title)
        norm_hay = cls._normalize_title(haystack)
        if norm_title and (norm_title in norm_hay or (len(norm_hay) >= 15 and norm_hay in norm_title)):
            score += 10
        return score

    @staticmethod
    def _fuzzy_match(posts: List[Dict[str, Any]], row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Best-scoring title match on normalized text (tags/emoji stripped).

        Duration filters only when BOTH sides have it (only posts logged at
        mark-posted since Q6 carry ``duration_sec``), widened to ±5s for
        encode padding differences.
        """
        title = str(row.get("title") or "").strip()
        if len(title) < 4:
            return None
        dur = row.get("duration_sec")
        best: Optional[Dict[str, Any]] = None
        best_score = 0
        for post in posts:
            haystack = " ".join(str(post.get(k) or "") for k in ("caption", "angle_title", "hook", "clip_file", "product_name", "hashtags"))
            score = PostLog._score_against_haystack(title, haystack)
            if score < 4:
                continue
            if dur is not None and post.get("duration_sec") is not None:
                try:
                    if abs(float(post["duration_sec"]) - float(dur)) > 5:
                        continue
                except (TypeError, ValueError):
                    pass
            if score > best_score or (score == best_score and best is not None and str(post.get("posted_at") or "") > str(best.get("posted_at") or "")):
                best, best_score = post, score
        return best

    @classmethod
    def _candidate_score(cls, row: Dict[str, Any], cand: Dict[str, Any]) -> int:
        title = str(row.get("title") or "").strip()
        if len(title) < 4:
            return 0
        haystack = " ".join(str(cand.get(k) or "") for k in (
            "caption", "tiktok_caption", "angle_title", "hook_title",
            "product_name", "clip_file", "hashtags", "hook_brand", "hook_model", "project_name"
        ))
        return cls._score_against_haystack(title, haystack)

    @classmethod
    def _match_candidate(cls, row: Dict[str, Any], cand: Dict[str, Any]) -> bool:
        return cls._candidate_score(row, cand) >= 4

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    @classmethod
    def list_posts(
        cls, newest_first: bool = True, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> List[Dict[str, Any]]:
        posts = cls._scoped_load(cls._scope(channel_id, all_channels))
        return sorted(posts, key=lambda p: p.get("posted_at", ""), reverse=newest_first)

    @classmethod
    def get_all(
        cls, newest_first: bool = True, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> List[Dict[str, Any]]:
        return cls.list_posts(newest_first=newest_first, channel_id=channel_id, all_channels=all_channels)

    @staticmethod
    def _pending_of(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=METRICS_DUE_HOURS)
        due = []
        for post in posts:
            if mature_metrics(post):
                continue
            posted = _parse_dt(post.get("posted_at"))
            if posted is None:
                continue
            if posted <= cutoff:
                due.append(post)
        return due

    @classmethod
    def pending_metrics(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> List[Dict[str, Any]]:
        """Posts past the 48-hour mark that have no 48-hour-old numbers yet.

        "Measured" means mature_metrics() finds a snapshot captured at post
        age >= 48h (or a legacy row with plain `metrics` and no history), so
        a sync done 1 hour after posting does not hide the post from here.
        """
        return cls._pending_of(cls._scoped_load(cls._scope(channel_id, all_channels)))

    @classmethod
    def angle_performance(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> List[Dict[str, Any]]:
        """
        Average results grouped by angle — the answer to "which angle sells".

        Only posts with filled-in metrics count, so this stays empty until the
        loop has actually run a few times.
        """
        buckets: Dict[str, Dict[str, Any]] = {}

        for post in cls._scoped_load(cls._scope(channel_id, all_channels)):
            # Latest numbers on purpose (display/back-compat); the 48h-age
            # evidence rule lives in mature_metrics() and is applied by the
            # scheduler's analytics and pending_metrics.
            metrics = post.get("metrics")
            if not metrics:
                continue
            key = post.get("angle_key") or "unspecified"
            bucket = buckets.setdefault(
                key,
                {"angle_key": key, "angle_title": post.get("angle_title", ""), "clips": 0,
                 "views": 0, "cart_clicks": 0, "orders": 0, "commission_thb": 0.0},
            )
            bucket["clips"] += 1
            bucket["views"] += metrics.get("views", 0)
            bucket["cart_clicks"] += metrics.get("cart_clicks", 0)
            bucket["orders"] += metrics.get("orders", 0)
            bucket["commission_thb"] += metrics.get("commission_thb", 0.0)

        results = []
        for bucket in buckets.values():
            views = bucket["views"]
            bucket["avg_views"] = round(views / bucket["clips"])
            bucket["cart_click_rate"] = round(bucket["cart_clicks"] / views * 100, 2) if views else 0.0
            results.append(bucket)

        return sorted(results, key=lambda b: b["commission_thb"], reverse=True)

    @staticmethod
    def _style_key(post: Dict[str, Any], field: str) -> str:
        value = post.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        # Rows logged before story formats existed were all the classic format.
        return DEFAULT_STORY_FORMAT if field == "story_format" else "unspecified"

    @classmethod
    def style_performance(
        cls,
        group_by: str = "style_preset",
        *,
        posts: Optional[List[Dict[str, Any]]] = None,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> List[Dict[str, Any]]:
        """Read-only: measured results grouped by one style dimension.

        Uses mature_metrics() only (snapshot at post age >= 48h, or a legacy
        row's latest metrics), so a 1-hour sync never counts.  Per group:
        ``count`` (measured posts), ``median_views``, ``avg_watch_time_sec``
        and ``completion_rate`` (means over posts that carry them; ``None``
        when no post in the group has that metric).  Missing style values
        group as ``"unspecified"`` (``story_format`` -> ``"classic"``).
        Sorted by median views, highest first.
        """
        if group_by not in STYLE_GROUP_FIELDS:
            raise ValueError(f"group_by ต้องเป็นหนึ่งใน {', '.join(STYLE_GROUP_FIELDS)} (ได้: {group_by!r})")
        rows = posts if posts is not None else cls._scoped_load(cls._scope(channel_id, all_channels))
        buckets: Dict[str, Dict[str, Any]] = {}
        for post in rows:
            metrics = mature_metrics(post)
            if not metrics:
                continue
            bucket = buckets.setdefault(
                cls._style_key(post, group_by), {"count": 0, "views": [], "watch": [], "completion": []}
            )
            bucket["count"] += 1
            views = metrics.get("views")
            if isinstance(views, (int, float)) and not isinstance(views, bool):
                bucket["views"].append(float(views))
            watch = parse_watch_time_sec(metrics.get("avg_watch_time_sec"))
            if watch is not None:
                bucket["watch"].append(watch)
            rate = parse_completion_rate(metrics.get("completion_rate"))
            if rate is not None:
                bucket["completion"].append(rate)
        results = []
        for key, bucket in buckets.items():
            median_views = _median(bucket["views"])
            watch = _mean(bucket["watch"])
            rate = _mean(bucket["completion"])
            results.append({
                group_by: key,
                "count": bucket["count"],
                "median_views": round(median_views, 1) if median_views is not None else None,
                "avg_watch_time_sec": round(watch, 2) if watch is not None else None,
                "completion_rate": round(rate, 4) if rate is not None else None,
            })
        return sorted(results, key=lambda r: (-(r["median_views"] or 0), str(r[group_by])))

    @classmethod
    def style_performance_report(
        cls, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> Dict[str, Any]:
        """All three groupings from ONE scoped read (for the stats endpoint)."""
        rows = cls._scoped_load(cls._scope(channel_id, all_channels))
        return {
            "measured": sum(1 for post in rows if mature_metrics(post)),
            **{f"by_{field}": cls.style_performance(field, posts=rows) for field in STYLE_GROUP_FIELDS},
        }

    @classmethod
    def summary(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> Dict[str, Any]:
        posts = cls._scoped_load(cls._scope(channel_id, all_channels))
        measured = [p for p in posts if p.get("metrics")]
        return {
            "total_posted": len(posts),
            "measured": len(measured),
            "pending_metrics": len(cls._pending_of(posts)),
            "total_views": sum(p["metrics"].get("views", 0) for p in measured),
            "total_orders": sum(p["metrics"].get("orders", 0) for p in measured),
            "total_commission_thb": round(
                sum(p["metrics"].get("commission_thb", 0.0) for p in measured), 2
            ),
        }

if __name__ == "__main__":
    print(json.dumps(PostLog.summary(), ensure_ascii=False, indent=2))

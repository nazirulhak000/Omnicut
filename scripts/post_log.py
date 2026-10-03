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
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR
from scripts.db import DocumentTable

LOG_PATH = BASE_DIR / "_Docs" / "post_log.json"
METRICS_DUE_HOURS = 48

METRIC_FIELDS = ("views", "likes", "comments", "shares", "cart_clicks", "orders", "commission_thb")

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
    """Append-only record of posted clips plus their measured results."""

    # ------------------------------------------------------------------
    # Storage
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
    ) -> Dict[str, Any]:
        """Record that a clip went live. Returns the stored row.

        The trailing keyword fields are optional and only written when given,
        so rows created by older callers keep their exact old shape.
        """
        now = datetime.datetime.now()

        # _mutate() holds one SQLite transaction across the read-modify-write
        # (P0 item 1 / plan step 2) -- two concurrent add_post() calls used to
        # both read the same posts list outside any lock and could silently
        # drop one row on save; the id used to collide too (see the uuid4
        # below -- was f"{timestamp}_{len(posts)+1}", which two posts added
        # in the same second at the same list length would share).
        with cls._mutate() as posts:
            post = {
                "id": uuid.uuid4().hex,
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
    ) -> Dict[str, Any]:
        """Idempotently log one posted export (called from mark-posted).

        Identity is export_id when both sides have it, else the clip file's
        basename -- the same key upsert_tiktok_stats' auto-register and
        attach_manual use, so a later stats sync merges into THIS row instead
        of creating a second one. An existing row is enriched (only empty
        fields are filled), never duplicated or overwritten.
        """
        wanted = {
            "product_name": product_name, "product_id": product_id, "angle_key": angle_key,
            "angle_title": angle_title or hook, "hook": hook, "style_preset": style_preset,
            "hook_color": hook_color, "caption": caption, "scheduled_at": scheduled_at,
            "export_id": export_id,
        }
        name = _clip_name(clip_file)
        with cls._mutate() as posts:
            for post in posts:
                if (export_id and post.get("export_id") == export_id) or (name and _clip_name(post.get("clip_file")) == name):
                    for key, value in wanted.items():
                        if value and not post.get(key):
                            post[key] = value
                    if hashtags and not post.get("hashtags"):
                        post["hashtags"] = list(hashtags)
                    return post
            post = {
                "id": uuid.uuid4().hex,
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
            return post

    @classmethod
    def update_metrics(cls, post_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fill in the 48-hour numbers for one post."""
        with cls._mutate() as posts:
            for post in posts:
                if post["id"] == post_id:
                    clean = {}
                    for field in METRIC_FIELDS:
                        raw = metrics.get(field)
                        if raw in (None, ""):
                            continue
                        try:
                            clean[field] = float(raw) if field == "commission_thb" else int(raw)
                        except (TypeError, ValueError):
                            raise ValueError(f"ค่า '{field}' ต้องเป็นตัวเลข (ได้: {raw!r})")

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
    ) -> Dict[str, Any]:
        """Merge scraped TikTok Studio rows into the post log.

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
        with cls._mutate() as posts:
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
                metrics = {k: row.get(k) for k in ("views", "likes", "comments", "shares") if isinstance(row.get(k), int)}
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
                        claimed_cand_keys.add(ckey)
                        posted_at = cls._parse_studio_posted_at(row.get("posted_text")) or now
                        # A post for this very clip may already exist (e.g.
                        # logged by mark-posted but the Studio title was too
                        # different to fuzzy-match). Link to it instead of
                        # registering a duplicate; same key as register_posted_export.
                        cand_name = _clip_name(cand.get("clip_file"))
                        existing = None
                        if cand_name:
                            for post in posts:
                                if _clip_name(post.get("clip_file")) != cand_name:
                                    continue
                                stored_vid = str(post.get("tiktok_video_id") or "")
                                if stored_vid and video_id and stored_vid != str(video_id):
                                    continue
                                if claimed.get(str(post.get("id"))) not in (None, claim):
                                    continue
                                existing = post
                                break
                        if existing is not None:
                            target = existing
                        else:
                            # Append here -- never call add_post() inside this
                            # mutate (nested _mutate on the same table would
                            # fight the open SQLite transaction).
                            new_post = {
                                "id": uuid.uuid4().hex,
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
    ) -> Dict[str, Any]:
        """Attach a hand-matched Studio row (from TikTokPending) to a post.

        Either post_id targets an existing post, or candidate (a library
        clip from _export_clip_candidates) attaches to the post already
        holding that clip_file/hook or registers a new post -- exactly the
        auto-register path but chosen by a human, so no score threshold
        applies.
        """
        if post_id is None and candidate is None:
            raise ValueError("ต้องระบุ post_id หรือ candidate อย่างใดอย่างหนึ่ง")
        now_dt = datetime.datetime.now()
        now = now_dt.isoformat(timespec="seconds")
        metrics = {k: row.get(k) for k in ("views", "likes", "comments", "shares") if isinstance(row.get(k), int)}
        video_id = (row.get("video_id") or "").strip() if isinstance(row.get("video_id"), str) else row.get("video_id")
        with cls._mutate() as posts:
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
                for post in posts:
                    if cand_clip and str(post.get("clip_file") or "") == cand_clip:
                        target = post
                        break
                    if cand_hook and str(post.get("hook") or "").lower() == cand_hook:
                        target = post
                        break
                if target is None:
                    target = {
                        "id": uuid.uuid4().hex,
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

        Duration filters only when BOTH sides have it (post_log posts never
        store duration), widened to ±5s for encode padding differences.
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
    def list_posts(cls, newest_first: bool = True) -> List[Dict[str, Any]]:
        posts = cls._load()
        return sorted(posts, key=lambda p: p.get("posted_at", ""), reverse=newest_first)

    @classmethod
    def get_all(cls, newest_first: bool = True) -> List[Dict[str, Any]]:
        return cls.list_posts(newest_first=newest_first)

    @classmethod
    def pending_metrics(cls) -> List[Dict[str, Any]]:
        """Posts past the 48-hour mark that have no 48-hour-old numbers yet.

        "Measured" means mature_metrics() finds a snapshot captured at post
        age >= 48h (or a legacy row with plain `metrics` and no history), so
        a sync done 1 hour after posting does not hide the post from here.
        """
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=METRICS_DUE_HOURS)
        due = []
        for post in cls._load():
            if mature_metrics(post):
                continue
            posted = _parse_dt(post.get("posted_at"))
            if posted is None:
                continue
            if posted <= cutoff:
                due.append(post)
        return due

    @classmethod
    def angle_performance(cls) -> List[Dict[str, Any]]:
        """
        Average results grouped by angle — the answer to "which angle sells".

        Only posts with filled-in metrics count, so this stays empty until the
        loop has actually run a few times.
        """
        buckets: Dict[str, Dict[str, Any]] = {}

        for post in cls._load():
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

    @classmethod
    def summary(cls) -> Dict[str, Any]:
        posts = cls._load()
        measured = [p for p in posts if p.get("metrics")]
        return {
            "total_posted": len(posts),
            "measured": len(measured),
            "pending_metrics": len(cls.pending_metrics()),
            "total_views": sum(p["metrics"].get("views", 0) for p in measured),
            "total_orders": sum(p["metrics"].get("orders", 0) for p in measured),
            "total_commission_thb": round(
                sum(p["metrics"].get("commission_thb", 0.0) for p in measured), 2
            ),
        }


if __name__ == "__main__":
    print(json.dumps(PostLog.summary(), ensure_ascii=False, indent=2))

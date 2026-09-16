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
    ) -> Dict[str, Any]:
        """Record that a clip went live. Returns the stored row."""
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

                    post["metrics"] = clean
                    post["metrics_filled_at"] = datetime.datetime.now().isoformat(timespec="seconds")
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
        now = datetime.datetime.now().isoformat(timespec="seconds")
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
                        # Append here -- never call add_post() inside this
                        # mutate (nested _mutate on the same table would fight
                        # the open SQLite transaction).
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
                    target["metrics"] = merged
                    target["metrics_filled_at"] = now
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
        now = datetime.datetime.now().isoformat(timespec="seconds")
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
                target["metrics"] = merged
                target["metrics_filled_at"] = now
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
        """Posts that are past the 48-hour mark and still have no numbers."""
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=METRICS_DUE_HOURS)
        due = []
        for post in cls._load():
            if post.get("metrics"):
                continue
            try:
                posted = datetime.datetime.fromisoformat(post["posted_at"])
            except (KeyError, ValueError):
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

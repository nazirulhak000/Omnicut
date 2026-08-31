"""
Post log — the feedback loop.

Every clip that actually goes live gets a row here, and 48 hours later the
numbers get filled in by hand. Without this the angle picker is guessing
forever; with it, the app can tell which angles and hooks earn clicks.

Storage is a plain JSON file so it stays readable and hand-editable.
"""

import json
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR

LOG_PATH = BASE_DIR / "_Docs" / "post_log.json"
METRICS_DUE_HOURS = 48

METRIC_FIELDS = ("views", "likes", "comments", "shares", "cart_clicks", "orders", "commission_thb")


class PostLog:
    """Append-only record of posted clips plus their measured results."""

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        if not LOG_PATH.exists():
            return []
        try:
            data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    @classmethod
    def _save(cls, posts: List[Dict[str, Any]]) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOG_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(LOG_PATH)

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
        posts = cls._load()
        now = datetime.datetime.now()

        post = {
            "id": f"{now.strftime('%Y%m%d%H%M%S')}_{len(posts) + 1}",
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
        cls._save(posts)
        return post

    @classmethod
    def update_metrics(cls, post_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fill in the 48-hour numbers for one post."""
        posts = cls._load()
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
                cls._save(posts)
                return post

        raise ValueError(f"ไม่พบโพสต์ id '{post_id}'")

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    @classmethod
    def list_posts(cls, newest_first: bool = True) -> List[Dict[str, Any]]:
        posts = cls._load()
        return sorted(posts, key=lambda p: p.get("posted_at", ""), reverse=newest_first)

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

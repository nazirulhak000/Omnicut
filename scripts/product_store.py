"""
Product queue — the front of the funnel.

Affiliate work is a stream of products, not one project. This keeps the ones
worth filming, what the AI worked out about each, and how far each has got.

Storage is a plain JSON file so it stays readable and hand-editable.
"""

import json
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR

STORE_PATH = BASE_DIR / "_Docs" / "products.json"

# candidate      → the URL is saved, nothing else done yet
# scripted       → angles picked and a script exists
# in_production  → currently editing in Studio
# rendered       → clip rendered & QC checked
# mobile_ready   → clip transferred to mobile phone
# posted         → clip is live on TikTok
STATUSES = ("candidate", "scripted", "in_production", "rendered", "mobile_ready", "posted")


class ProductStore:
    """The list of products in play, with what the AI worked out about each."""

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        if not STORE_PATH.exists():
            return []
        try:
            data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    @classmethod
    def _save(cls, products: List[Dict[str, Any]]) -> None:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STORE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STORE_PATH)

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------
    @classmethod
    def add(
        cls,
        name: str,
        url: str = "",
        platform: str = "",
        category: str = "",
        specs: Optional[List[Dict[str, str]]] = None,
        pain_points: Optional[List[str]] = None,
        selling_points: Optional[List[str]] = None,
        price_note: str = "",
        target_buyer: str = "",
        thumbnail: str = "",
        angles: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Add a product, or return the existing one when the URL is already queued."""
        if not name.strip():
            raise ValueError("ต้องมีชื่อสินค้า")

        products = cls._load()

        if url.strip():
            for existing in products:
                if existing.get("url", "").strip() == url.strip():
                    if angles:
                        existing["angles"] = angles
                        existing["status"] = "scripted"
                    if images:
                        existing["images"] = images
                    existing["updated_at"] = cls._now()
                    cls._save(products)
                    return existing

        now = cls._now()
        product = {
            "id": f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{len(products) + 1}",
            "name": name.strip(),
            "url": url.strip(),
            "platform": platform or cls.detect_platform(url),
            "category": category,
            "specs": specs or [],
            "pain_points": pain_points or [],
            "selling_points": selling_points or [],
            "price_note": price_note,
            "target_buyer": target_buyer,
            "thumbnail": thumbnail,
            "status": "scripted" if angles else "candidate",
            "angles": angles or [],
            "images": images or [],
            "videos": [],
            "projects": [],
            "created_at": now,
            "updated_at": now,
        }
        products.append(product)
        cls._save(products)
        return product

    @classmethod
    def update(cls, product_id: str, **fields: Any) -> Dict[str, Any]:
        """Patch a product. Unknown keys are stored as-is so the UI can grow."""
        products = cls._load()
        for product in products:
            if product["id"] == product_id:
                fields.pop("id", None)
                fields.pop("created_at", None)

                status = fields.get("status")
                if status and status not in STATUSES:
                    raise ValueError(f"status '{status}' ไม่ถูกต้อง — ต้องเป็นหนึ่งใน {', '.join(STATUSES)}")

                product.update(fields)
                product["updated_at"] = cls._now()
                cls._save(products)
                return product

    @classmethod
    def update_angle_status(cls, product_id: str, angle_id: str, status: str, video_url: Optional[str] = None) -> Dict[str, Any]:
        """Updates the lifecycle status of a specific script angle in a product."""
        products = cls._load()
        for product in products:
            if product["id"] == product_id:
                angles = product.get("angles", [])
                for angle in angles:
                    if angle.get("angle_id") == angle_id:
                        angle["status"] = status
                        if video_url:
                            angle["video_url"] = video_url
                        angle["updated_at"] = cls._now()
                        product["updated_at"] = cls._now()
                        cls._save(products)
                        return product
        raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def update_angle_videos(cls, product_id: str, angle_id: str, selected_videos: List[str]) -> Dict[str, Any]:
        """Persists selected raw footage attachments for a specific script angle in a product."""
        products = cls._load()
        for product in products:
            if product["id"] == product_id:
                angles = product.get("angles", [])
                for angle in angles:
                    if angle.get("angle_id") == angle_id:
                        angle["selected_videos"] = selected_videos
                        angle["selected_video"] = selected_videos[0] if selected_videos else None
                        angle["updated_at"] = cls._now()
                        product["updated_at"] = cls._now()
                        cls._save(products)
                        return product
        raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def add_video_to_product(cls, product_id: str, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Attaches a raw footage item specifically to a product."""
        products = cls._load()
        for product in products:
            if product["id"] == product_id:
                v_list = product.setdefault("videos", [])
                # Avoid duplicates
                v_path = video_info.get("path") or video_info.get("rel_path")
                if not any(v.get("path") == v_path or v.get("rel_path") == v_path for v in v_list):
                    v_list.append(video_info)
                product["updated_at"] = cls._now()
                cls._save(products)
                return product
        raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def remove_video_from_product(cls, product_id: str, video_path: str) -> Dict[str, Any]:
        """Removes a footage link from a product."""
        products = cls._load()
        for product in products:
            if product["id"] == product_id:
                v_list = product.get("videos", [])
                product["videos"] = [
                    v for v in v_list
                    if v.get("path") != video_path and v.get("rel_path") != video_path
                ]
                product["updated_at"] = cls._now()
                cls._save(products)
                return product
        raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def get_product_videos(cls, product_id: str) -> List[Dict[str, Any]]:
        """Retrieves all footage assigned to a product."""
        product = cls.get(product_id)
        if not product:
            return []
        return product.get("videos", [])

    @classmethod
    def attach_project(cls, product_id: str, project_name: str) -> Dict[str, Any]:
        """Link a rendered project back to the product it came from."""
        product = cls.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

        projects = product.get("projects", [])
        if project_name not in projects:
            projects.append(project_name)

        return cls.update(product_id, projects=projects, status="rendered")

    @classmethod
    def remove_angle(cls, product_id: str, angle_id: str) -> Dict[str, Any]:
        """
        Drop one angle (its hook, script and caption) from a product.

        Returns what happened, including whether the product itself was removed
        because that was its last angle -- a product with no angles left is an
        empty card in the tracker, not something to keep.
        """
        product = cls.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

        angles = product.get("angles") or []
        remaining = [a for a in angles if a.get("angle_id") != angle_id]
        if len(remaining) == len(angles):
            raise ValueError(f"ไม่พบมุม '{angle_id}' ในสินค้านี้")

        if not remaining:
            cls.delete(product_id)
            return {"angle_removed": angle_id, "product_removed": product_id, "angles_left": 0}

        cls.update(product_id, angles=remaining)
        return {"angle_removed": angle_id, "product_removed": None, "angles_left": len(remaining)}

    @classmethod
    def find_by_project(cls, project_name: str, product_name: str = "", hook_title: str = ""):
        """
        Which product/angle a rendered project came from.

        Prefers the explicit link (products carry the project names rendered
        from them). Falls back to matching the product name and hook for
        projects rendered before that link was recorded -- those are the only
        two things a manifest kept about its origin.
        """
        products = cls._load()
        for product in products:
            if project_name in (product.get("projects") or []):
                angle = cls._match_angle(product, hook_title)
                return product, angle

        if not product_name:
            return None, None
        for product in products:
            names = {(product.get("name") or ""), (product.get("title") or "")}
            names |= {(a.get("product_name") or "") for a in (product.get("angles") or [])}
            if product_name in names:
                return product, cls._match_angle(product, hook_title)
        return None, None

    @staticmethod
    def _match_angle(product: Dict[str, Any], hook_title: str):
        for angle in product.get("angles") or []:
            if hook_title and angle.get("hook_title") == hook_title:
                return angle
        return None

    @classmethod
    def delete(cls, product_id: str) -> None:
        products = cls._load()
        remaining = [p for p in products if p["id"] != product_id]
        if len(remaining) == len(products):
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")
        cls._save(remaining)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        return cls._load()

    @classmethod
    def list(cls, status: Optional[str] = None) -> List[Dict[str, Any]]:
        products = cls._load()
        if status:
            products = [p for p in products if p.get("status") == status]
        return sorted(products, key=lambda p: p.get("updated_at", ""), reverse=True)

    @classmethod
    def get(cls, product_id: str) -> Optional[Dict[str, Any]]:
        for product in cls._load():
            if product["id"] == product_id:
                return product
        return None

    @classmethod
    def summary(cls) -> Dict[str, int]:
        products = cls._load()
        counts = {status: 0 for status in STATUSES}
        for product in products:
            status = product.get("status")
            if status in counts:
                counts[status] += 1
        counts["total"] = len(products)
        return counts

    # ------------------------------------------------------------------
    @staticmethod
    def detect_platform(url: str) -> str:
        lowered = (url or "").lower()
        if "shopee" in lowered:
            return "shopee"
        if "tiktok" in lowered:
            return "tiktok"
        if "lazada" in lowered:
            return "lazada"
        return ""

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(ProductStore.summary(), ensure_ascii=False, indent=2))

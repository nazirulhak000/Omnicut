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


import threading

class ProductStore:
    """The list of products in play, with what the AI worked out about each."""

    _lock: threading.Lock = threading.Lock()

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
        with cls._lock:
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
        raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

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
    def update_angle_status(
        cls,
        product_id: str,
        angle_id: str,
        status: str,
        video_url: Optional[str] = None,
        project_name: Optional[str] = None,
        qc_note: Optional[str] = None,
        clear_qc_note: bool = False,
    ) -> Dict[str, Any]:
        """Updates the lifecycle status of a specific script angle in a product.

        qc_note  – optional free-text reason for a QC failure; stored on the
                   angle so Studio can surface it the next time the angle is
                   opened for re-editing.
        clear_qc_note – pass True to wipe any previous qc_note (e.g. when the
                         angle passes QC and advances beyond 'rendered').
        """
        products = cls._load()
        for product in products:
            if product["id"] == product_id:
                angles = product.get("angles", [])
                for angle in angles:
                    current_aid = angle.get("angle_id") or angle.get("id")
                    if current_aid == angle_id:
                        angle["status"] = status
                        if video_url is not None:
                            angle["video_url"] = video_url if video_url else None
                        if project_name is not None:
                            angle["project_name"] = project_name if project_name else None
                        # QC note handling
                        if qc_note is not None:
                            angle["qc_note"] = qc_note.strip() or None
                        elif clear_qc_note:
                            angle["qc_note"] = None
                        angle["updated_at"] = cls._now()
                        product["updated_at"] = cls._now()
                        cls._save(products)
                        return product
        raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def rollback_by_video_or_project(cls, identifier: str) -> List[str]:
        """
        Finds any angle matching the given video filename or project_name,
        and rolls its status back.
        If only the video MP4 was removed but the timeline project still exists on disk,
        the angle transitions to 'in_production' (keeping project_name).
        If the project itself was deleted or does not exist, it rolls back to 'scripted'.
        """
        if not identifier:
            return []
        products = cls._load()
        target_token = Path(identifier).stem.lower().strip()
        raw_id_low = identifier.lower().strip()
        projects_dir = BASE_DIR / "03_Projects"
        rolled_back = []
        changed = False

        for product in products:
            for angle in product.get("angles", []):
                v_url = (angle.get("video_url") or "").lower()
                p_name = (angle.get("project_name") or "").lower()
                v_name = Path(v_url).name.lower() if v_url else ""
                v_stem = Path(v_url).stem.lower() if v_url else ""

                is_match = (
                    (p_name and (p_name == raw_id_low or p_name == target_token)) or
                    (v_name and (v_name == raw_id_low or v_name == Path(identifier).name.lower())) or
                    (v_stem and v_stem == target_token)
                )
                if is_match and angle.get("status") in ("rendered", "in_production"):
                    cur_p_name = angle.get("project_name")
                    has_proj = False
                    if cur_p_name:
                        # If the identifier being deleted IS the project itself, project will not exist
                        if cur_p_name.lower() != raw_id_low and cur_p_name.lower() != target_token:
                            proj_dir = projects_dir / cur_p_name
                            if proj_dir.exists() and proj_dir.is_dir():
                                has_proj = True

                    if has_proj:
                        angle["status"] = "in_production"
                        angle["video_url"] = None
                    else:
                        angle["status"] = "scripted"
                        angle["video_url"] = None
                        angle["project_name"] = None

                    angle["updated_at"] = cls._now()
                    product["updated_at"] = cls._now()
                    rolled_back.append(angle.get("angle_id", ""))
                    changed = True

        if changed:
            cls._save(products)
        return rolled_back

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
    def set_default_videos_for_all_angles(cls, product_id: str, selected_videos: List[str]) -> Dict[str, Any]:
        """Sets default raw footage attachments for all script angles belonging to this product."""
        products = cls._load()
        for product in products:
            if product["id"] == product_id:
                for angle in product.get("angles", []):
                    # Do not overwrite angles that are actively in_production in timeline
                    if angle.get("status") == "in_production" or (angle.get("project_name") and angle.get("status") not in ("rendered", "posted")):
                        continue
                    angle["selected_videos"] = selected_videos
                    angle["selected_video"] = selected_videos[0] if selected_videos else None
                    angle["updated_at"] = cls._now()
                # Also ensure each video is in product['videos']
                v_list = product.setdefault("videos", [])
                for v_path in selected_videos:
                    if not any(v.get("path") == v_path or v.get("rel_path") == v_path for v in v_list):
                        v_list.append({"rel_path": v_path, "path": v_path})
                product["updated_at"] = cls._now()
                cls._save(products)
                return product
        raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

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
    def find_by_project(cls, project_name: str, product_name: str = "", hook_title: str = "", product_id: str = "", angle_id: str = ""):
        """
        Which product/angle a rendered project came from.

        Prefers exact product_id/angle_id or direct angle.project_name matching.
        Falls back to product.projects list and product name/hook matching.
        """
        products = cls._load()
        # 1. Exact product_id and angle_id if provided
        if product_id:
            for product in products:
                if product.get("id") == product_id:
                    if angle_id:
                        for angle in product.get("angles") or []:
                            if (angle.get("angle_id") or angle.get("id")) == angle_id:
                                return product, angle
                    return product, None

        # 2. Direct match on angle.project_name
        for product in products:
            for angle in product.get("angles") or []:
                if angle.get("project_name") == project_name:
                    return product, angle

        # 3. Match in product.projects list
        for product in products:
            if project_name in (product.get("projects") or []):
                for angle in product.get("angles") or []:
                    if angle.get("project_name") == project_name:
                        return product, angle
                angle = cls._match_angle(product, hook_title)
                return product, angle

        # 4. Fallback to product name and hook title
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
    # Reading & Automatic Reconciliation
    # ------------------------------------------------------------------
    @classmethod
    def reconcile_existing_projects(cls) -> bool:
        """
        Scans 03_Projects and 04_Exports to match existing rendered projects
        with their corresponding angles in products.json.
        """
        import re
        products = cls._load()
        if not products:
            return False

        changed = False
        projects_dir = BASE_DIR / "03_Projects"
        exports_dir = BASE_DIR / "04_Exports" / "Ready_to_post"
        
        if not projects_dir.exists():
            return False

        for p_folder in projects_dir.iterdir():
            if not p_folder.is_dir():
                continue
            manifest_file = p_folder / "project.json"
            if not manifest_file.exists():
                continue

            try:
                p_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            p_hook = p_data.get("script_data", {}).get("hook", "") or ""
            p_lines = [line.get("text", "") for line in p_data.get("script_data", {}).get("lines", [])]
            p_clean_hook = re.sub(r"[\s\.\…\u2026]+", "", p_hook)
            p_clean_lines = [re.sub(r"[\s\.\…\u2026]+", "", l) for l in p_lines if l]

            p_rp = p_data.get("render_params", {}) or {}
            p_pid = p_rp.get("product_id") or p_data.get("product_id")
            p_aid = p_rp.get("angle_id") or p_data.get("angle_id")

            # Check if an exported MP4 exists
            mp4_path = None
            art_mp4 = p_data.get("artifacts", {}).get("mp4_video", {}).get("path")
            if art_mp4 and Path(art_mp4).exists():
                mp4_path = art_mp4
            elif exports_dir.exists():
                candidates = list(exports_dir.glob(f"{p_folder.name}*.mp4"))
                if candidates:
                    mp4_path = str(candidates[0])

            # Match against products
            for product in products:
                # If project explicitly specified a product_id, it MUST match product["id"]
                if p_pid and product.get("id") and p_pid != product.get("id"):
                    continue

                for angle in product.get("angles", []):
                    current_aid = angle.get("angle_id") or angle.get("id")
                    
                    is_match = False

                    # 1. Exact Product ID + Angle ID match from project manifest
                    if p_pid and p_aid and product.get("id") == p_pid and current_aid == p_aid:
                        is_match = True
                    # 2. Already explicitly linked by project_name on this angle
                    elif angle.get("project_name") and angle.get("project_name") == p_folder.name:
                        is_match = True

                    if is_match:
                        # Ensure project is linked
                        if angle.get("project_name") != p_folder.name:
                            angle["project_name"] = p_folder.name
                            changed = True

                        if mp4_path:
                            # If angle has a QC failure note or is explicitly set to in_production,
                            # do NOT automatically overwrite it to 'rendered'!
                            if angle.get("qc_note"):
                                if angle.get("status") != "in_production":
                                    angle["status"] = "in_production"
                                    changed = True
                                if angle.get("video_url") != mp4_path:
                                    angle["video_url"] = mp4_path
                                    changed = True
                            elif angle.get("status") in ("mobile_ready", "posted"):
                                # Preserve advanced lifecycle status
                                if angle.get("video_url") != mp4_path:
                                    angle["video_url"] = mp4_path
                                    changed = True
                            elif angle.get("status") == "in_production":
                                # User is currently editing in Studio or sent for re-edit
                                if angle.get("video_url") != mp4_path:
                                    angle["video_url"] = mp4_path
                                    changed = True
                            else:
                                if angle.get("status") != "rendered" or angle.get("video_url") != mp4_path:
                                    angle["status"] = "rendered"
                                    angle["video_url"] = mp4_path
                                    changed = True
                        else:
                            # Project timeline exists in 03_Projects, but NO exported MP4 video yet!
                            # It MUST be 'in_production', NOT 'rendered'!
                            if angle.get("status") != "in_production" or angle.get("video_url") is not None:
                                angle["status"] = "in_production"
                                angle["video_url"] = None
                                changed = True

                        p_list = product.setdefault("projects", [])
                        if p_folder.name not in p_list:
                            p_list.append(p_folder.name)
                            changed = True

        # Strict state validation: Clean up any angle whose project or video does not actually exist on disk
        for product in products:
            for angle in product.get("angles", []):
                p_name = angle.get("project_name")
                has_proj = False
                if p_name:
                    p_path = projects_dir / p_name
                    if p_path.exists() and p_path.is_dir():
                        has_proj = True
                
                has_video = False
                v_url = angle.get("video_url")
                if v_url:
                    if Path(v_url).exists():
                        has_video = True
                    else:
                        ready_file = exports_dir / Path(v_url).name
                        if ready_file.exists():
                            has_video = True

                if angle.get("status") == "rendered" and not has_video:
                    if has_proj:
                        angle["status"] = "in_production"
                    else:
                        angle["status"] = "scripted"
                        angle["project_name"] = None
                    angle["video_url"] = None
                    changed = True
                elif angle.get("status") == "in_production" and not has_proj:
                    # No project folder on disk! Revert strictly to scripted
                    angle["status"] = "scripted"
                    angle["project_name"] = None
                    angle["video_url"] = None
                    changed = True

        if changed:
            cls._save(products)
        return changed

    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        cls.reconcile_existing_projects()
        return cls._load()

    @classmethod
    def list(cls, status: Optional[str] = None) -> List[Dict[str, Any]]:
        cls.reconcile_existing_projects()
        products = cls._load()
        if status:
            products = [p for p in products if p.get("status") == status]
        return sorted(products, key=lambda p: p.get("updated_at", ""), reverse=True)

    @classmethod
    def get(cls, product_id: str) -> Optional[Dict[str, Any]]:
        cls.reconcile_existing_projects()
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

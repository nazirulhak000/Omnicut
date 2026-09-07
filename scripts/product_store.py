"""
Product queue — the front of the funnel.

Affiliate work is a stream of products, not one project. This keeps the ones
worth filming, what the AI worked out about each, and how far each has got.

Storage is SQLite (see scripts/db.py) behind the exact same _load()/_save()
contract this module always had, mirrored out to a plain JSON file so it
stays readable, hand-editable, and diffable as a backup. The mirror file
lives at STORE_PATH, same path as before.
"""

import json
import re
import uuid
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR
from scripts.db import DocumentTable

STORE_PATH = BASE_DIR / "_Docs" / "products.json"

# candidate      → the URL is saved, nothing else done yet
# scripted       → angles picked and a script exists
# in_production  → currently editing in Studio
# rendered       → clip rendered & QC checked
# mobile_ready   → clip transferred to mobile phone
# posted         → clip is live on TikTok
STATUSES = ("candidate", "scripted", "in_production", "rendered", "mobile_ready", "posted")


import threading


def _store_db_path() -> Path:
    # STORE_PATH.parent is BASE_DIR/_Docs -- both products and posts share one
    # sqlite file there, but live in their own tables.
    return STORE_PATH.parent / "store.db"


def _store_json_path() -> Path:
    # Read STORE_PATH dynamically (not captured at import time) so tests that
    # monkeypatch scripts.product_store.STORE_PATH keep working.
    return STORE_PATH


_TABLE = DocumentTable("products", _store_db_path, _store_json_path)


class ProductStore:
    """The list of products in play, with what the AI worked out about each."""

    # Kept only so any external code that still references ProductStore._lock
    # (none found in this repo, but this was public-by-convention before)
    # does not hit an AttributeError. No longer load-bearing for correctness
    # -- the real mutual exclusion is the SQLite transaction in _mutate().
    _lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def _save(cls, products: List[Dict[str, Any]]) -> None:
        _TABLE.save(products)

    @classmethod
    def _mutate(cls):
        """Context manager: read-modify-write the full product list as one
        SQLite transaction (fixes the lost-update race -- see class docs on
        the individual write methods below, and _Docs/SAAS_READINESS_PLAN.md
        P0 item 1). Every write method that used to do

            products = cls._load()
            ...mutate...
            cls._save(products)

        with the load OUTSIDE any lock now does

            with cls._mutate() as products:
                ...mutate...

        instead -- the save happens automatically (and only) on a clean
        exit, still inside the same transaction the load happened in, so
        two concurrent writers can no longer both read stale data and have
        one silently clobber the other's write.
        """
        return _TABLE.mutate()

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
        tiktok_product_id: Optional[str] = None,
        product_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a product, or return the existing one when the URL is already queued."""
        if not name.strip():
            raise ValueError("ต้องมีชื่อสินค้า")

        # The load-modify-save below used to run with the load OUTSIDE any
        # lock (P0 item 1 in SAAS_READINESS_PLAN.md): two concurrent adds for
        # the same new URL could both read "not found" and both append a
        # product, or a concurrent add-for-existing-URL update could vanish
        # under a concurrent unrelated add. _mutate() holds one SQLite
        # transaction across the whole read-modify-write.
        with cls._mutate() as products:
            if url.strip():
                for existing in products:
                    if existing.get("url", "").strip() == url.strip():
                        if angles:
                            existing["angles"] = angles
                            existing["status"] = "scripted"
                        if images:
                            existing["images"] = images
                        if tiktok_product_id and tiktok_product_id.strip():
                            existing["tiktok_product_id"] = tiktok_product_id.strip()
                        if not existing.get("product_code"):
                            existing["product_code"] = (
                                product_code.strip().upper()
                                if (product_code and product_code.strip())
                                else cls._generate_product_code(existing.get("name", ""), products)
                            )
                        existing["updated_at"] = cls._now()
                        return existing

            now = cls._now()
            product = {
                "id": uuid.uuid4().hex,
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
                "tiktok_product_id": tiktok_product_id.strip() if (tiktok_product_id and tiktok_product_id.strip()) else None,
                "product_code": (product_code.strip().upper() if (product_code and product_code.strip()) else cls._generate_product_code(name, products)),
                "status": "scripted" if angles else "candidate",
                "angles": angles or [],
                "images": images or [],
                "videos": [],
                "projects": [],
                "created_at": now,
                "updated_at": now,
            }
            products.append(product)
            return product

    @classmethod
    def update(cls, product_id: str, **fields: Any) -> Dict[str, Any]:
        """Patch a product. Unknown keys are stored as-is so the UI can grow."""
        with cls._mutate() as products:
            for product in products:
                if product["id"] == product_id:
                    fields.pop("id", None)
                    fields.pop("created_at", None)

                    status = fields.get("status")
                    if status and status not in STATUSES:
                        raise ValueError(f"status '{status}' ไม่ถูกต้อง — ต้องเป็นหนึ่งใน {', '.join(STATUSES)}")

                    # Uppercase product_code the same way add() does, so a
                    # code's casing does not drift depending on whether it was
                    # set at creation or edited later via PATCH.
                    if "product_code" in fields and fields["product_code"]:
                        fields["product_code"] = fields["product_code"].strip().upper()

                    product.update(fields)
                    product["updated_at"] = cls._now()
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
        clear_conflict_note: bool = False,
    ) -> Dict[str, Any]:
        """Updates the lifecycle status of a specific script angle in a product.

        qc_note  – optional free-text reason for a QC failure; stored on the
                   angle so Studio can surface it the next time the angle is
                   opened for re-editing.
        clear_qc_note – pass True to wipe any previous qc_note (e.g. when the
                         angle passes QC and advances beyond 'rendered').
        clear_conflict_note – pass True to dismiss the `data_conflict_note`
                               reconcile_existing_projects() sets when it
                               auto-unlinks this angle from another angle's
                               project/video (Round BUG-3).
        """
        with cls._mutate() as products:
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
                            if clear_conflict_note:
                                angle["data_conflict_note"] = None
                            if status == "posted" and not angle.get("posted_at"):
                                angle["posted_at"] = cls._now()
                            angle["updated_at"] = cls._now()
                            product["updated_at"] = cls._now()
                            return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def rollback_by_video_or_project(
        cls,
        identifier: str,
        product_id: str = "",
        angle_id: str = "",
    ) -> List[str]:
        """
        Finds the angle matching the given video filename or project_name,
        and rolls its status back.
        If only the video MP4 was removed but the timeline project still exists on disk,
        the angle transitions to 'in_production' (keeping project_name).
        If the project itself was deleted or does not exist, it rolls back to 'scripted'.

        `product_id`/`angle_id` scope the match to the specific angle the
        caller is actually rolling back. When given, only that exact angle is
        ever touched -- filename stems are not unique across products/angles
        (two angles can render to files that stem-match), so matching by
        filename alone risks rolling back an unrelated angle that happens to
        share the same stem. When omitted (legacy callers that only know the
        filename), at most ONE angle is still touched: the first match, and a
        warning is logged if more than one candidate exists, since silently
        mutating every stem-alike angle is exactly the bug this guards against.
        """
        if not identifier:
            return []
        target_token = Path(identifier).stem.lower().strip()
        raw_id_low = identifier.lower().strip()
        projects_dir = BASE_DIR / "03_Projects"
        rolled_back = []

        def _roll(product, angle):
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

        with cls._mutate() as products:
            # Scoped path: caller knows exactly which angle it means. No stem
            # matching at all -- the identifier is only used to decide
            # in_production vs scripted above, not to locate the angle.
            if product_id and angle_id:
                for product in products:
                    if product.get("id") != product_id:
                        continue
                    for angle in product.get("angles", []):
                        current_aid = angle.get("angle_id") or angle.get("id")
                        if current_aid == angle_id:
                            _roll(product, angle)
                            return rolled_back
                return rolled_back

            # Legacy path: only the filename/project_name is known. Stop after
            # the first match -- and warn if more exist -- rather than silently
            # cascading the rollback onto every angle that happens to share the
            # same filename stem.
            matches = []
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
                    if is_match:
                        matches.append((product, angle))

            if not matches:
                return rolled_back

            if len(matches) > 1:
                print(
                    f"[ProductStore.rollback_by_video_or_project] WARNING: '{identifier}' matched "
                    f"{len(matches)} angles by filename/project stem alone -- rolling back only the "
                    "first (product_id="
                    f"{matches[0][0].get('id')!r}, angle_id={(matches[0][1].get('angle_id') or matches[0][1].get('id'))!r}). "
                    "Pass product_id/angle_id explicitly to avoid this ambiguity."
                )

            # Round BUG-3: used to skip mobile_ready/posted angles entirely --
            # deleting the file behind an already-posted clip left its card
            # showing as if the video still existed. A user-triggered delete
            # (unlike reconcile's passive best-effort scan) should always
            # cascade, regardless of how far the angle's status advanced.
            product, angle = matches[0]
            _roll(product, angle)
            return rolled_back

    @classmethod
    def update_angle_videos(cls, product_id: str, angle_id: str, selected_videos: List[str]) -> Dict[str, Any]:
        """Persists selected raw footage attachments for a specific script angle in a product."""
        with cls._mutate() as products:
            for product in products:
                if product["id"] == product_id:
                    angles = product.get("angles", [])
                    for angle in angles:
                        if angle.get("angle_id") == angle_id:
                            angle["selected_videos"] = selected_videos
                            angle["selected_video"] = selected_videos[0] if selected_videos else None
                            angle["updated_at"] = cls._now()
                            product["updated_at"] = cls._now()
                            return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def set_default_videos_for_all_angles(cls, product_id: str, selected_videos: List[str]) -> Dict[str, Any]:
        """Sets default raw footage attachments for all script angles belonging to this product."""
        with cls._mutate() as products:
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
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def add_video_to_product(cls, product_id: str, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Attaches a raw footage item specifically to a product."""
        with cls._mutate() as products:
            for product in products:
                if product["id"] == product_id:
                    v_list = product.setdefault("videos", [])
                    # Avoid duplicates
                    v_path = video_info.get("path") or video_info.get("rel_path")
                    if not any(v.get("path") == v_path or v.get("rel_path") == v_path for v in v_list):
                        v_list.append(video_info)
                    product["updated_at"] = cls._now()
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def remove_video_from_product(cls, product_id: str, video_path: str) -> Dict[str, Any]:
        """Removes a footage link from a product."""
        with cls._mutate() as products:
            for product in products:
                if product["id"] == product_id:
                    v_list = product.get("videos", [])
                    product["videos"] = [
                        v for v in v_list
                        if v.get("path") != video_path and v.get("rel_path") != video_path
                    ]
                    product["updated_at"] = cls._now()
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
    def find_by_project(cls, project_name: str, product_id: str = "", angle_id: str = ""):
        """
        Which product/angle a rendered project came from.

        Prefers exact product_id/angle_id (the stable ids the render pipeline
        stamps into project.json's render_params -- see video_assembly_stage.py)
        or direct angle.project_name matching. Both are keyed off stable ids,
        never off display name/hook text: this feeds project/product deletion
        (DELETE /api/projects/{name}?scope=product), and matching by name text
        risks cascade-deleting the WRONG product when two share a display name.

        If none of that resolves anything, this refuses to guess rather than
        falling back to a name-string match -- old projects rendered before
        product_id/angle_id were recorded simply cannot be traced this way,
        and it's safer to say "not found" than to silently match on a
        collision-prone name.
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

        # 3. Match in product.projects list (still id-based: project_name is
        # the same stable folder-name key recorded in product.projects, not
        # a display-name heuristic)
        for product in products:
            if project_name in (product.get("projects") or []):
                for angle in product.get("angles") or []:
                    if angle.get("project_name") == project_name:
                        return product, angle
                return product, None

        print(
            f"[ProductStore.find_by_project] WARNING: no stable-id match for project "
            f"'{project_name}' (product_id={product_id!r}, angle_id={angle_id!r}) -- "
            "refusing to fall back to a name-based guess."
        )
        return None, None

    @classmethod
    def delete(cls, product_id: str) -> None:
        with cls._mutate() as products:
            remaining = [p for p in products if p["id"] != product_id]
            if len(remaining) == len(products):
                raise ValueError(f"ไม่พบสินค้า id '{product_id}'")
            products[:] = remaining

    # ------------------------------------------------------------------
    # Reading & Automatic Reconciliation
    # ------------------------------------------------------------------
    @classmethod
    def reconcile_existing_projects(cls) -> bool:
        """
        Scans 03_Projects and 04_Exports to match existing rendered projects
        with their corresponding angles in products.json.
        """
        products = cls._load()
        if not products:
            return False

        changed = False
        projects_dir = BASE_DIR / "03_Projects"
        exports_dir = BASE_DIR / "04_Exports" / "Ready_to_post"
        # A posted clip's mp4 lives here now (Round POST-1.4) -- if this scan
        # only checked Ready_to_post, a posted clip would look exactly like
        # "no export exists yet" the moment it was moved out.
        posted_dir = BASE_DIR / "04_Exports" / "Posted"

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

            p_rp = p_data.get("render_params", {}) or {}
            p_pid = p_rp.get("product_id") or p_data.get("product_id")
            p_aid = p_rp.get("angle_id") or p_data.get("angle_id")

            # Check if an exported MP4 exists
            mp4_path = None
            art_mp4 = p_data.get("artifacts", {}).get("mp4_video", {}).get("path")
            if art_mp4 and Path(art_mp4).exists():
                mp4_path = art_mp4
            else:
                for scan_dir in (exports_dir, posted_dir):
                    if not scan_dir.exists():
                        continue
                    candidates = list(scan_dir.glob(f"{p_folder.name}*.mp4"))
                    if candidates:
                        mp4_path = str(candidates[0])
                        break

            # Match against products.
            #
            # Round BUG-3: this used to apply the update below to EVERY
            # angle that matched, with no cap -- if two angles both claimed
            # this same p_folder (one legitimately via its own manifest,
            # one only because its own project_name field already said so),
            # both got the same video_url/status, forever, since condition
            # #2 just re-confirms whatever project_name an angle already
            # has without ever verifying it's actually this angle's own
            # render. Now: condition #1 (this folder's OWN manifest names
            # this exact product+angle) is ground truth and always wins.
            # Condition #2 (self-referential -- "an angle already claims
            # this folder") is only a fallback, and at most ONE angle may
            # win it per folder per pass; every other angle claiming the
            # same folder is a data conflict and gets unlinked back to
            # scripted instead of silently mirroring the winner's clip.
            authoritative_match = None  # (product, angle) via condition #1
            self_ref_matches = []       # [(product, angle), ...] via condition #2

            for product in products:
                # If project explicitly specified a product_id, it MUST match product["id"]
                if p_pid and product.get("id") and p_pid != product.get("id"):
                    continue

                for angle in product.get("angles", []):
                    current_aid = angle.get("angle_id") or angle.get("id")

                    # 1. Exact Product ID + Angle ID match from project manifest
                    if p_pid and p_aid and product.get("id") == p_pid and current_aid == p_aid:
                        if authoritative_match is None:
                            authoritative_match = (product, angle)
                    # 2. Already explicitly linked by project_name on this angle
                    elif angle.get("project_name") and angle.get("project_name") == p_folder.name:
                        self_ref_matches.append((product, angle))

            winner = authoritative_match or (self_ref_matches[0] if self_ref_matches else None)
            losers = self_ref_matches if authoritative_match else self_ref_matches[1:]

            for _loser_product, loser_angle in losers:
                loser_angle["project_name"] = None
                loser_angle["video_url"] = None
                loser_angle["status"] = "scripted"
                loser_angle["data_conflict_note"] = (
                    f"ปลดออกจาก '{p_folder.name}' อัตโนมัติ — ชนกับ angle อื่นที่ผูกกับคลิปนี้ถูกต้องกว่า ({cls._now()})"
                )
                loser_angle["updated_at"] = cls._now()
                changed = True

            if winner:
                product, angle = winner

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
                elif angle.get("status") in ("mobile_ready", "posted"):
                    # No mp4 found by either path -- this scan's own
                    # heuristic came up empty, which used to be read
                    # as "no export was ever made" and wiped the
                    # angle back to in_production. That is exactly
                    # what happened to a posted clip the instant its
                    # file moved to Posted/ and its manifest's
                    # artifacts.mp4_video.path (still pointing at the
                    # old Ready_to_post location) stopped resolving.
                    # An already-posted clip does not get less posted
                    # because this pass could not find its file.
                    pass
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
    @classmethod
    def _generate_product_code(cls, name: str, products: Optional[List[Dict[str, Any]]] = None) -> str:
        """Short scannable code for a product, e.g. 'ESS01' for 'ESSAGER สายชาร์จ...'.

        Prefix is a naive first-3-letters of the name's first Latin word (falls
        back to 'GEN' for pure-Thai names with no Latin brand token) — this is
        meant to be corrected by hand once via the edit UI, not to be a perfect
        brand abbreviation.
        """
        match = re.search(r"[A-Za-z]+", name or "")
        prefix = (match.group(0)[:3] if match else "GEN").upper()
        if len(prefix) < 3:
            prefix = (prefix + "XXX")[:3]

        existing = products if products is not None else cls._load()
        max_n = 0
        for product in existing:
            code = (product.get("product_code") or "").upper()
            m = re.match(rf"^{re.escape(prefix)}(\d+)$", code)
            if m:
                max_n = max(max_n, int(m.group(1)))
        next_n = max_n + 1
        suffix = f"{next_n:02d}" if next_n < 100 else str(next_n)
        return f"{prefix}{suffix}"

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

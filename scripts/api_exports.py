"""
API Router for Exported Videos and Versioning.
"""

import os
import re
import json
import filecmp
import shutil
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from scripts.channel_ownership import resolve_store_scope
from scripts.channel_scope import ChannelScope, get_channel_scope, require_writable
from scripts.channel_store import ChannelError
from scripts.config import BASE_DIR, EXPORTS_DIR, COVERS_DIR
from scripts.product_store import ProductStore
from scripts.media_service import get_file_info
from scripts.api_schemas import LinkAngleRequest
from scripts.video_editor import VideoEditor
from scripts.export_registry import ExportRegistry


# ---------------------------------------------------------------------------
# Channel scope (multi-channel P2.2, ADR §7.1 + §12/§13)
# ---------------------------------------------------------------------------
# Export identity is the registry row (``export_id``) and its ``channel_id``;
# the flat 04_Exports folders are shared until P6 (nested channel folders and
# Gallery discovery are not changed here).  So a path/filename sent in scope A
# may only act on A's registry row: a file registered to another channel is
# 404 before any move/write, and an UNREGISTERED file is only usable where
# legacy data belongs to the scope (compat ``main``) -- elsewhere it has no
# provable owner.  Handlers called directly (not via FastAPI) get ``None`` =
# compat unscoped (strict -> 422 from the stores).

def _channel_of(scope: Any) -> Optional[str]:
    return scope.channel_id if isinstance(scope, ChannelScope) else None


def _kw(channel_id: Optional[str]) -> Dict[str, Any]:
    return {} if channel_id is None else {"channel_id": channel_id}


def _guard_writable(scope: Any) -> None:
    if isinstance(scope, ChannelScope) and not scope.is_implicit_default:
        require_writable(scope)


def _legacy_files_allowed(channel_id: Optional[str]) -> bool:
    scope = resolve_store_scope(channel_id)
    return scope.unscoped or scope.include_legacy


def _unregistered_file_error() -> ChannelError:
    return ChannelError(
        404,
        "resource_not_found",
        "ไฟล์นี้ยังไม่ได้ลงทะเบียนเป็น export ของช่องที่เลือก",
    )


def _raise_if_foreign_product(product_id: Optional[str], channel_id: Optional[str]) -> None:
    """A product of another channel (or a legacy one hidden by strict mode)
    looks like it does not exist (404) -- checked before any file is moved."""
    if not product_id or channel_id is None:
        return
    exists, _owner = ProductStore.owner_of(product_id)
    if exists and ProductStore.find(product_id, channel_id=channel_id) is None:
        raise ChannelError(404, "resource_not_found", "ไม่พบสินค้าที่ร้องขอ")


def _is_contained(path: Path, root: Path) -> bool:
    """True when `path` sits inside `root`.

    `str.startswith` would also accept a sibling whose name merely extends
    the root's (``Capcut_evil`` against ``Capcut``), so compare path
    components instead.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

router = APIRouter(tags=["Exports"])

# "Ready_to_post" was a permanent lie the moment the first clip got posted --
# nothing ever moved the file out, so list_exports() (scanning ONLY this dir)
# kept showing a posted clip as still-to-post forever. Posted/ is scanned
# alongside it below so a moved clip stays findable, tagged `is_posted`.
POSTED_DIR = EXPORTS_DIR.parent / "Posted"

# Project manifests are only needed to enrich legacy/unlinked exports with
# script metadata.  Keep a stat-keyed snapshot so a gallery poll does not
# decode every project.json repeatedly.  The key includes each manifest's
# mtime and size, so a newly created, changed, or removed manifest naturally
# invalidates the snapshot without a time-based stale window.
_PROJECT_DISK_INFO_LOCK = threading.Lock()
_PROJECT_DISK_INFO_CACHE: tuple[str, tuple[tuple[str, str, int, int], ...], Dict[str, dict]] | None = None


def _load_project_disk_info(projects_dir: Path) -> Dict[str, dict]:
    """Load project metadata once per unchanged manifest set."""

    global _PROJECT_DISK_INFO_CACHE

    try:
        project_dirs = [p.parent for p in projects_dir.rglob("project.json")
                        if not p.is_symlink() and p.resolve().is_relative_to(projects_dir.resolve())]
    except OSError:
        return {}

    signature_rows = []
    for pdir in project_dirs:
        manifest = pdir / "project.json"
        try:
            stat = manifest.stat()
        except OSError:
            continue
        signature_rows.append((str(pdir), pdir.relative_to(projects_dir).as_posix().lower(), stat.st_mtime_ns, stat.st_size))
    signature = tuple(sorted(signature_rows))
    cache_key = str(projects_dir.resolve(strict=False))

    with _PROJECT_DISK_INFO_LOCK:
        cached = _PROJECT_DISK_INFO_CACHE
        if cached and cached[0] == cache_key and cached[1] == signature:
            return dict(cached[2])

    loaded: Dict[str, dict] = {}
    for raw_path, lowered_name, _mtime_ns, _size in signature:
        try:
            with open(Path(raw_path) / "project.json", "r", encoding="utf-8") as pf:
                loaded[lowered_name] = json.load(pf)
        except (OSError, ValueError, TypeError):
            continue

    with _PROJECT_DISK_INFO_LOCK:
        _PROJECT_DISK_INFO_CACHE = (cache_key, signature, loaded)
    return dict(loaded)


def _stored_export_path(raw_path: Any) -> Optional[Path]:
    """Resolve a ProductStore export path without guessing from a display name."""
    if not raw_path:
        return None
    path = Path(str(raw_path))
    return path.resolve() if path.is_absolute() else (BASE_DIR / path).resolve()


def _is_actual_posted_export(file_path: Path, angle: Optional[Dict[str, Any]]) -> bool:
    """Return true only for the export file that has posted evidence.

    ``angle.status == 'posted'`` is angle-level history, not a version
    identity. Older files of that angle must remain deletable. A physical
    file in Posted/ is conclusive; otherwise use the exact stored video path,
    with a same-name Posted/ duplicate treated as the already-posted copy.
    """
    resolved = file_path.resolve()
    if resolved.parent == POSTED_DIR.resolve():
        return True
    if not angle or not (angle.get("status") == "posted" or angle.get("posted_at")):
        return False
    stored = _stored_export_path(angle.get("video_url"))
    if stored and stored == resolved:
        # Older mark-posted attempts could leave the same filename in both
        # folders while the manifest still points at Ready_to_post. The
        # Ready copy is then the removable duplicate; Posted/ is the actual
        # evidence file and is the only one that stays locked.
        if resolved.parent == EXPORTS_DIR.resolve() and (POSTED_DIR / resolved.name).is_file():
            return False
        return True
    return False


def _is_posted_duplicate_copy(
    file_path: Path,
    angle: Optional[Dict[str, Any]],
    registry_by_path: Dict[Path, Dict[str, Any]],
) -> bool:
    """Identify the old Ready copy left beside its Posted proof.

    The old move flow could leave the same MP4 in both directories. Matching
    that pair by basename alone would be unsafe, so require identical bytes
    and a Posted registry record (or posted evidence from the angle).
    """
    if file_path.parent.resolve() != EXPORTS_DIR.resolve():
        return False
    posted_peer = POSTED_DIR / file_path.name
    if not posted_peer.is_file():
        return False
    posted_record = registry_by_path.get(posted_peer.resolve())
    if not posted_record or posted_record.get("status") != "posted":
        if not _is_actual_posted_export(posted_peer, angle):
            return False
    return _same_file_contents(file_path, posted_peer)


def _find_cover_by_stem(stem: str) -> Optional[Path]:
    """Find a generated 9:16 cover by its canonical stem."""
    name = str(stem or "").strip()
    if not name or not COVERS_DIR.exists():
        return None
    for suffix in ("_cover.jpg", "_cover_3x4.jpg"):
        expected = f"{name}{suffix}"
        direct = COVERS_DIR / expected
        if direct.is_file():
            return direct
        expected_folded = expected.casefold()
        for candidate in COVERS_DIR.iterdir():
            if candidate.is_file() and candidate.name.casefold() == expected_folded:
                return candidate
    return None


def _find_cover_sibling(cover: Path, suffix: str) -> Optional[Path]:
    """Find the other generated crop next to ``cover`` (case-insensitive)."""
    name = cover.name
    folded = name.casefold()
    if folded.endswith("_cover_3x4.jpg"):
        base = name[:-len("_cover_3x4.jpg")]
    elif folded.endswith("_cover.jpg"):
        base = name[:-len("_cover.jpg")]
    else:
        return None
    expected = f"{base}{suffix}"
    direct = cover.parent / expected
    if direct.is_file():
        return direct
    if cover.parent.exists():
        expected_folded = expected.casefold()
        for candidate in cover.parent.iterdir():
            if candidate.is_file() and candidate.name.casefold() == expected_folded:
                return candidate
    return None


def _promote_tiktok_cover_variant(info: Dict[str, Any]) -> None:
    """Expose both crops and make 3:4 the generic cover for TikTok flows."""
    raw = info.get("cover_path")
    if not raw:
        return
    selected = Path(raw)
    if not selected.is_absolute():
        selected = BASE_DIR / selected
    if not selected.is_file():
        return

    cover_3x4 = selected if selected.name.casefold().endswith("_cover_3x4.jpg") else _find_cover_sibling(selected, "_cover_3x4.jpg")
    cover_9x16 = selected if selected.name.casefold().endswith("_cover.jpg") else _find_cover_sibling(selected, "_cover.jpg")

    def add_variant(key: str, path: Optional[Path]) -> None:
        if not path or not path.is_file():
            return
        rel = str(path.relative_to(BASE_DIR)).replace("\\", "/")
        info[key] = rel
        info[key.replace("_path", "_url")] = f"/api/media/{rel}"

    add_variant("cover_3x4_path", cover_3x4)
    add_variant("cover_9x16_path", cover_9x16)
    if cover_3x4 and cover_3x4.is_file():
        rel = str(cover_3x4.relative_to(BASE_DIR)).replace("\\", "/")
        info["cover_path"] = rel
        info["cover_url"] = f"/api/media/{rel}"


def _find_project_cover(project_name: str) -> Optional[Path]:
    """Find a cover saved with the canonical project name."""
    return _find_cover_by_stem(project_name)


def _find_product_cover(product_name: str) -> Optional[Path]:
    """Find a legacy cover saved with the product name."""
    return _find_cover_by_stem(product_name)


@router.get("/api/exports")
def list_exports(scope: ChannelScope = Depends(get_channel_scope)):
    """Lists all rendered videos in 04_Exports/Ready_to_post enriched with product & script metadata.
    Distinguishes latest active export vs previous superseded versions vs external unlinked files.

    Channel-scoped (P2.2): only files registered to the request channel are
    listed and matched against that channel's products; files registered to
    another channel are hidden; unregistered files are listed/hydrated only
    where legacy data belongs to the scope (compat ``main``).
    """
    channel_id = _channel_of(scope)
    files = sorted(
        list(EXPORTS_DIR.glob("*.mp4")) + list(POSTED_DIR.glob("*.mp4")),
        key=os.path.getmtime, reverse=True,
    )
    all_products = ProductStore.get_all(**_kw(channel_id))

    # 1. Build lookup tables
    project_angle_map: Dict[str, tuple] = {}
    # Check 1 below used to be a nested "for every product: for every angle"
    # scan per export file (O(files x products x angles)). It is replaced by
    # two O(1) dict lookups (by video_url stem, by video_url name) built once
    # here. The old loop broke on the FIRST product/angle (in all_products /
    # angles iteration order) whose video_url stem OR name matched a given
    # file -- a plain dict keyed by stem/name would instead let a LATER angle
    # that happens to share a stem/name silently overwrite an earlier one.
    # Each entry below is (insertion_seq, product, angle) so the lookup at
    # match time can pick whichever of the stem/name hits has the smaller
    # seq, reproducing the original first-match-wins priority exactly.
    video_stem_map: Dict[str, tuple] = {}
    video_name_map: Dict[str, tuple] = {}
    product_angle_id_map: Dict[tuple, tuple] = {}
    # Check 3's exact-equality case (fstem_low == pid), first-match-wins.
    product_id_map: Dict[str, dict] = {}
    _angle_seq = 0
    for p in all_products:
        pid_key = (p.get("id") or "").lower()
        if pid_key and pid_key not in product_id_map:
            product_id_map[pid_key] = p
        for proj_name in p.get("projects", []):
            if proj_name:
                project_angle_map[proj_name.lower()] = (p, None)
        for a in p.get("angles", []):
            angle_key = a.get("angle_id") or a.get("id")
            if pid_key and angle_key:
                product_angle_id_map[(pid_key, str(angle_key))] = (p, a)
            proj = a.get("project_name", "")
            if proj:
                project_angle_map[proj.lower()] = (p, a)
            vid_url = a.get("video_url", "")
            if vid_url:
                project_angle_map[Path(vid_url).stem.lower()] = (p, a)
                project_angle_map[Path(vid_url).name.lower()] = (p, a)

                stem_key = Path(vid_url).stem.lower()
                name_key = Path(vid_url).name.lower()
                if stem_key not in video_stem_map:
                    video_stem_map[stem_key] = (_angle_seq, p, a)
                if name_key not in video_name_map:
                    video_name_map[name_key] = (_angle_seq, p, a)
                _angle_seq += 1

    # Check 03_Projects/ folders to get script_data if available. The helper
    # reuses decoded manifests while their stat signature is unchanged.
    projects_dir = BASE_DIR / "03_Projects"
    project_disk_info = _load_project_disk_info(projects_dir)

    # A registry hit is authoritative. Filename/project matching below is
    # retained only as a one-time migration path for exports made before
    # export_id existed.
    registry_by_path: Dict[Path, Dict[str, Any]] = {}
    foreign_paths: set = set()
    try:
        for record in ExportRegistry.all(**_kw(channel_id)):
            registered_path = _stored_export_path(record.get("path"))
            if registered_path:
                registry_by_path[registered_path] = record
        for raw in ExportRegistry.out_of_scope_paths(**_kw(channel_id)):
            foreign = _stored_export_path(raw)
            if foreign:
                foreign_paths.add(foreign)
    except ChannelError:
        raise
    except Exception as registry_err:
        print(f"[api_exports] WARNING: could not load export registry: {registry_err}")

    # Discover namespaced outputs by their scoped registry identity. Never
    # recursively import unregistered files from another channel's directory.
    candidates = {f.resolve(): f for f in files}
    for path in registry_by_path:
        if path.suffix.lower() == ".mp4" and path.is_file() and any(_is_contained(path, root) for root in (EXPORTS_DIR, POSTED_DIR)):
            candidates.setdefault(path, path)
    files = sorted(candidates.values(), key=os.path.getmtime, reverse=True)

    if channel_id is not None:
        legacy_ok = _legacy_files_allowed(channel_id)
        files = [
            f for f in files
            if f.resolve() in registry_by_path
            or (legacy_ok and f.resolve() not in foreign_paths)
        ]

    # Pass 1: Identify match for each file
    raw_matches = []
    for f in files:
        fname_low = f.name.lower()
        fstem_low = f.stem.lower()

        matched_prod = None
        matched_angle = None
        matched_proj_name = None

        registry_record = registry_by_path.get(f.resolve())
        if registry_record:
            matched_proj_name = registry_record.get("project_name")
            registered_product = product_id_map.get(str(registry_record.get("product_id") or "").lower())
            registered_angle = None
            if registered_product:
                registered_angle = product_angle_id_map.get(
                    (str(registered_product.get("id") or "").lower(), str(registry_record.get("angle_id") or "")),
                    (None, None),
                )[1]
            if registered_product:
                matched_prod = registered_product
                matched_angle = registered_angle
                matched_proj_name = registry_record.get("project_name") or (
                    registered_angle or {}
                ).get("project_name")

        # 1. Exact angle video_url match (O(1) via the maps built above,
        # instead of scanning every product's every angle for every file)
        name_hit = video_name_map.get(fname_low)
        stem_hit = video_stem_map.get(fstem_low)
        if name_hit and stem_hit:
            winner = name_hit if name_hit[0] <= stem_hit[0] else stem_hit
        else:
            winner = name_hit or stem_hit
        if winner and not matched_prod:
            _, p, a = winner
            matched_prod, matched_angle = p, a
            matched_proj_name = a.get("project_name")

        # 2. Exact project name match (stripping timestamp suffix like _YYYYMMDD_HHMMSS)
        if not matched_prod:
            base_proj_name = re.sub(r'_\d{8}_\d{6}(_draft)?$', '', fstem_low)
            if base_proj_name in project_angle_map:
                p, a = project_angle_map[base_proj_name]
                matched_prod = p
                matched_angle = a
                matched_proj_name = a.get("project_name") if a else base_proj_name
            elif fstem_low in project_angle_map:
                p, a = project_angle_map[fstem_low]
                matched_prod = p
                matched_angle = a
                matched_proj_name = a.get("project_name") if a else fstem_low

        # 2.5 Check project_disk_info if still not matched
        if not matched_proj_name:
            base_proj_name = re.sub(r'_\d{8}_\d{6}(_draft)?$', '', fstem_low)
            if base_proj_name in project_disk_info:
                matched_proj_name = base_proj_name
            elif fstem_low in project_disk_info:
                matched_proj_name = fstem_low

        # 3. Product ID match (exact token match). The exact-equality case
        # (by far the common one -- pass 1/2 already caught most files, so
        # this is only reached for files with no angle/project match at
        # all) is an O(1) dict lookup via product_id_map built once above.
        # The prefix ("{pid}_...") and infix ("..._{pid}_...") cases can't be
        # turned into a plain dict lookup (pid is a variable-length,
        # arbitrary-content token -- there is no fixed key to index on
        # without risking a different match than the original substring
        # scan), so they still walk all_products, but ONLY for files that
        # reach this fallback, not for every file.
        if not matched_prod:
            exact_hit = product_id_map.get(fstem_low)
            if exact_hit:
                matched_prod = exact_hit
            else:
                for p in all_products:
                    pid = p.get("id", "").lower()
                    if pid and (fstem_low.startswith(f"{pid}_") or f"_{pid}_" in fstem_low):
                        matched_prod = p
                        break

        disk_proj = project_disk_info.get(matched_proj_name.lower()) if matched_proj_name else None
        if registry_record and registry_record.get("project_name"):
            canonical_name = registry_record["project_name"]
            canonical = project_disk_info.get(canonical_name.lower())
            if canonical and canonical.get("engine") == "hyperframes":
                matched_proj_name, disk_proj = canonical_name, canonical
                if canonical.get("source_binding", {}).get("type") in {"standalone", "gadget_project"}:
                    matched_prod, matched_angle = None, None

        raw_matches.append({
            "file": f,
            "product": matched_prod,
            "angle": matched_angle,
            "proj_name": matched_proj_name,
            "disk_proj": disk_proj,
            "registry_record": registry_record,
        })

    # Pass 2: Determine versioning per group
    latest_file_per_group: Dict[str, Any] = {}
    for item in raw_matches:
        p = item["product"]
        a = item["angle"]
        proj = item["proj_name"]
        group_key = None
        if p and a:
            group_key = f"{p.get('id')}:{a.get('angle_id') or a.get('id')}"
        elif proj:
            group_key = f"proj:{proj}"
        elif p:
            group_key = f"prod:{p.get('id')}"

        if group_key and group_key not in latest_file_per_group and not _is_posted_duplicate_copy(
            item["file"], item["angle"], registry_by_path
        ):
            latest_file_per_group[group_key] = item["file"]

    # Hydrate registry identities in one transaction. The old loop called
    # ExportRegistry.ensure() once per MP4, opening a read-modify-write
    # transaction for every file and making this read endpoint scale linearly
    # with database commits as the export library grows.
    registry_requests = []
    for item in raw_matches:
        export_file = item["file"]
        matched_prod = item["product"]
        matched_angle = item["angle"]
        is_duplicate_copy = _is_posted_duplicate_copy(export_file, matched_angle, registry_by_path)
        is_posted = bool(
            (item["registry_record"] or {}).get("status") == "posted"
            or _is_actual_posted_export(export_file, matched_angle)
        )
        if is_duplicate_copy:
            is_posted = False
        item["_is_duplicate_copy"] = is_duplicate_copy
        item["_is_posted"] = is_posted
        registry_requests.append({
            "path": export_file,
            "product_id": matched_prod.get("id") if matched_prod else None,
            "angle_id": (matched_angle.get("angle_id") or matched_angle.get("id")) if matched_angle else None,
            "project_name": (matched_angle or {}).get("project_name") or item["proj_name"],
            "status": "posted" if is_posted else "rendered",
            "posted_at": (matched_angle or {}).get("posted_at") if is_posted else None,
        })

    try:
        ensured_records = ExportRegistry.ensure_many(registry_requests, **_kw(channel_id))
    except Exception as registry_err:
        # Preserve the legacy per-file fallback if a read-only/older
        # installation cannot perform the bulk write.
        print(f"[api_exports] WARNING: bulk export identity hydration failed: {registry_err}")
        ensured_records = []
        for request in registry_requests:
            try:
                ensured_records.append(ExportRegistry.ensure(
                    request["path"],
                    product_id=request["product_id"],
                    angle_id=request["angle_id"],
                    project_name=request["project_name"],
                    status=request["status"],
                    posted_at=request["posted_at"],
                    **_kw(channel_id),
                ))
            except Exception as single_err:
                print(f"[api_exports] WARNING: could not persist export identity for {request['path'].name}: {single_err}")
                ensured_records.append(None)

    for item, record in zip(raw_matches, ensured_records):
        item["_export_record"] = record

    results = []
    for item in raw_matches:
        f = item["file"]
        matched_prod = item["product"]
        matched_angle = item["angle"]
        matched_proj_name = item["proj_name"]
        disk_proj = item["disk_proj"]
        registry_record = item.get("_export_record") or item["registry_record"]
        is_duplicate_copy = item["_is_duplicate_copy"]
        is_posted = item["_is_posted"]

        info = get_file_info(f)
        if is_duplicate_copy:
            # The Ready copy is removable, but it must never be offered to
            # Extension as the latest clip when its identical Posted proof
            # already exists.
            is_posted = False
            info["is_duplicate_copy"] = True
        info["is_posted"] = is_posted
        if registry_record:
            export_record = registry_record
            info["export_id"] = export_record["id"]
            info["export_status"] = export_record.get("status")
        else:
            # Listing remains usable on a legacy read-only installation;
            # render/mark flows still persist identity before they proceed.
            info["export_id"] = None
            info["export_status"] = "posted" if is_posted else "rendered"
        if not info.get("cover_path"):
            project_name = (matched_angle or {}).get("project_name") or matched_proj_name
            project_cover = _find_project_cover(project_name)
            if project_cover:
                rel_cover = str(project_cover.relative_to(BASE_DIR)).replace("\\", "/")
                info["cover_path"] = rel_cover
                info["cover_url"] = f"/api/media/{rel_cover}"
        if not info.get("cover_path") and matched_prod:
            product_cover = _find_product_cover(matched_prod.get("name", ""))
            if product_cover:
                rel_cover = str(product_cover.relative_to(BASE_DIR)).replace("\\", "/")
                info["cover_path"] = rel_cover
                info["cover_url"] = f"/api/media/{rel_cover}"
        _promote_tiktok_cover_variant(info)

        group_key = None
        if matched_prod and matched_angle:
            group_key = f"{matched_prod.get('id')}:{matched_angle.get('angle_id') or matched_angle.get('id')}"
        elif matched_proj_name:
            group_key = f"proj:{matched_proj_name}"
        elif matched_prod:
            group_key = f"prod:{matched_prod.get('id')}"

        latest_f = latest_file_per_group.get(group_key) if group_key else None
        if latest_f:
            latest_record = registry_by_path.get(latest_f.resolve())
            if latest_record:
                info["latest_export_id"] = latest_record.get("id")

        # Product metadata
        if matched_prod:
            info["product_id"] = matched_prod.get("id")
            info["product_name"] = matched_prod.get("name")
            info["tiktok_product_id"] = (
                matched_prod.get("tiktok_product_id")
                or matched_prod.get("name", "")
            )

        # Script/Angle metadata
        if matched_angle:
            info["angle_id"] = matched_angle.get("angle_id") or matched_angle.get("id")
            info["angle_name"] = matched_angle.get("angle_name")
            info["hook_title"] = matched_angle.get("hook_title")
            info["script_lines"] = matched_angle.get("script_lines")
            info["tiktok_caption"] = matched_angle.get("tiktok_caption")
            info["tiktok_hashtags"] = matched_angle.get("tiktok_hashtags")
            info["ad_tone"] = matched_angle.get("ad_tone")
            info["angle_status"] = matched_angle.get("status")
            info["qc_note"] = matched_angle.get("qc_note")
            info["project_name"] = matched_angle.get("project_name") or matched_proj_name
        elif disk_proj:
            s_data = disk_proj.get("script_data", {})
            info["hook_title"] = s_data.get("hook")
            info["script_lines"] = [l.get("text", "") if isinstance(l, dict) else str(l) for l in s_data.get("lines", [])]
            info["tiktok_caption"] = s_data.get("hook", "") + " พิกัดในตะกร้าเลย 👇" if s_data.get("hook") else ""
            info["tiktok_hashtags"] = f"#{matched_prod.get('name', '').replace(' ', '')} #รีวิวของดี #พิกัดในตะกร้า" if (matched_prod and matched_prod.get("name")) else "#รีวิวของดี #พิกัดในตะกร้า"
            info["project_name"] = disk_proj.get("project_name") or matched_proj_name

        # HyperFrames stores a frozen package for each export. A later Angle
        # revision must not replace historical caption, basket or chosen cover.
        if disk_proj and disk_proj.get("engine") == "hyperframes":
            packages = disk_proj.get("publish_package_refs") or []
            package = next((p for p in packages if p.get("export_id") == info.get("export_id")), None)
            if package:
                for key in ("cover_url", "cover_3x4_path", "cover_3x4_url", "cover_9x16_path", "cover_9x16_url"):
                    info.pop(key, None)
                info.update(tiktok_caption=package.get("caption", ""),
                            tiktok_hashtags=" ".join(package.get("hashtags") or []),
                            tiktok_product_id=package.get("tiktok_product_id", ""),
                            cover_path=package.get("cover_path"),
                            project_name=package.get("project_name"),
                            source_binding=package.get("source_binding"),
                            composition_revision=package.get("composition_revision"))
                if package.get("source_title"):
                    info["product_name"] = package["source_title"]
                    info["hook_title"] = package.get("source_hook") or package["source_title"]
                if package.get("cover_path"):
                    info["cover_url"] = f"/api/media/{package['cover_path']}"
                from scripts.hyperframes_publish_readiness import export_readiness
                try:
                    review = export_readiness(BASE_DIR, channel_id or "main", {"id": info["export_id"], "project_name": info["project_name"], "path": info.get("rel_path") or info.get("path")})
                    info.update(source_review_required=review["required"], source_review_ready=review["ready"], source_review_project_id=review.get("project_id"))
                except ChannelError as error:
                    info.update(source_review_required=True, source_review_ready=False, source_review_error=error.code)

        # CoverStudio also serves legacy exports: a saved exact selection
        # must survive reload for either engine, without changing old queues.
        if info.get("export_id"):
            from scripts.export_cover_bindings import ExportCoverBindingStore
            selections = ExportCoverBindingStore(BASE_DIR)
            try:
                selected = [selections.get(channel_id, info["export_id"], format=fmt)
                            for fmt in ("3:4", "9:16")]
                for binding in filter(None, selected):
                    variant = "3x4" if binding["format"] == "3:4" else "9x16"
                    info[f"cover_{variant}_path"] = binding["path"]
                    info[f"cover_{variant}_url"] = f"/api/media/{binding['path']}"
                chosen = next(filter(None, selected), None)
                if chosen:
                    info.update(cover_path=chosen["path"],
                                cover_url=f"/api/media/{chosen['path']}",
                                cover_sha256=chosen["sha256"],
                                cover_format=chosen["format"],
                                cover_revision=chosen["revision"])
            except ChannelError as error:
                for key in ("cover_url", "cover_3x4_path", "cover_3x4_url", "cover_9x16_path", "cover_9x16_url"):
                    info.pop(key, None)
                info.update(cover_path=None, cover_selection_error=error.code)

        # Determine version status
        has_script = bool(matched_angle or (disk_proj and disk_proj.get("script_data", {}).get("hook")) or
                          (disk_proj and disk_proj.get("engine") == "hyperframes" and package))

        if has_script:
            info["is_unlinked"] = False
            if latest_f and latest_f == f:
                info["is_latest"] = True
                info["is_previous_version"] = False
            else:
                info["is_latest"] = False
                info["is_previous_version"] = True
                if latest_f:
                    info["latest_video_name"] = latest_f.name
                    info["latest_video_path"] = str(latest_f)
                    # Derived from the file's real parent, not hardcoded to
                    # Ready_to_post -- the "latest version" of a group can now
                    # be one that already moved to Posted/.
                    info["latest_video_rel"] = str(latest_f.relative_to(BASE_DIR)).replace("\\", "/")

            angle_vid = (matched_angle.get("video_url") or "").lower() if matched_angle else ""
            angle_qc_note = matched_angle.get("qc_note") if matched_angle else None
            is_this_file_rejected = False
            if angle_qc_note and angle_vid:
                is_this_file_rejected = (fname_low in angle_vid or str(f).lower() in angle_vid or Path(angle_vid).name.lower() == fname_low)
            elif angle_qc_note and matched_angle:
                is_this_file_rejected = (latest_f and latest_f == f)

            info["is_qc_rejected"] = is_this_file_rejected
            if not is_this_file_rejected:
                info["qc_note"] = None
        else:
            info["is_unlinked"] = True
            info["is_latest"] = False
            info["is_previous_version"] = False
            info["is_qc_rejected"] = False

        results.append(info)

    return {"exports": results}


@router.post("/api/exports/link-angle")
def link_export_to_angle(req: LinkAngleRequest, scope: ChannelScope = Depends(get_channel_scope)):
    """Links an exported video to a product angle (both must belong to the request channel)."""
    channel_id = _channel_of(scope)
    try:
        _guard_writable(scope)
        _raise_if_foreign_product(req.product_id, channel_id)
        # Scoped lookups: an export id / file of another channel -> 404 here,
        # before anything is registered or linked.
        export_record = ExportRegistry.lookup(export_id=req.export_id, **_kw(channel_id)) if req.export_id else None
        if req.export_id and export_record is None:
            raise HTTPException(status_code=409, detail="ไม่พบ export_id ที่ระบุ จึงหยุดการผูกคลิปเพื่อป้องกันการแมพผิดตัว")
        if export_record is None:
            export_record = ExportRegistry.lookup(path=req.video_path, **_kw(channel_id))
        if export_record is None:
            if not _legacy_files_allowed(channel_id):
                raise _unregistered_file_error()
            export_record = ExportRegistry.ensure(
                req.video_path,
                product_id=req.product_id,
                angle_id=req.angle_id,
                status="rendered",
                **_kw(channel_id),
            )
        requested_path = _stored_export_path(req.video_path)
        registered_path = _stored_export_path(export_record.get("path"))
        if requested_path != registered_path:
            raise HTTPException(status_code=409, detail="export_id ไม่ตรงกับไฟล์ที่เลือก")
        if export_record.get("status") == "posted":
            raise HTTPException(status_code=409, detail="คลิปนี้โพสต์แล้ว ไม่สามารถนำกลับไปผูกเป็นคลิปใหม่ได้")
        _require_latest_export(export_record, req.product_id, req.angle_id, channel_id)
        updated = ProductStore.update_angle_status(
            product_id=req.product_id,
            angle_id=req.angle_id,
            status="rendered",
            video_url=req.video_path,
            export_id=export_record["id"],
            **_kw(channel_id),
        )
        return {"status": "success", "product": updated}
    except ChannelError:
        # Typed scope errors keep their status/code (404/409/422) -- the
        # generic 400 below is the route's legacy contract for everything else.
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class MarkPostedRequest(BaseModel):
    file_path: str
    export_id: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None


def _posted_companions(
    mp4_path: Path,
    product_id: Optional[str] = None,
    angle_id: Optional[str] = None,
    channel_id: Optional[str] = None,
) -> List[Path]:
    """Every file that travels with an export when it moves: the gallery
    poster (webp) and TikTok covers (3:4, 9:16)."""
    stem = mp4_path.stem
    found = set()
    poster = mp4_path.with_suffix(".webp")
    if poster.exists():
        found.add(poster)

    covers_dir = BASE_DIR / "05_Covers_Thumbnails"
    patterns = [
        f"{stem}_cover.jpg",
        f"{stem}_cover_9x16.jpg",
        f"{stem}_cover_3x4.jpg",
        f"{stem}_cover_9x16.png",
        f"{stem}_cover_3x4.png",
        f"{stem}_cover.png",
    ]
    for pat in patterns:
        c = covers_dir / pat
        if c.exists():
            found.add(c)

    if product_id and angle_id:
        try:
            prod = ProductStore.get(product_id, **_kw(channel_id))
            if prod:
                for a in prod.get("angles", []):
                    if a.get("angle_id") == angle_id or a.get("id") == angle_id:
                        for key in ("cover_path", "cover_9x16_path", "cover_3x4_path"):
                            val = a.get(key)
                            if val:
                                p = Path(val)
                                if not p.is_absolute():
                                    p = BASE_DIR / p
                                if p.exists() and p.is_file():
                                    found.add(p)
        except Exception:
            pass

    return sorted(found)


def _mark_scheduled_queue_item_posted(
    source: Path,
    destination: Path,
    export_id: Optional[str] = None,
    channel_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Close the durable queue row when the extension moves this export.

    Returns a copy of the matched queue row (hook/style/caption/schedule
    metadata for the post log) or None when no row matched / the queue is
    unavailable.

    Queue identity is filename-based across Ready_to_post/Posted, so moving
    the file must update its lifecycle while keeping the same one-clip guard.
    A queue update is best-effort here: the export move remains authoritative
    even if an old installation has no schedule table yet.

    Channel-scoped (P2.2): only the request channel's queue rows are looked
    at, and the filename fallback must be unambiguous (one row, preferring
    rows that are not posted yet) -- otherwise nothing is changed.
    """
    try:
        from scripts.api_schedule_queue import video_key
        from scripts.schedule_store import ScheduleQueueStore, now_iso
        key = video_key(source)
        with ScheduleQueueStore.transaction(**_kw(channel_id)) as records:
            # An exact export_id match is preferred, but a queue row's
            # export_id goes stale the moment the angle is re-rendered after
            # being queued: a fresh render mints a new export_id while the
            # queue row still holds whatever it was queued under. Matching
            # export_id only used to mean that case silently updated nothing
            # -- the row for this exact physical file still exists (under its
            # old export_id/video_key), so fall back to matching the file
            # itself rather than leaving a genuinely-posted clip stuck
            # showing as pending in the queue and the Extension forever.
            target_row = None
            if export_id:
                target_row = next((row for row in records if row.get("export_id") == export_id), None)
            if target_row is None:
                by_file = [
                    row for row in records
                    if row.get("video_key") == key
                    or Path(str(row.get("video_path", ""))).name.casefold() == source.name.casefold()
                ]
                open_rows = [row for row in by_file if row.get("status") != "posted"]
                pool = open_rows or by_file
                target_row = pool[0] if len(pool) == 1 else None
            if target_row is not None:
                target_row["video_path"] = str(destination.relative_to(BASE_DIR)).replace("\\", "/")
                target_row["video_key"] = key
                if export_id:
                    target_row["export_id"] = export_id
                target_row["status"] = "posted"
                target_row["posted_at"] = now_iso()
                target_row["updated_at"] = now_iso()
                return dict(target_row)
    except Exception:
        # Never turn a successful file move into a failed post because the
        # optional queue mirror is unavailable.
        return None
    return None


def _hashtag_list(value: Any) -> List[str]:
    """Queue/product rows keep hashtags as one string; the post log wants a list."""
    if isinstance(value, (list, tuple)):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    return re.findall(r"#[^\s#]+", text) or text.split()


def _planned_post_time(scheduled_at: Any) -> Optional[str]:
    """Naive local ISO time a scheduled post really goes live, or None.

    The extension marks a clip posted when TikTok ACCEPTS it, which for a
    scheduled post is before it is public. A future scheduled_at is therefore
    the true post time (so metrics age counts from it); a past or missing one
    means "posted now" and the caller falls back to the current time.
    """
    import datetime as _dt
    try:
        when = _dt.datetime.fromisoformat(str(scheduled_at or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        return when.isoformat(timespec="seconds") if when > _dt.datetime.now() else None
    local = when.astimezone().replace(tzinfo=None)
    return local.isoformat(timespec="seconds") if local > _dt.datetime.now() else None


def _record_posted_in_post_log(
    export_record: Dict[str, Any],
    destination: Path,
    queue_row: Optional[Dict[str, Any]],
    product_id: Optional[str],
    angle_id: Optional[str],
    channel_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Write exactly one PostLog row for a clip just marked posted.

    Without this the row only appeared later through a fuzzy TikTok stats
    match, and hook / style_preset / hook_color / schedule time were lost.
    Idempotent (PostLog.record_posted_export matches on (channel, export_id),
    then an UNAMBIGUOUS legacy clip basename in the same channel), so a
    repeated mark-posted or a later stats auto-register reuses the same row.
    Returns the PostLog result (``status`` ``ambiguous`` = nothing written,
    reported by the caller) or None. Best-effort: never fails an
    already-completed file move.
    """
    try:
        from scripts import post_log as post_log_module
        # The post log is anchored at the real project root. Skip when this
        # module was pointed at a different root (isolated test workspaces),
        # so those runs can never write into the real store.db.
        if post_log_module.LOG_PATH.parent.parent.resolve() != BASE_DIR.resolve():
            return None
        row = queue_row or {}
        product: Dict[str, Any] = {}
        angle: Dict[str, Any] = {}
        pid = product_id or row.get("product_id") or export_record.get("product_id")
        aid = angle_id or row.get("angle_id") or export_record.get("angle_id")
        if pid:
            try:
                product = ProductStore.get(pid, **_kw(channel_id)) or {}
                angle = next(
                    (a for a in product.get("angles", []) if aid and (a.get("angle_id") == aid or a.get("id") == aid)),
                    {},
                )
            except Exception:
                product, angle = {}, {}
        hook = str(row.get("hook_title") or angle.get("hook_title") or "")
        scheduled_at = str(row.get("scheduled_at") or "")
        return post_log_module.PostLog.record_posted_export(
            product_name=str(row.get("product_name") or product.get("name") or product.get("product_name") or ""),
            clip_file=destination.name,
            export_id=str(export_record.get("id") or ""),
            product_id=str(pid or ""),
            angle_key=str(aid or ""),
            angle_title=str(angle.get("angle_name") or angle.get("angle_title") or hook),
            hook=hook,
            style_preset=str(row.get("style_preset") or angle.get("style_preset") or ""),
            hook_color=str(row.get("hook_color") or angle.get("hook_color") or ""),
            caption=str(row.get("caption") or angle.get("tiktok_caption") or angle.get("caption") or "")[:200],
            hashtags=_hashtag_list(row.get("hashtags") or angle.get("tiktok_hashtags") or angle.get("hashtags")),
            scheduled_at=scheduled_at,
            posted_at=_planned_post_time(scheduled_at),
            **_kw(channel_id),
        )
    except Exception as exc:
        print(f"[mark_posted] PostLog notice: {exc}")
        return None


def _same_file_contents(left: Path, right: Path) -> bool:
    try:
        return filecmp.cmp(left, right, shallow=False)
    except OSError:
        return False


def _move_or_reuse_posted(source: Path, destination: Path) -> None:
    """Move one companion into Posted without overwriting posted evidence.

    A previous interrupted/retried mark can leave the same file in both
    folders. Treat identical copies as an idempotent retry and reject a
    conflicting destination with an actionable 409 instead of leaking a 500
    from ``shutil.move``.
    """
    if source.resolve() == destination.resolve():
        return
    if destination.exists():
        if not _same_file_contents(source, destination):
            raise HTTPException(
                status_code=409,
                detail=f"มีไฟล์ชื่อเดียวกันใน Posted/ แต่เนื้อหาไม่ตรงกัน: {destination.name}",
            )
        source.unlink(missing_ok=True)
        return
    try:
        shutil.move(str(source), str(destination))
    except FileNotFoundError:
        # `source` vanished between our exists() check above and this move --
        # a second "mark posted" request for the same clip fired while the
        # first was still in flight (mark_posted's handlers are sync `def`,
        # so FastAPI genuinely runs overlapping requests on separate threads;
        # rapid double-clicks on the mark button reach this window in
        # practice, not just in theory). If `destination` exists now, the
        # other request already finished this exact move -- that's a
        # successful idempotent outcome for THIS request too, not a failure.
        # If it doesn't, something else removed the file; surface that
        # plainly instead of a raw 500 from shutil.move.
        if destination.exists():
            return
        raise HTTPException(
            status_code=409,
            detail=f"ไฟล์หายไประหว่างย้าย (อาจมีการมาร์คคลิปนี้ซ้อนกันอยู่): {source.name}",
        )


def _require_latest_export(
    export_record: Dict[str, Any],
    product_id: Optional[str],
    angle_id: Optional[str],
    channel_id: Optional[str] = None,
) -> None:
    """Prevent a stale version from entering the posting flow (versions of the same channel)."""
    if not product_id or not angle_id:
        return
    latest = ExportRegistry.latest_for_angle(product_id, angle_id, **_kw(channel_id))
    if latest and latest.get("status") != "posted" and latest.get("id") != export_record.get("id"):
        raise HTTPException(
            status_code=409,
            detail="ไฟล์นี้ไม่ใช่ export เวอร์ชันล่าสุดของมุมนี้ กรุณาเลือกคลิปล่าสุด",
        )


@router.post("/api/exports/mark-posted")
def mark_posted(req: MarkPostedRequest, scope: ChannelScope = Depends(get_channel_scope)):
    return _mark_posted_impl(req, scope)


def apply_posted_outcome(req: MarkPostedRequest, scope: ChannelScope, posting_job: dict):
    """Internal receipt repair; HTTP callers cannot select this path."""
    if (posting_job.get("status") != "published" or not posting_job.get("receipt_hash")
            or posting_job.get("channel_id") != _channel_of(scope)
            or posting_job.get("export_id") != req.export_id):
        raise ChannelError(409, "posting_receipt_required", "ต้องมีผลยืนยันของงานและช่องเดียวกันก่อนซ่อมสถานะโพสต์")
    return _mark_posted_impl(req, scope, posting_job=posting_job)


def _mark_posted_impl(req: MarkPostedRequest, scope: ChannelScope, *, posting_job=None):
    """
    Moves a clip (+ its poster/cover) from Ready_to_post/ into Posted/, and
    when the angle is known, sets its status to 'posted' with the new path.

    ProductStore.reconcile() preserves 'posted' status
    regardless of where the manifest's video_url points (product_store.py's
    "Preserve permanent posted status" branch), so moving the file here
    does not fight the background reconciler.

    Channel-scoped (P2.2): the export (by id or file) and the product must
    belong to the request channel -- checked before any file moves.  Recording
    a posted result is allowed for an archived channel (ADR §10.4).
    """
    channel_id = _channel_of(scope)
    src = Path(req.file_path)
    if not src.is_absolute():
        src = BASE_DIR / req.file_path
    src = src.resolve()

    if not (_is_contained(src, EXPORTS_DIR.resolve()) or _is_contained(src, POSTED_DIR.resolve())):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ไม่ได้อยู่ในโฟลเดอร์ export ที่อนุญาต")
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {src.name}")

    _raise_if_foreign_product(req.product_id, channel_id)
    export_record = (
        ExportRegistry.lookup(export_id=req.export_id, **_kw(channel_id))
        if req.export_id
        else ExportRegistry.lookup(path=src, **_kw(channel_id))
    )
    if req.export_id and export_record is None:
        raise HTTPException(status_code=409, detail="ไม่พบ export_id ที่ระบุ จึงหยุดการโพสต์เพื่อป้องกันการเลือกคลิปผิดตัว")
    if export_record is None:
        if not _legacy_files_allowed(channel_id):
            raise _unregistered_file_error()
        export_record = ExportRegistry.ensure(
            src,
            product_id=req.product_id,
            angle_id=req.angle_id,
            status="rendered",
            **_kw(channel_id),
        )
    else:
        registry_path = _stored_export_path(export_record.get("path"))
        if registry_path != src:
            raise HTTPException(
                status_code=409,
                detail="export_id ไม่ตรงกับไฟล์ที่เลือก จึงหยุดการทำรายการเพื่อป้องกันการมาร์กผิดคลิป",
            )

    superseded_job = False
    if posting_job is None:
        _require_latest_export(export_record, req.product_id, req.angle_id, channel_id)
    else:
        latest = ExportRegistry.latest_for_angle(req.product_id, req.angle_id, **_kw(channel_id))
        superseded_job = bool(latest and latest.get("status") != "posted" and latest["id"] != export_record["id"])
    if posting_job is not None and posting_job.get("queue_id"):
        from scripts.schedule_store import ScheduleQueueStore
        queued = ScheduleQueueStore.get_item(posting_job["queue_id"], **_kw(channel_id))
        if not queued or queued.get("export_id") != posting_job["export_id"]:
            raise ChannelError(409, "posting_queue_changed", "คิวเปลี่ยนเจ้าของงานแล้ว ต้องตรวจผลก่อนซ่อมบันทึก")
        if queued.get("posting_job_id") and queued["posting_job_id"] != posting_job["job_id"]:
            raise ChannelError(409, "posting_queue_changed", "คิวเปลี่ยนเจ้าของงานแล้ว ต้องตรวจผลก่อนซ่อมบันทึก")
        if queued.get("status") == "cancelled":
            raise ChannelError(409, "posting_queue_changed", "คิวยกเลิกแล้ว ต้องตรวจผลก่อนซ่อมบันทึก")

    # A receipt has frozen export ownership, but no frozen angle cover/project
    # ownership. Those live pointers can change during repair, so only move
    # companions belonging to this exact export filename.
    companions = _posted_companions(src, None if posting_job else req.product_id,
                                   None if posting_job else req.angle_id, channel_id)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

    dest = POSTED_DIR / src.name
    move_pairs = [(src, dest)]
    for companion in companions:
        if companion.exists():
            move_pairs.append((companion, POSTED_DIR / companion.name))

    # Posted/ is still one flat folder (P6): never move onto a path another
    # channel's registry row already owns (it would merge two channels'
    # exports into one file).  Checked before any file moves.
    if channel_id is not None and dest.resolve() != src:
        visible_ids = {str(export_record.get("id"))}
        for owner_export_id, owner in ExportRegistry.path_owners(dest):
            if owner_export_id in visible_ids:
                continue
            if not resolve_store_scope(channel_id).owns({"channel_id": owner}):
                raise ChannelError(
                    409,
                    "export_path_conflict",
                    f"มีคลิปชื่อเดียวกันของช่องอื่นอยู่ใน Posted/ แล้ว: {dest.name} จึงหยุดเพื่อไม่ให้ทับไฟล์ของอีกช่อง",
                )

    # Preflight all collisions before moving anything, so a conflicting
    # poster/cover cannot leave a half-moved export behind.
    for source, destination in move_pairs:
        if destination.exists() and source.resolve() != destination.resolve() and not _same_file_contents(source, destination):
            raise HTTPException(
                status_code=409,
                detail=f"มีไฟล์ชื่อเดียวกันใน Posted/ แต่เนื้อหาไม่ตรงกัน: {destination.name}",
            )

    _move_or_reuse_posted(src, dest)
    moved = [str(dest.relative_to(BASE_DIR)).replace("\\", "/")]
    new_cover_path = None
    new_cover_3x4 = None
    new_cover_9x16 = None

    for companion, companion_dest in move_pairs[1:]:
        _move_or_reuse_posted(companion, companion_dest)
        rel_dest = str(companion_dest.relative_to(BASE_DIR)).replace("\\", "/")
        moved.append(rel_dest)
        lower_name = companion.name.lower()
        if "9x16" in lower_name:
            new_cover_9x16 = rel_dest
        elif "3x4" in lower_name:
            new_cover_3x4 = rel_dest
        elif "cover" in lower_name and lower_name.endswith((".jpg", ".png", ".webp")):
            if not new_cover_path:
                new_cover_path = rel_dest
            if not new_cover_3x4:
                new_cover_3x4 = rel_dest

    # Fallbacks if one variant exists
    if new_cover_path and not new_cover_3x4:
        new_cover_3x4 = new_cover_path
    if not new_cover_path and new_cover_9x16:
        new_cover_path = new_cover_9x16

    # Mark registry before updating ProductStore
    ExportRegistry.move_and_mark_posted(export_record["id"], dest, **_kw(channel_id))

    product_result: Dict[str, Any] = {}
    if req.product_id and req.angle_id and not superseded_job:
        try:
            product_result["product"] = ProductStore.update_angle_status(
                product_id=req.product_id,
                angle_id=req.angle_id,
                status="posted",
                video_url=str(dest.relative_to(BASE_DIR)).replace("\\", "/"),
                export_id=export_record["id"],
                cover_path=new_cover_path,
                cover_3x4_path=new_cover_3x4,
                cover_9x16_path=new_cover_9x16,
                **({"require_latest_export": True} if posting_job is not None else {}),
                **_kw(channel_id),
            )
            if posting_job is not None and product_result["product"] is None:
                superseded_job = True
                product_result.pop("product")
        except Exception as e:
            # The file already moved -- report the status-update failure
            # rather than rolling the move back; "it's in Posted/" stays true
            # either way, and the angle can be re-linked by hand afterward.
            product_result["status_warning"] = str(e)

    # Positional on purpose: tests replace this helper with ``lambda *args``.
    # Durable publication effects select the exact queue job later, under its
    # own transaction. Legacy basename/export matching must never repair a
    # different queue job, and the post log uses the frozen receipt payload.
    queue_row = dict(posting_job) if posting_job is not None else _mark_scheduled_queue_item_posted(src, dest, export_record["id"], channel_id)
    post_result = _record_posted_in_post_log(export_record, dest, queue_row, req.product_id, req.angle_id, channel_id)
    if post_result is None:
        product_result["post_log_warning"] = {"code": "post_log_incomplete", "detail": "ประวัติโพสต์ยังบันทึกไม่สำเร็จ ต้องซ่อมผลเดิม"}
    if isinstance(post_result, dict) and post_result.get("status") == "ambiguous":
        # Never guess which legacy post row this clip is: nothing was written
        # to the post log; tell the caller which rows need a manual pick.
        product_result["post_log_warning"] = {
            "code": "post_log_ambiguous",
            "detail": "พบประวัติโพสต์เดิมชื่อไฟล์เดียวกันมากกว่า 1 รายการ จึงยังไม่บันทึกลง Post Log กรุณาเลือกโพสต์ที่ถูกต้องเอง",
            "candidate_post_ids": post_result.get("candidate_post_ids") or [],
        }

    # Auto-archive project folder from 03_Projects to 06_Archive/Projects
    target_project_name = None
    if req.product_id and req.angle_id:
        try:
            prod = ProductStore.get(req.product_id, **_kw(channel_id))
            for a in (prod or {}).get("angles", []):
                if (a.get("angle_id") == req.angle_id or a.get("id") == req.angle_id) and a.get("project_name"):
                    target_project_name = a.get("project_name")
                    break
        except Exception:
            pass

    if target_project_name and not superseded_job and posting_job is None:
        try:
            from scripts.project_manifest import ProjectManifest
            from scripts.config import PROJECTS_DIR
            p_folder = PROJECTS_DIR / target_project_name
            if p_folder.exists() and p_folder.is_dir():
                ProjectManifest.archive(target_project_name)
        except Exception as arc_err:
            print(f"[mark_posted] Auto-archive notice: {arc_err}")

    return {"success": True, "moved": moved, **product_result}


@router.get("/api/exports/media-info")
def get_export_media_info(path: str, scope: ChannelScope = Depends(get_channel_scope)):
    """
    Real per-file ffprobe data for the Post Studio spec tiles, fetched
    on-demand for whichever single clip is on screen -- NOT folded into
    list_exports() itself, since ffprobing every export on every gallery
    refresh would add real latency that grows with the export count for a
    property only ever looked at one clip at a time.

    Exists because the spec tiles used to hardcode "1080x1920 (9:16 FHD)" /
    "30 FPS - H.264 MP4" for every clip, which quietly lied for a `_draft`
    720p export.
    """
    target = Path(path)
    if not target.is_absolute():
        target = BASE_DIR / path
    target = target.resolve()

    if not (
        _is_contained(target, EXPORTS_DIR.resolve())
        or _is_contained(target, POSTED_DIR.resolve())
    ):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ไม่ได้อยู่ในโฟลเดอร์ export ที่อนุญาต")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {target.name}")

    channel_id = _channel_of(scope)
    if channel_id is not None:
        # A file registered to another channel -> 404 (lookup raises); an
        # unregistered file only where legacy data belongs to the scope.
        if ExportRegistry.lookup(path=target, channel_id=channel_id) is None and not _legacy_files_allowed(channel_id):
            raise _unregistered_file_error()

    return VideoEditor.get_media_info(str(target))


class EnhanceTikTokRequest(BaseModel):
    export_id: Optional[str] = None
    path: Optional[str] = None


@router.post("/api/exports/enhance-tiktok")
def enhance_export_for_tiktok(
    req: EnhanceTikTokRequest,
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Enhance an exported video with TikTok sharpness optimization (Unsharp + BT.709 + FastStart)."""
    _guard_writable(scope)
    channel_id = _channel_of(scope)

    if not req.export_id and not req.path:
        raise HTTPException(status_code=400, detail="ต้องระบุ export_id หรือ path")

    export_record = None
    if req.export_id:
        export_record = ExportRegistry.get(req.export_id, **_kw(channel_id))
        if export_record is None:
            raise HTTPException(status_code=404, detail="ไม่พบ export_id ในระบบ")
        target = BASE_DIR / export_record["path"]
    else:
        target = Path(req.path)
        if not target.is_absolute():
            target = BASE_DIR / req.path

    target = target.resolve()
    if not (
        _is_contained(target, EXPORTS_DIR.resolve())
        or _is_contained(target, POSTED_DIR.resolve())
    ):
        raise HTTPException(status_code=403, detail="ไฟล์นี้ไม่ได้อยู่ในโฟลเดอร์ export ที่อนุญาต")

    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {target.name}")

    if export_record is None and channel_id is not None:
        export_record = ExportRegistry.lookup(path=target, **_kw(channel_id))
        if export_record is None and not _legacy_files_allowed(channel_id):
            raise _unregistered_file_error()

    from scripts.tiktok_enhancer import enhance_video_for_tiktok

    try:
        enhanced_file = enhance_video_for_tiktok(target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"การปรับปรุงความคมชัดล้มเหลว: {str(e)}")

    rel_path = str(enhanced_file.relative_to(BASE_DIR)).replace("\\", "/")

    new_record = None
    try:
        new_record = ExportRegistry.ensure(
            rel_path,
            product_id=export_record.get("product_id") if export_record else None,
            angle_id=export_record.get("angle_id") if export_record else None,
            project_name=export_record.get("project_name") if export_record else None,
            **_kw(channel_id),
        )
    except Exception as reg_err:
        print(f"[enhance_export_for_tiktok] Warning registering enhanced export: {reg_err}")

    return {
        "success": True,
        "enhanced_path": rel_path,
        "enhanced_filename": enhanced_file.name,
        "size_bytes": enhanced_file.stat().st_size,
        "export_id": (new_record or {}).get("id"),
        "message": "ปรับความคมชัดสำหรับ TikTok สำเร็จเรียบร้อย",
    }


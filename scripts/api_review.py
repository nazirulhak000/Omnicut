"""
Mobile Review Queue, Visual Gate Snapshots API, Proxy 540p Preview,
and Light Script/Timing Editor (Phase 4).
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from scripts import config
from scripts.product_store import ProductStore

router = APIRouter(prefix="/api/review", tags=["MobileReview"])

_LOCK = threading.RLock()

# Configurable paths (can be monkeypatched in tests)
REVIEW_CACHE_DIR: Optional[Path] = None
REVIEW_STATE_FILE: Optional[Path] = None

# Validation regexes for light script editing (Project Rules 7, 20, Phase 0.5)
_PRICE_PATTERN = re.compile(
    r"(?:ราคา|โปรโมชั่น|โปรโมชัน|ส่วนลด|บาท|฿|\b\d[\d,]*\s*บ\.)",
    re.IGNORECASE,
)
_ELLIPSIS_PATTERN = re.compile(r"(\.\.\.|…)")
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)

# Regex patterns to locate #b-cta and extract its data-start timestamp
_B_CTA_TAG_PATTERN = re.compile(
    r"<[a-zA-Z0-9_-]+[^>]*\bid\s*=\s*['\"]b-cta['\"][^>]*>",
    re.IGNORECASE | re.DOTALL,
)
_DATA_START_ATTR_PATTERN = re.compile(
    r"\bdata-start\s*=\s*['\"]([0-9]+(?:\.[0-9]+)?)['\"]",
    re.IGNORECASE,
)


def _get_cache_dir() -> Path:
    if REVIEW_CACHE_DIR is not None:
        base = Path(REVIEW_CACHE_DIR)
    else:
        base = Path(config.PROJECTS_DIR) / ".cache" / "review"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _get_state_file() -> Path:
    if REVIEW_STATE_FILE is not None:
        path = Path(REVIEW_STATE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return _get_cache_dir() / "review_state.json"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def extract_cta_timestamp(
    html_text: str = "",
    timings_data: Optional[Dict[str, Any]] = None,
    fallback: float = 24.5,
) -> float:
    """
    Extract the CTA scene timestamp (`cta_t`) from composition HTML `#b-cta[data-start]`
    or `timings.json`. Guarantees `cta_t > 0.0` so the CTA snapshot is never captured at frame 0.
    """
    if html_text:
        tag_match = _B_CTA_TAG_PATTERN.search(html_text)
        if tag_match:
            attr_match = _DATA_START_ATTR_PATTERN.search(tag_match.group(0))
            if attr_match:
                try:
                    val = float(attr_match.group(1))
                    if val > 0.0:
                        return round(val, 3)
                except (ValueError, TypeError):
                    pass

    if isinstance(timings_data, dict):
        for key in ("cta_t", "cta_start", "b_cta_start", "cta_timestamp"):
            raw = timings_data.get(key)
            if raw is not None:
                try:
                    val = float(raw)
                    if val > 0.0:
                        return round(val, 3)
                except (ValueError, TypeError):
                    pass
        # Check nested elements/clips if present
        elements = timings_data.get("elements") or timings_data.get("clips") or []
        if isinstance(elements, list):
            for el in elements:
                if isinstance(el, dict) and el.get("id") in ("b-cta", "#b-cta"):
                    try:
                        val = float(el.get("start") or el.get("data_start") or 0.0)
                        if val > 0.0:
                            return round(val, 3)
                    except (ValueError, TypeError):
                        pass

    return round(max(0.5, float(fallback or 24.5)), 3)


def _discover_cta_timestamp_for_clip(clip_id: str, record: Dict[str, Any]) -> float:
    """
    Resolve `cta_t` from a clip's composition HTML or timings.json on disk,
    falling back to `record.get("cta_t")` or 24.5s (never 0.0).
    """
    candidates_html: List[Path] = []
    candidates_timings: List[Path] = []

    if record.get("composition_html_path"):
        candidates_html.append(Path(record["composition_html_path"]))
    if record.get("timings_path"):
        candidates_timings.append(Path(record["timings_path"]))

    proj_dir = Path(config.PROJECTS_DIR) / clip_id
    candidates_html.extend([
        proj_dir / "index.html",
        proj_dir / "composition.html",
    ])
    candidates_timings.extend([
        proj_dir / "timings.json",
        proj_dir / "verify.json",
    ])

    html_text = ""
    for hp in candidates_html:
        if hp.is_file():
            try:
                html_text = hp.read_text(encoding="utf-8", errors="ignore")
                if html_text:
                    break
            except OSError:
                pass

    timings_data: Optional[Dict[str, Any]] = None
    for tp in candidates_timings:
        if tp.is_file():
            try:
                loaded = json.loads(tp.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    timings_data = loaded
                    break
            except (OSError, ValueError):
                pass

    existing_cta_t = record.get("cta_t")
    try:
        fallback = float(existing_cta_t) if existing_cta_t and float(existing_cta_t) > 0 else 24.5
    except (ValueError, TypeError):
        fallback = 24.5

    return extract_cta_timestamp(html_text=html_text, timings_data=timings_data, fallback=fallback)


def _render_snapshot_webp(
    clip_id: str,
    kind: str,
    timestamp_sec: float,
    record: Dict[str, Any],
) -> bytes:
    """
    Generate a lightweight 9:16 WebP snapshot (≤80KB) representing either the
    chat frame (`kind == "chat"`) or the CTA frame (`kind == "cta"` at `cta_t`).
    """
    from PIL import Image, ImageDraw

    width, height = 270, 480
    bg_color = (242, 236, 224) if kind == "chat" else (235, 245, 232)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Header bar
    header_color = (34, 42, 58) if kind == "chat" else (22, 101, 52)
    draw.rectangle([0, 0, width, 56], fill=header_color)
    draw.text((14, 18), f"{clip_id} [{kind.upper()}]", fill=(255, 255, 255))

    turns = record.get("turns") or []
    y = 76
    if kind == "chat":
        for idx, turn in enumerate(turns[:4]):
            speaker = str(turn.get("speaker") or ("Nui" if idx % 2 == 0 else "Bao"))
            is_right = speaker in ("พี่บ่าว", "bao", "male", "B")
            bubble_bg = (141, 224, 122) if is_right else (255, 255, 255)
            x0 = 46 if is_right else 14
            x1 = width - 14 if is_right else width - 46
            draw.rounded_rectangle([x0, y, x1, y + 64], radius=12, fill=bubble_bg, outline=(200, 200, 200))
            snippet = str(turn.get("display") or "")[:24]
            draw.text((x0 + 10, y + 22), snippet.encode("ascii", "replace").decode("ascii"), fill=(20, 20, 20))
            y += 78
    else:
        # CTA card visual
        draw.rounded_rectangle([18, 96, width - 18, 360], radius=18, fill=(255, 255, 255), outline=(34, 197, 94), width=3)
        draw.rectangle([34, 124, width - 34, 230], fill=(226, 232, 240))
        draw.rounded_rectangle([34, 290, width - 34, 340], radius=10, fill=(22, 163, 74))
        draw.text((54, 308), f"CTA @ {timestamp_sec:.2f}s", fill=(255, 255, 255))

    # Footer metadata strip
    draw.rectangle([0, height - 38, width, height], fill=(15, 23, 42))
    offset = float(record.get("timing_offset_sec") or 0.0)
    rev = int(record.get("revision") or 1)
    draw.text(
        (12, height - 26),
        f"t={timestamp_sec:.2f}s | off={offset:+.1f}s | r{rev}",
        fill=(148, 163, 184),
    )

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=78, method=4)
    return buf.getvalue()


def _normalize_turns(raw_turns: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not isinstance(raw_turns, list):
        return normalized
    for idx, t in enumerate(raw_turns):
        if not isinstance(t, dict):
            continue
        speaker = str(t.get("speaker") or ("น้องนุ้ย" if idx % 2 == 0 else "พี่บ่าว"))
        # Support either flat {display, spoken} or nested phrases[{display, spoken}]
        display = t.get("display")
        spoken = t.get("spoken")
        phrases = t.get("phrases")
        if (display is None or spoken is None) and isinstance(phrases, list) and phrases:
            if display is None:
                display = " ".join(str(p.get("display") or "") for p in phrases if isinstance(p, dict)).strip()
            if spoken is None:
                spoken = " ".join(str(p.get("spoken") or p.get("display") or "") for p in phrases if isinstance(p, dict)).strip()
        display_str = str(display if display is not None else (spoken or "")).strip()
        spoken_str = str(spoken if spoken is not None else display_str).strip()
        photo = t.get("photo")
        normalized.append({
            "speaker": speaker,
            "display": display_str,
            "spoken": spoken_str,
            "photo": str(photo) if photo else None,
        })
    return normalized


def _normalize_clip_record(clip_id: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    qc_status = str(raw.get("qc_status") or "pending").lower()
    if qc_status not in ("pending", "passed", "rejected"):
        qc_status = "pending"

    cta_t = _discover_cta_timestamp_for_clip(clip_id, raw)
    try:
        timing_offset = round(float(raw.get("timing_offset_sec") or 0.0), 2)
    except (ValueError, TypeError):
        timing_offset = 0.0
    timing_offset = max(-2.0, min(2.0, timing_offset))

    try:
        revision = max(1, int(raw.get("revision") or 1))
    except (ValueError, TypeError):
        revision = 1

    turns = _normalize_turns(raw.get("turns") or [])
    available_photos = [
        str(p) for p in (raw.get("available_photos") or raw.get("photos") or []) if p
    ]
    for turn in turns:
        if turn.get("photo") and turn["photo"] not in available_photos:
            available_photos.append(turn["photo"])

    return {
        "clip_id": clip_id,
        "product_id": raw.get("product_id"),
        "product_code": str(raw.get("product_code") or "UNKNOWN"),
        "angle_id": str(raw.get("angle_id") or clip_id),
        "title": str(raw.get("title") or clip_id),
        "qc_status": qc_status,
        "qc_note": raw.get("qc_note"),
        "chat_snapshot_url": f"/api/review/{clip_id}/snapshots/chat?r={revision}",
        "cta_snapshot_url": f"/api/review/{clip_id}/snapshots/cta?r={revision}",
        "proxy_video_url": str(
            raw.get("proxy_video_url") or f"/api/proxy/for-clip?clip_id={clip_id}"
        ),
        "cta_t": cta_t,
        "timing_offset_sec": timing_offset,
        "turns": turns,
        "available_photos": available_photos,
        "revision": revision,
        "rerender_job_id": raw.get("rerender_job_id"),
        "composition_html_path": raw.get("composition_html_path"),
        "timings_path": raw.get("timings_path"),
        "updated_at": raw.get("updated_at") or _now_iso(),
    }


def _load_state() -> Dict[str, Dict[str, Any]]:
    with _LOCK:
        state_file = _get_state_file()
        records: Dict[str, Dict[str, Any]] = {}
        if state_file.is_file():
            try:
                raw = json.loads(state_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    items = raw.get("clips") if "clips" in raw and isinstance(raw["clips"], dict) else raw
                    if isinstance(items, dict):
                        for cid, rec in items.items():
                            if isinstance(rec, dict):
                                records[str(cid)] = _normalize_clip_record(str(cid), rec)
                    elif isinstance(items, list):
                        for rec in items:
                            if isinstance(rec, dict) and rec.get("clip_id"):
                                cid = str(rec["clip_id"])
                                records[cid] = _normalize_clip_record(cid, rec)
            except (OSError, ValueError):
                pass

        # Also sync from ProductStore if angles have rendered clips not yet in state
        try:
            products = ProductStore.get_all()
        except Exception:
            products = []

        for prod in products:
            if not isinstance(prod, dict):
                continue
            p_code = str(prod.get("product_code") or prod.get("code") or prod.get("id") or "PROD")
            p_id = prod.get("id")
            p_photos = [str(x) for x in (prod.get("photos") or prod.get("images") or []) if x]
            for angle in prod.get("angles") or []:
                if not isinstance(angle, dict):
                    continue
                status = str(angle.get("status") or "")
                video_url = angle.get("video_url")
                project_name = angle.get("project_name")
                if status not in ("rendered", "ready_to_post", "in_review") and not video_url and not project_name:
                    continue
                cid = str(angle.get("clip_id") or project_name or f"{p_code}_{angle.get('id') or '1'}")
                if cid in records:
                    continue
                if angle.get("qc_reviewed"):
                    qc_stat = "passed"
                elif angle.get("qc_note"):
                    qc_stat = "rejected"
                else:
                    qc_stat = "pending"
                records[cid] = _normalize_clip_record(
                    cid,
                    {
                        "clip_id": cid,
                        "product_id": p_id,
                        "product_code": p_code,
                        "angle_id": str(angle.get("id") or cid),
                        "title": str(angle.get("title") or angle.get("hook") or cid),
                        "qc_status": qc_stat,
                        "qc_note": angle.get("qc_note"),
                        "proxy_video_url": f"/api/proxy/for-clip?clip_id={cid}",
                        "turns": angle.get("turns") or [],
                        "available_photos": p_photos,
                        "revision": int(angle.get("revision") or 1),
                    },
                )
        return records


def _save_state(records: Dict[str, Dict[str, Any]]) -> None:
    with _LOCK:
        state_file = _get_state_file()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = state_file.with_suffix(".json.tmp")
        payload = {"clips": records, "updated_at": _now_iso()}
        tmp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_file.replace(state_file)


def upsert_review_clip(clip_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a clip in the review state store."""
    with _LOCK:
        cid = str(clip_data.get("clip_id") or "").strip()
        if not cid:
            raise ValueError("clip_id is required")
        records = _load_state()
        merged = dict(records.get(cid) or {})
        merged.update(clip_data)
        normalized = _normalize_clip_record(cid, merged)
        records[cid] = normalized
        _save_state(records)
        return normalized


def seed_review_clips(clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replace or seed multiple clips into the review queue."""
    with _LOCK:
        records = _load_state()
        out: List[Dict[str, Any]] = []
        for item in clips:
            cid = str(item.get("clip_id") or "").strip()
            if not cid:
                continue
            normalized = _normalize_clip_record(cid, item)
            records[cid] = normalized
            out.append(normalized)
        _save_state(records)
        return out


def _sync_decision_to_product_store(record: Dict[str, Any], decision: str, note: Optional[str]) -> None:
    """Best-effort sync of review decision back to ProductStore angle status."""
    product_id = record.get("product_id")
    angle_id = record.get("angle_id")
    if not product_id or not angle_id:
        return
    try:
        if decision == "pass":
            ProductStore.update_angle_status(
                str(product_id),
                str(angle_id),
                status="ready_to_post",
                mark_qc_passed=True,
                clear_qc_note=True,
            )
        else:
            ProductStore.update_angle_status(
                str(product_id),
                str(angle_id),
                status="rendered",
                qc_note=note or "ตีกลับจากคิวตรวจมือถือ",
                mark_qc_passed=False,
            )
    except Exception:
        pass


def _generate_snapshots_for_record(clip_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    cta_t = _discover_cta_timestamp_for_clip(clip_id, record)
    record["cta_t"] = cta_t
    chat_t = round(min(4.0, max(1.2, cta_t * 0.2)), 2)

    clip_cache_dir = _get_cache_dir() / clip_id
    clip_cache_dir.mkdir(parents=True, exist_ok=True)

    chat_bytes = _render_snapshot_webp(clip_id, "chat", chat_t, record)
    cta_bytes = _render_snapshot_webp(clip_id, "cta", cta_t, record)

    chat_path = clip_cache_dir / "chat.webp"
    cta_path = clip_cache_dir / "cta.webp"
    chat_path.write_bytes(chat_bytes)
    cta_path.write_bytes(cta_bytes)

    rev = int(record.get("revision") or 1)
    return {
        "clip_id": clip_id,
        "chat_t": chat_t,
        "cta_t": cta_t,
        "chat_snapshot_url": f"/api/review/{clip_id}/snapshots/chat?r={rev}",
        "cta_snapshot_url": f"/api/review/{clip_id}/snapshots/cta?r={rev}",
        "chat_webp_path": str(chat_path),
        "cta_webp_path": str(cta_path),
    }


def _validate_display_text(text: str) -> None:
    cleaned = (text or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="display_text_empty")
    if _PRICE_PATTERN.search(cleaned):
        raise HTTPException(status_code=422, detail="display_contains_forbidden_price")
    if _ELLIPSIS_PATTERN.search(cleaned):
        raise HTTPException(status_code=422, detail="display_contains_ellipsis")
    if _EMOJI_PATTERN.search(cleaned):
        raise HTTPException(status_code=422, detail="display_contains_emoji")


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class SnapshotRequest(BaseModel):
    html: Optional[str] = None
    timings: Optional[Dict[str, Any]] = None


class DecisionRequest(BaseModel):
    decision: str = Field(..., description="'pass' or 'reject'")
    note: Optional[str] = Field(default="")
    seen: bool = Field(default=False)


class BatchApproveSeenRequest(BaseModel):
    seen_clip_ids: List[str] = Field(default_factory=list)


class TurnLightEditItem(BaseModel):
    index: Optional[int] = None
    speaker: Optional[str] = None
    display: Optional[str] = None
    spoken: Optional[str] = None
    photo: Optional[str] = None


class LightScriptPatchRequest(BaseModel):
    turns: Optional[List[TurnLightEditItem]] = None
    timing_offset_sec: Optional[float] = None
    timing_delta_sec: Optional[float] = None
    base_revision: Optional[int] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/queue")
def get_review_queue(
    product_code: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """
    Return the list of clips for mobile review, optionally filtered by
    `product_code` and `status` (`pending` | `passed` | `rejected` | `all`).
    """
    records = _load_state()
    items = list(records.values())

    if product_code and product_code.strip().lower() not in ("all", "*"):
        target_code = product_code.strip().upper()
        items = [c for c in items if str(c.get("product_code") or "").upper() == target_code]

    if status and status.strip().lower() not in ("all", "*"):
        target_status = status.strip().lower()
        items = [c for c in items if str(c.get("qc_status") or "pending").lower() == target_status]

    return items


@router.post("/{clip_id}/snapshots")
def generate_clip_snapshots(
    clip_id: str,
    payload: Optional[SnapshotRequest] = None,
) -> Dict[str, Any]:
    """
    Generate or refresh `chat.webp` and `cta.webp` under `03_Projects/.cache/review/{clip_id}/`.
    Extracts `#b-cta[data-start]` from the composition HTML or `timings.json` so the CTA
    snapshot is captured at the real `cta_t` timestamp, never at frame 0.
    """
    with _LOCK:
        records = _load_state()
        record = records.get(clip_id)
        if record is None:
            record = _normalize_clip_record(clip_id, {"clip_id": clip_id})

        if payload and (payload.html or payload.timings):
            cta_t = extract_cta_timestamp(
                html_text=payload.html or "",
                timings_data=payload.timings,
                fallback=float(record.get("cta_t") or 24.5),
            )
            record["cta_t"] = cta_t

        snap_info = _generate_snapshots_for_record(clip_id, record)
        record["cta_t"] = snap_info["cta_t"]
        record["updated_at"] = _now_iso()
        records[clip_id] = record
        _save_state(records)
        return snap_info


@router.get("/{clip_id}/snapshots/{kind}")
def get_clip_snapshot(
    clip_id: str,
    kind: str,
    request: Request,
) -> Response:
    """
    Serve the cached WebP snapshot (`chat` or `cta`) with `Cache-Control` and `ETag`.
    """
    norm_kind = (kind or "").strip().lower()
    if norm_kind not in ("chat", "cta"):
        raise HTTPException(status_code=422, detail="invalid_snapshot_kind")

    clip_cache_dir = _get_cache_dir() / clip_id
    webp_path = clip_cache_dir / f"{norm_kind}.webp"

    if not webp_path.is_file():
        with _LOCK:
            records = _load_state()
            record = records.get(clip_id)
            if record is None:
                raise HTTPException(status_code=404, detail="clip_not_found")
            _generate_snapshots_for_record(clip_id, record)
            records[clip_id] = record
            _save_state(records)

    if not webp_path.is_file():
        raise HTTPException(status_code=404, detail="snapshot_not_found")

    data = webp_path.read_bytes()
    etag = f'"{hashlib.sha256(data).hexdigest()[:24]}"'
    headers = {
        "Cache-Control": "public, max-age=60, must-revalidate",
        "ETag": etag,
    }

    inm = request.headers.get("if-none-match")
    if inm and inm.strip() == etag:
        return Response(status_code=304, headers=headers)

    return Response(content=data, media_type="image/webp", headers=headers)


@router.post("/{clip_id}/decision")
def submit_clip_decision(
    clip_id: str,
    payload: DecisionRequest,
) -> Dict[str, Any]:
    """
    Record a review decision (`pass` or `reject`) for a clip.
    - Requires `seen == True` (cannot approve or reject without viewing the card).
    - Requires non-empty `note` when `decision == "reject"`.
    """
    decision = (payload.decision or "").strip().lower()
    if decision not in ("pass", "reject"):
        raise HTTPException(status_code=422, detail="invalid_decision")

    if not payload.seen:
        raise HTTPException(status_code=422, detail="seen_required_before_decision")

    clean_note = (payload.note or "").strip()
    if decision == "reject" and not clean_note:
        raise HTTPException(status_code=422, detail="reject_note_required")

    with _LOCK:
        records = _load_state()
        record = records.get(clip_id)
        if record is None:
            raise HTTPException(status_code=404, detail="clip_not_found")

        record["qc_status"] = "passed" if decision == "pass" else "rejected"
        record["qc_note"] = clean_note if clean_note else (None if decision == "pass" else clean_note)
        record["revision"] = int(record.get("revision") or 1) + 1
        record["updated_at"] = _now_iso()
        records[clip_id] = _normalize_clip_record(clip_id, record)
        _save_state(records)

        _sync_decision_to_product_store(records[clip_id], decision, clean_note)
        return records[clip_id]


@router.post("/batch-approve-seen")
def batch_approve_seen(payload: BatchApproveSeenRequest) -> Dict[str, Any]:
    """
    Approve ONLY the clips explicitly listed in `seen_clip_ids`.
    Never approves unseen clips.
    """
    seen_ids = [str(cid).strip() for cid in (payload.seen_clip_ids or []) if str(cid).strip()]
    seen_set = set(seen_ids)

    with _LOCK:
        records = _load_state()
        approved_ids: List[str] = []
        for cid in seen_ids:
            record = records.get(cid)
            if record is None:
                continue
            if record.get("qc_status") == "rejected":
                continue
            record["qc_status"] = "passed"
            record["qc_note"] = None
            record["revision"] = int(record.get("revision") or 1) + 1
            record["updated_at"] = _now_iso()
            records[cid] = _normalize_clip_record(cid, record)
            _sync_decision_to_product_store(records[cid], "pass", None)
            approved_ids.append(cid)

        unseen_count = sum(1 for cid in records if cid not in seen_set)
        _save_state(records)

        return {
            "approved_clip_ids": approved_ids,
            "approved_count": len(approved_ids),
            "skipped_unseen_count": unseen_count,
        }


@router.patch("/{clip_id}/script")
def light_edit_clip_script(
    clip_id: str,
    payload: LightScriptPatchRequest,
) -> Dict[str, Any]:
    """
    Light edit endpoint for a clip:
    - Updates `turns[i].display` (validates no price, no ellipsis, no emoji).
    - Strictly locks `turns[i].spoken` (returns 400 `spoken_locked_in_light_edit` if mutated).
    - Allows changing `turns[i].photo` from `available_photos`.
    - Adjusts `timing_offset_sec` in steps of ±0.1s (clamped to [-2.0, 2.0]).
    - Queues a single-clip re-render job (`rerender_job_id`) and increments `revision`.
    """
    with _LOCK:
        records = _load_state()
        record = records.get(clip_id)
        if record is None:
            raise HTTPException(status_code=404, detail="clip_not_found")

        current_rev = int(record.get("revision") or 1)
        if payload.base_revision is not None and int(payload.base_revision) != current_rev:
            raise HTTPException(status_code=409, detail="revision_conflict")

        turns = [dict(t) for t in (record.get("turns") or [])]
        available_photos = list(record.get("available_photos") or [])

        if payload.turns is not None:
            for item_idx, patch_turn in enumerate(payload.turns):
                target_idx = patch_turn.index if patch_turn.index is not None else item_idx
                if target_idx < 0 or target_idx >= len(turns):
                    raise HTTPException(status_code=422, detail=f"turn_index_out_of_range:{target_idx}")

                existing_turn = turns[target_idx]

                # Strictly lock spoken text so TTS audio stays 100% in sync
                if patch_turn.spoken is not None and patch_turn.spoken.strip() != str(existing_turn.get("spoken") or "").strip():
                    raise HTTPException(status_code=400, detail="spoken_locked_in_light_edit")

                if patch_turn.display is not None:
                    _validate_display_text(patch_turn.display)
                    existing_turn["display"] = patch_turn.display.strip()

                if patch_turn.photo is not None:
                    new_photo = patch_turn.photo.strip() if patch_turn.photo else None
                    if new_photo and available_photos and new_photo not in available_photos:
                        raise HTTPException(status_code=422, detail="photo_not_in_available_photos")
                    existing_turn["photo"] = new_photo

                turns[target_idx] = existing_turn

        current_offset = float(record.get("timing_offset_sec") or 0.0)
        if payload.timing_offset_sec is not None:
            next_offset = float(payload.timing_offset_sec)
        elif payload.timing_delta_sec is not None:
            next_offset = current_offset + float(payload.timing_delta_sec)
        else:
            next_offset = current_offset

        # Quantize to 0.1s steps and clamp to [-2.0, 2.0]
        quantized_offset = round(round(next_offset * 10.0) / 10.0, 1)
        quantized_offset = max(-2.0, min(2.0, quantized_offset))
        if quantized_offset == -0.0:
            quantized_offset = 0.0

        next_rev = current_rev + 1
        rerender_job_id = f"rerender_{clip_id}_v{next_rev}_{uuid.uuid4().hex[:6]}"

        record["turns"] = turns
        record["timing_offset_sec"] = quantized_offset
        record["revision"] = next_rev
        record["rerender_job_id"] = rerender_job_id
        record["qc_status"] = "pending"
        record["updated_at"] = _now_iso()

        normalized = _normalize_clip_record(clip_id, record)
        _generate_snapshots_for_record(clip_id, normalized)
        records[clip_id] = normalized
        _save_state(records)

        return normalized

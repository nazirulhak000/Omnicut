"""
Recording-session storage and finalization for the guided-take filming
feature. A session is created from an already-generated shot list
(scripts/shot_list_builder.py) and tracks one segment per beat, uploaded
progressively from the mobile filming page, in strict order -- only the
most-recently-uploaded segment may be retaken. Finalizing normalizes and
concatenates the segments into one raw video, tagged with a
`.guided_take.json` sidecar the render pipeline's ShotMatchingStage reads to
map footage onto script beats exactly, without AI vision.

See C:\\Users\\Winon\\.claude\\plans\\cheeky-cooking-quokka.md (Phase B).
"""

from __future__ import annotations

import datetime
import json
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.config import BASE_DIR, RAW_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS
from scripts.db import DocumentTable
from scripts.video_editor import VideoEditor
from scripts.media_service import get_file_info
from scripts.product_store import ProductStore
from scripts.shot_lists_store import ShotListsStore

STORE_PATH = BASE_DIR / "_Docs" / "recording_sessions.json"

# A session lingers well past a single sitting -- the user might film half a
# product, close the tab, and come back the next day -- so this is a display
# hint (surfaced by the API, not enforced as a hard cutoff by finalize/upload
# below) rather than something that blocks a legitimately late continuation.
_SESSION_TTL_HOURS = 48

_TERMINAL_STATUSES = ("completed", "cancelled", "expired")


def _store_db_path() -> Path:
    return STORE_PATH.parent / "store.db"


def _store_json_path() -> Path:
    return STORE_PATH


_TABLE = DocumentTable("recording_sessions", _store_db_path, _store_json_path)


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _safe_product_dir(base_dir: Path, product_id: str) -> Path:
    """Same containment check as scripts/api_videos.py's _safe_product_dir
    (duplicated rather than imported to keep this module free of a circular
    import back into the videos router)."""
    resolved_base = base_dir.resolve()
    candidate = (base_dir / product_id).resolve()
    try:
        candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise ValueError(f"product_id ไม่ถูกต้อง: {product_id!r}") from exc
    return candidate


def _ffprobe_duration(path: Path) -> float:
    info = VideoEditor.get_media_info(str(path))
    duration = float(info.get("duration") or 0.0)
    if duration <= 0:
        raise ValueError(f"ตรวจสอบความยาวไฟล์ไม่สำเร็จหรือไฟล์เสียหาย: {path}")
    return duration


def _normalize_segment(src: Path, dest: Path) -> None:
    """Re-encodes one recorded segment to a common codec/resolution/fps so
    every segment shares identical params before the stream-copy concat
    below -- mobile browsers across different MediaRecorder sessions (and
    especially different devices/OSes) are not guaranteed to produce
    concat-compatible files otherwise."""
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf",
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=120)
    if result.returncode != 0 or not dest.exists():
        raise ValueError(f"แปลงไฟล์วิดีโอไม่สำเร็จ ({src.name}): {(result.stderr or '')[-500:]}")


class RecordingSessionStore:
    """Keyed by session id (`secrets.token_urlsafe(16)`, same minting
    convention as scripts/task_manager.py's task ids)."""

    @staticmethod
    def _now() -> str:
        return _now_iso()

    @staticmethod
    def _expires_at(created_at_iso: str) -> str:
        created = datetime.datetime.fromisoformat(created_at_iso.rstrip("Z"))
        return (created + datetime.timedelta(hours=_SESSION_TTL_HOURS)).isoformat() + "Z"

    @classmethod
    def get(cls, session_id: str) -> Optional[Dict[str, Any]]:
        for record in _TABLE.load():
            if record.get("id") == session_id:
                return record
        return None

    @classmethod
    def create(cls, product_id: str, angle_id: str, batch: int = 1) -> Dict[str, Any]:
        shot_list_record = ShotListsStore.get(product_id, angle_id)
        if not shot_list_record:
            raise ValueError(f"ยังไม่มีแผนถ่ายสำหรับมุม '{angle_id}' -- กรุณาสร้างแผนถ่ายก่อน")
        shot_list = shot_list_record.get("shot_list") or []
        if not shot_list:
            raise ValueError(f"แผนถ่ายของมุม '{angle_id}' ว่างเปล่า")

        with _TABLE.mutate() as records:
            # Reopening the same QR link resumes existing session ONLY if the
            # shot plan has not changed. If beats changed, expire old session.
            for existing in records:
                if (
                    existing.get("product_id") == product_id
                    and existing.get("angle_id") == angle_id
                    and existing.get("status") not in _TERMINAL_STATUSES
                ):
                    if len(existing.get("segments") or []) == len(shot_list):
                        return existing
                    # Script or shot structure changed -> expire stale session
                    existing["status"] = "expired"
                    existing["expired_reason"] = "script_revision_changed"
                    existing["updated_at"] = cls._now()
                    break

            now = cls._now()
            session = {
                "id": secrets.token_urlsafe(16),
                "product_id": product_id,
                "angle_id": angle_id,
                "shot_list_key": f"{product_id}:{angle_id}",
                "status": "pending",
                "segments": [
                    {
                        "beat_index": beat["beat_index"],
                        "role": beat["role"],
                        "planned_start": beat["start"],
                        "planned_end": beat["end"],
                        "planned_duration": beat["planned_duration"],
                        "is_separate_clip": bool(beat.get("is_separate_clip")),
                        "status": "pending",
                        "raw_file_path": None,
                        "probed_duration": None,
                        "uploaded_at": None,
                    }
                    for beat in shot_list
                ],
                "raw_video_path": None,
                "clip_map": None,
                "created_at": now,
                "updated_at": now,
                "expires_at": cls._expires_at(now),
            }
            records.append(session)
            return session

    @classmethod
    def _next_pending_index(cls, segments: List[Dict[str, Any]]) -> Optional[int]:
        return next((i for i, s in enumerate(segments) if s["status"] != "uploaded"), None)

    @classmethod
    def upload_segment(
        cls, session_id: str, beat_index: int, raw_file_path: str, probed_duration: float
    ) -> Dict[str, Any]:
        with _TABLE.mutate() as records:
            session = next((r for r in records if r.get("id") == session_id), None)
            if not session:
                raise ValueError(f"ไม่พบเซสชันถ่ายทำ id '{session_id}'")
            if session.get("status") in _TERMINAL_STATUSES:
                raise ValueError("เซสชันนี้ปิดแล้ว ไม่สามารถอัปโหลดเพิ่มได้")

            segments = session["segments"]
            expected = cls._next_pending_index(segments)
            if expected is None:
                raise ValueError("ถ่ายครบทุกช็อตแล้ว")
            if beat_index != expected:
                raise ValueError(
                    f"ต้องถ่ายตามลำดับ ตอนนี้รอช็อตที่ {expected + 1} อยู่ "
                    "ไม่สามารถข้ามหรือแก้ไขช็อตก่อนหน้าได้"
                )

            segments[beat_index].update({
                "status": "uploaded",
                "raw_file_path": raw_file_path,
                "probed_duration": probed_duration,
                "uploaded_at": cls._now(),
            })
            session["status"] = "recording"
            session["updated_at"] = cls._now()
            return session

    @classmethod
    def delete_segment(cls, session_id: str, beat_index: int) -> Tuple[Dict[str, Any], Optional[str]]:
        """Retake: only the most-recently-uploaded segment may be removed,
        so the on-screen product state a later beat's footage already
        depends on can never be invalidated by rewinding an earlier one.
        Returns the updated session and the now-orphaned file path (if any)
        so the caller can unlink it outside this transaction."""
        with _TABLE.mutate() as records:
            session = next((r for r in records if r.get("id") == session_id), None)
            if not session:
                raise ValueError(f"ไม่พบเซสชันถ่ายทำ id '{session_id}'")
            if session.get("status") in _TERMINAL_STATUSES:
                raise ValueError("เซสชันนี้ปิดแล้ว ไม่สามารถย้อนถ่ายได้")

            segments = session["segments"]
            uploaded = [i for i, s in enumerate(segments) if s["status"] == "uploaded"]
            if not uploaded or beat_index != max(uploaded):
                raise ValueError("ย้อนถ่ายได้เฉพาะช็อตล่าสุดที่ถ่ายไปเท่านั้น")

            removed_path = segments[beat_index].get("raw_file_path")
            segments[beat_index].update({
                "status": "pending",
                "raw_file_path": None,
                "probed_duration": None,
                "uploaded_at": None,
            })
            session["updated_at"] = cls._now()
            return session, removed_path

    @classmethod
    def finalize(cls, session_id: str) -> Dict[str, Any]:
        session = cls.get(session_id)
        if not session:
            raise ValueError(f"ไม่พบเซสชันถ่ายทำ id '{session_id}'")
        segments = session["segments"]
        if any(s["status"] != "uploaded" for s in segments):
            raise ValueError("ถ่ายไม่ครบทุกช็อต")

        product_id = session["product_id"]
        dest_dir = _safe_product_dir(RAW_DIR, product_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        work_dir = Path(tempfile.mkdtemp(prefix=f"guided_take_{session_id}_"))
        try:
            normalized_paths: List[Path] = []
            for seg in segments:
                src = Path(seg["raw_file_path"])
                norm_path = work_dir / f"seg_{seg['beat_index']:03d}.mp4"
                _normalize_segment(src, norm_path)
                normalized_paths.append(norm_path)

            durations = [_ffprobe_duration(p) for p in normalized_paths]

            concat_list = work_dir / "concat_list.txt"
            concat_list.write_text(
                "\n".join(f"file '{p.as_posix()}'" for p in normalized_paths), encoding="utf-8"
            )

            timestamp = int(time.time())
            out_path = dest_dir / f"guided_take_{timestamp}.mp4"
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list), "-c", "copy", str(out_path),
            ]
            result = subprocess.run(
                concat_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=120
            )
            if result.returncode != 0 or not out_path.exists():
                raise ValueError(f"ต่อคลิปไม่สำเร็จ: {(result.stderr or '')[-500:]}")

            clip_map = []
            cursor = 0.0
            for seg, dur in zip(segments, durations):
                clip_map.append({
                    "beat_index": seg["beat_index"],
                    "role": seg["role"],
                    "trim_start": round(cursor, 3),
                    "trim_end": round(cursor + dur, 3),
                    "actual_duration": round(dur, 3),
                    "planned_duration": seg["planned_duration"],
                })
                cursor += dur

            sidecar_path = out_path.with_name(out_path.name + ".guided_take.json")
            sidecar_path.write_text(
                json.dumps({
                    "session_id": session_id,
                    "product_id": product_id,
                    "angle_id": session["angle_id"],
                    "clip_map": clip_map,
                    "created_at": cls._now(),
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            file_info = get_file_info(out_path)
            file_info["source"] = "guided_take"
            file_info["recording_session_id"] = session_id
            try:
                ProductStore.add_video_to_product(product_id, file_info)
            except Exception as e:
                # Mirrors scripts/api_videos.py's own upload endpoint: failing
                # to link the video into the product record is not a reason
                # to fail a render-ready file that's already safely on disk.
                print(f"Warning: Failed to attach guided-take video to product {product_id}: {e}")

            try:
                # This footage was shot beat-for-beat against this exact
                # angle's shot list -- auto-select it as the angle's clip
                # (replacing any prior selection) so the user isn't left
                # having to dig it out of the raw-footage picker manually,
                # and so source_resolution.py resolves to THIS file (the one
                # with the matching .guided_take.json sidecar) rather than
                # some other clip that happens to also be selected.
                ProductStore.update_angle_videos(product_id, session["angle_id"], [str(out_path)])
            except Exception as e:
                print(f"Warning: Failed to auto-select guided-take video for angle {session['angle_id']}: {e}")

            with _TABLE.mutate() as records:
                rec = next((r for r in records if r.get("id") == session_id), None)
                if rec:
                    rec["status"] = "completed"
                    rec["raw_video_path"] = str(out_path)
                    rec["clip_map"] = clip_map
                    rec["updated_at"] = cls._now()

            # The per-beat raw segments are now fully consumed into out_path
            # -- keeping them around served no purpose except leaving stray
            # working files behind (they all share one session-scoped
            # directory, scripts/api_recording.py's _SEGMENTS_DIR / session_id).
            first_raw_path = segments[0].get("raw_file_path")
            if first_raw_path:
                shutil.rmtree(Path(first_raw_path).parent, ignore_errors=True)

            return {"raw_video_path": str(out_path), "clip_map": clip_map}
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

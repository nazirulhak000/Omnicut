"""
Flow Service: Coordinates video generation with Google Flow via flow-mcp,
persists job records, and automates video ingestion into 01_Raw/<product_id>/AI_Flow.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR, RAW_DIR
from scripts.flow_client import FlowClient, get_flow_client

logger = logging.getLogger("omnicut.flow_service")

FLOW_JOBS_FILE = BASE_DIR / "_Docs" / "flow_jobs.json"


class FlowJobStore:
    """Thread-safe JSON store for Flow generation jobs."""

    @staticmethod
    def _now_iso() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    @classmethod
    def load(cls) -> Dict[str, Any]:
        if not FLOW_JOBS_FILE.exists():
            return {"jobs": {}}
        try:
            return json.loads(FLOW_JOBS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Error loading flow_jobs.json: {e}, resetting to empty.")
            return {"jobs": {}}

    @classmethod
    def save(cls, data: Dict[str, Any]) -> None:
        FLOW_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = FLOW_JOBS_FILE.with_suffix(f".tmp.{uuid.uuid4().hex[:6]}")
        tmp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_file.replace(FLOW_JOBS_FILE)

    @classmethod
    def create_job(cls, product_id: str, project_name: str, scenes: List[Dict[str, Any]], client_job_ids: List[str]) -> Dict[str, Any]:
        data = cls.load()
        job_id = f"flow_job_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        record = {
            "id": job_id,
            "product_id": product_id,
            "project_name": project_name,
            "client_job_ids": client_job_ids,
            "scenes": scenes,
            "status": "queued",
            "created_at": cls._now_iso(),
            "updated_at": cls._now_iso(),
            "results": [],
            "ingested_files": [],
            "error": None,
        }
        data["jobs"][job_id] = record
        cls.save(data)
        return record

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        data = cls.load()
        return data["jobs"].get(job_id)

    @classmethod
    def update_job(cls, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = cls.load()
        if job_id not in data["jobs"]:
            return None
        job = data["jobs"][job_id]
        job.update(updates)
        job["updated_at"] = cls._now_iso()
        cls.save(data)
        return job

    @classmethod
    def list_jobs(cls, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = cls.load()
        jobs = list(data["jobs"].values())
        if product_id:
            jobs = [j for j in jobs if j.get("product_id") == product_id]
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return jobs


class FlowService:
    _active_pollers: Dict[str, threading.Thread] = {}
    _poller_lock: threading.Lock = threading.Lock()

    def __init__(self, client: Optional[FlowClient] = None):
        self.client = client or get_flow_client()

    def get_status(self, detailed: bool = False, auto_start: bool = True) -> Dict[str, Any]:
        """Returns the status of flow-mcp service and Google Flow connection."""
        is_healthy = self.client.is_healthy()
        if not is_healthy and auto_start:
            # Auto-start headless daemon
            self.client.ensure_service_running(timeout=3.5)
            is_healthy = self.client.is_healthy()

        if not is_healthy:
            return {
                "service_online": False,
                "hint": "flow-mcp service is not running on port 8787. You can launch it via tools/flow-mcp or API.",
                "signedIn": False,
                "inProject": False,
                "credits_remaining": 0,
            }
        try:
            flow_state = self.client.get_status(detailed=detailed)
            return {
                "service_online": True,
                **flow_state,
            }
        except Exception as e:
            return {
                "service_online": True,
                "error": str(e),
                "signedIn": False,
                "inProject": False,
                "credits_remaining": 0,
            }

    def submit_generation(
        self,
        product_id: str,
        scenes: List[Dict[str, Any]],
        project_name: Optional[str] = None,
        auto_poll: bool = True,
    ) -> Dict[str, Any]:
        """
        Submits scenes to flow-mcp, registers the job in FlowJobStore,
        and starts asynchronous background poller.
        """
        if not scenes:
            raise ValueError("ต้องระบุฉากอย่างน้อย 1 ฉาก (scenes cannot be empty)")

        self.client.ensure_service_running()
        proj_name = project_name or f"Omni_{product_id[:8]}"
        res = self.client.generate(project=proj_name, scenes=scenes)

        client_job_ids = res.get("job_ids", [])
        if not client_job_ids and "task_id" in res:
            client_job_ids = [res["task_id"]]
        if not client_job_ids and "jobs" in res:
            client_job_ids = [j["id"] for j in res["jobs"] if isinstance(j, dict) and "id" in j]

        job = FlowJobStore.create_job(
            product_id=product_id,
            project_name=proj_name,
            scenes=scenes,
            client_job_ids=client_job_ids,
        )

        if auto_poll:
            self.start_background_poller(job["id"])

        return {"job": job, "flow_response": res}

    def dispatch_batch_generation(
        self,
        product_id: str,
        shots: List[Dict[str, Any]],
        project_name: Optional[str] = None,
        auto_bundle: bool = True,
    ) -> Dict[str, Any]:
        """
        Dispatches batch generation for multiple shots:
        - If auto_bundle is True, automatically generates cinematic prompts & attaches product images.
        - Submits scenes to Google Flow.
        - Spawns background poller for auto-ingest into 01_Raw/<product_id>/AI_Flow/.
        """
        if not shots:
            raise ValueError("รายการช็อตต้องไม่ว่างเปล่า (shots cannot be empty)")

        scenes_to_submit: List[Dict[str, Any]] = []

        if auto_bundle:
            from scripts.flow_prompt_engine import bundle_flow_context
            for shot in shots:
                # If already fully structured with prompt and (reference_images or first_frame)
                if shot.get("prompt") and (shot.get("reference_images") or shot.get("first_frame")):
                    scenes_to_submit.append(shot)
                else:
                    beat_text = (
                        shot.get("beat_text")
                        or shot.get("text")
                        or shot.get("prompt")
                        or shot.get("concept")
                        or "Cinematic product shot"
                    )
                    cam = shot.get("camera_direction") or shot.get("technique") or "orbit"
                    light = shot.get("lighting") or "studio_clean"
                    ratio = shot.get("aspect_ratio") or "9:16"
                    dur = int(shot.get("duration") or 8)

                    bundled = bundle_flow_context(
                        product_id=product_id,
                        beat_text=beat_text,
                        camera_direction=cam,
                        lighting=light,
                        aspect_ratio=ratio,
                        duration=dur,
                        download_quality=shot.get("download_quality", "original"),
                        max_credits=int(shot.get("max_credits", 25)),
                    )
                    scenes_to_submit.append(bundled)
        else:
            scenes_to_submit = shots

        return self.submit_generation(
            product_id=product_id,
            scenes=scenes_to_submit,
            project_name=project_name,
            auto_poll=True,
        )

    def check_and_sync_job(self, job_id: str) -> Dict[str, Any]:
        """Polls flow-mcp for the job status, updates local store, and auto-ingests completed files."""
        job = FlowJobStore.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job["status"] in ("completed", "failed"):
            return job

        client_job_ids = job.get("client_job_ids", [])
        wait_res = self.client.wait(job_ids=client_job_ids, timeout_seconds=12)

        is_finished = wait_res.get("finished", False)
        jobs_info = wait_res.get("jobs", []) or wait_res.get("tasks", [])

        product_id = job.get("product_id", "")
        ingested_files = list(job.get("ingested_files") or [])
        already_ingested_paths = {f.get("original_source") or f.get("path") for f in ingested_files}

        # Auto-ingest any newly produced output files
        for idx, item in enumerate(jobs_info):
            if not isinstance(item, dict):
                continue
            item_status = item.get("status")
            if item_status in ("done", "completed"):
                files = item.get("files") or []
                label = item.get("scene") or f"shot_{idx + 1}"
                for file_path in files:
                    if file_path and file_path not in already_ingested_paths and Path(file_path).is_file():
                        try:
                            meta = self.ingest_clip(
                                product_id=product_id,
                                source_path=file_path,
                                shot_label=label,
                            )
                            meta["original_source"] = file_path
                            ingested_files.append(meta)
                            already_ingested_paths.add(file_path)
                        except Exception as exc:
                            logger.error(f"Error auto-ingesting clip {file_path}: {exc}")

        updates: Dict[str, Any] = {
            "results": jobs_info,
            "ingested_files": ingested_files,
        }
        if is_finished:
            all_failed = all(j.get("status") == "failed" for j in jobs_info if isinstance(j, dict)) and len(jobs_info) > 0
            if all_failed:
                updates["status"] = "failed"
            else:
                updates["status"] = "completed"
        else:
            updates["status"] = "processing"

        updated = FlowJobStore.update_job(job_id, updates)
        return updated or job

    def start_background_poller(self, job_id: str) -> None:
        """Starts asynchronous background polling thread for a job."""
        with self._poller_lock:
            existing = self._active_pollers.get(job_id)
            if existing and existing.is_alive():
                return
            t = threading.Thread(
                target=self._run_job_poller,
                args=(job_id,),
                name=f"flow-poller-{job_id}",
                daemon=True,
            )
            self._active_pollers[job_id] = t
            t.start()
            logger.info(f"Started background poller for Flow job {job_id}")

    def _run_job_poller(self, job_id: str) -> None:
        """Background poller execution loop."""
        max_duration = 900.0  # 15 min safety timeout
        start_time = time.time()
        try:
            while time.time() - start_time < max_duration:
                job = FlowJobStore.get_job(job_id)
                if not job or job.get("status") in ("completed", "failed"):
                    break
                try:
                    updated = self.check_and_sync_job(job_id)
                    if updated.get("status") in ("completed", "failed"):
                        logger.info(f"Flow job {job_id} finished with status: {updated.get('status')}")
                        break
                except Exception as exc:
                    logger.warning(f"Flow poller error for {job_id}: {exc}")

                time.sleep(4.0)
        finally:
            with self._poller_lock:
                self._active_pollers.pop(job_id, None)

    def recover_pending_jobs(self) -> int:
        """Resumes background polling for any unfinished jobs across server restarts."""
        recovered = 0
        for job in FlowJobStore.list_jobs():
            if job.get("status") in ("queued", "processing"):
                self.start_background_poller(job["id"])
                recovered += 1
        return recovered

    def ingest_clip(
        self,
        product_id: str,
        source_path: str,
        shot_label: str = "",
        custom_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Copies a finished video clip into 01_Raw/<product_id>/AI_Flow/<filename>.mp4
        with SHA-256 deduplication and metadata recording.
        """
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source video not found: {source_path}")

        dest_dir = RAW_DIR / product_id / "AI_Flow"
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Checksum calculation for deduplication (Rule 3.13)
        hasher = hashlib.sha256()
        with src.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()

        # Check if identical clip is already ingested in AI_Flow
        for existing in dest_dir.glob("*.mp4"):
            try:
                if existing.stat().st_size == src.stat().st_size:
                    h = hashlib.sha256()
                    with existing.open("rb") as ef:
                        for chunk in iter(lambda: ef.read(65536), b""):
                            h.update(chunk)
                    if h.hexdigest() == digest:
                        logger.info(f"Deduplicated AI Flow clip {existing.name} (SHA-256 match)")
                        return {
                            "product_id": product_id,
                            "filename": existing.name,
                            "path": str(existing),
                            "relative_path": f"01_Raw/{product_id}/AI_Flow/{existing.name}",
                            "size_bytes": existing.stat().st_size,
                            "sha256": digest,
                            "shot_label": shot_label,
                            "ingested_at": FlowJobStore._now_iso(),
                            "deduplicated": True,
                        }
            except OSError:
                pass

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_label = "".join(c for c in (shot_label or custom_name or "broll") if c.isalnum() or c in ("_", "-"))
        filename = f"flow_{timestamp}_{safe_label}.mp4"
        dest_file = dest_dir / filename

        # Atomic copy
        tmp_file = dest_dir / f".{filename}.part"
        try:
            shutil.copy2(src, tmp_file)
            tmp_file.replace(dest_file)
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

        stat = dest_file.stat()
        rel_path = f"01_Raw/{product_id}/AI_Flow/{filename}"
        metadata = {
            "product_id": product_id,
            "filename": filename,
            "path": str(dest_file),
            "relative_path": rel_path,
            "size_bytes": stat.st_size,
            "sha256": digest,
            "shot_label": shot_label,
            "ingested_at": FlowJobStore._now_iso(),
            "deduplicated": False,
        }

        logger.info(f"Ingested Google Flow clip: {dest_file} ({stat.st_size} bytes, sha256={digest[:8]})")
        return metadata


_flow_service: Optional[FlowService] = None

def get_flow_service() -> FlowService:
    global _flow_service
    if _flow_service is None:
        _flow_service = FlowService()
    return _flow_service

"""
Flow Service: Coordinates video generation with Google Flow via flow-mcp,
persists job records, and automates video ingestion into 01_Raw/<product_id>/AI_Flow.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import shutil
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
    def __init__(self, client: Optional[FlowClient] = None):
        self.client = client or get_flow_client()

    def get_status(self, detailed: bool = False) -> Dict[str, Any]:
        """Returns the status of flow-mcp service and Google Flow connection."""
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
    ) -> Dict[str, Any]:
        """
        Submits scenes to flow-mcp and registers the job in FlowJobStore.
        """
        if not scenes:
            raise ValueError("ต้องระบุฉากอย่างน้อย 1 ฉาก (scenes cannot be empty)")

        proj_name = project_name or f"Omni_{product_id[:8]}"
        res = self.client.generate(project=proj_name, scenes=scenes)

        client_job_ids = res.get("job_ids", [])
        if not client_job_ids and "task_id" in res:
            client_job_ids = [res["task_id"]]

        job = FlowJobStore.create_job(
            product_id=product_id,
            project_name=proj_name,
            scenes=scenes,
            client_job_ids=client_job_ids,
        )
        return {"job": job, "flow_response": res}

    def check_and_sync_job(self, job_id: str) -> Dict[str, Any]:
        """Polls flow-mcp for the job status and updates local store."""
        job = FlowJobStore.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job["status"] in ("completed", "failed"):
            return job

        client_job_ids = job.get("client_job_ids", [])
        wait_res = self.client.wait(job_ids=client_job_ids, timeout_seconds=15)

        is_finished = wait_res.get("finished", False)
        jobs_info = wait_res.get("jobs", []) or wait_res.get("tasks", [])

        updates: Dict[str, Any] = {"results": jobs_info}
        if is_finished:
            # Check if any error occurred
            any_failed = any(j.get("status") == "failed" for j in jobs_info if isinstance(j, dict))
            updates["status"] = "failed" if any_failed else "completed"
        else:
            updates["status"] = "processing"

        updated = FlowJobStore.update_job(job_id, updates)
        return updated or job

    def ingest_clip(
        self,
        product_id: str,
        source_path: str,
        shot_label: str = "",
        custom_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Copies a finished video clip into 01_Raw/<product_id>/AI_Flow/<filename>.mp4
        and records its metadata.
        """
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source video not found: {source_path}")

        dest_dir = RAW_DIR / product_id / "AI_Flow"
        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_label = "".join(c for c in (shot_label or custom_name or "broll") if c.isalnum() or c in ("_", "-"))
        filename = f"flow_{timestamp}_{safe_label}.mp4"
        dest_file = dest_dir / filename

        shutil.copy2(src, dest_file)
        stat = dest_file.stat()

        rel_path = f"01_Raw/{product_id}/AI_Flow/{filename}"
        metadata = {
            "product_id": product_id,
            "filename": filename,
            "path": str(dest_file),
            "relative_path": rel_path,
            "size_bytes": stat.st_size,
            "shot_label": shot_label,
            "ingested_at": FlowJobStore._now_iso(),
        }

        logger.info(f"Ingested Google Flow clip: {dest_file} ({stat.st_size} bytes)")
        return metadata


_flow_service: Optional[FlowService] = None

def get_flow_service() -> FlowService:
    global _flow_service
    if _flow_service is None:
        _flow_service = FlowService()
    return _flow_service

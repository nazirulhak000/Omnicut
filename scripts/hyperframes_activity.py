"""Read-only projection of HF durable state into ActivityCenter task shapes."""
from copy import deepcopy
from datetime import datetime, timezone

from scripts.hyperframes_recovery import read_hyperframes_jobs


_STATUS = {"queued": "queued", "claimed": "processing", "authoring": "processing", "rendering": "processing",
           "finalizing": "processing", "submitted": "completed", "finalized": "completed",
           "failed": "failed", "cancelled": "cancelled", "qc_ready": "awaiting_review"}


def _timestamp(value):
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            return None
    return value


def hyperframes_activity_tasks(root, channel_id):
    tasks = []
    for table, mirror, kind in (("creative_jobs", "creative_jobs.json", "hyperframes_authoring"),
                                ("hyperframes_render_jobs", "hyperframes_render_jobs.json", "hyperframes_render")):
        for row in read_hyperframes_jobs(root, table=table, mirror=mirror):
            if row.get("channel_id") != channel_id:
                continue
            raw_status = row.get("status")
            status = _STATUS.get(raw_status, raw_status)
            error = row.get("error")
            tasks.append({"id": row["id"], "type": kind, "task_type": kind, "channel_id": channel_id,
                          "title": "HyperFrames authoring" if kind == "hyperframes_authoring" else "HyperFrames render",
                          "status": status, "hyperframes_status": raw_status,
                          "progress": 1.0 if status == "completed" else None,
                          "step_label": row.get("phase") or raw_status,
                          "target_tab": "creative", "target_id": row.get("project_id"),
                          "payload": {"project_id": row.get("project_id"), "job_id": row["id"],
                                      "channel_id": channel_id, "job_kind": kind},
                          "created_at": _timestamp(row.get("created_at")), "updated_at": _timestamp(row.get("updated_at")),
                          "result": deepcopy(row.get("result") or row.get("artifact")),
                          "error": error.get("message") if isinstance(error, dict) else error,
                          "error_detail": deepcopy(error), "logs": [], "read_only_projection": True})
    return tasks

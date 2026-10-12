"""Startup recovery of accepted HF work; no import-time stores or retries."""
from copy import deepcopy
from contextlib import closing
import json
import logging
from pathlib import Path
import sqlite3
import threading


def read_hyperframes_jobs(root, *, table="hyperframes_render_jobs", mirror="hyperframes_render_jobs.json"):
    """Read an existing store without initializing tables or importing mirrors."""
    if table not in {"hyperframes_render_jobs", "creative_jobs"} or mirror != f"{table}.json":
        raise ValueError("Unsupported HyperFrames job table")
    root = Path(root).resolve()
    database = root / "_Docs/store.db"
    if database.is_file():
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
            exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if exists:
                rows = [json.loads(row[0]) for row in connection.execute(f'SELECT data FROM "{table}"')]
                if not all(isinstance(row, dict) for row in rows):
                    raise ValueError("Malformed HyperFrames job rows")
                return rows
    path = root / "_Docs" / mirror
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError("Malformed HyperFrames job mirror")
    return deepcopy(data)


def _dispatch(operation, *args):
    def run():
        try:
            operation(*args)
        except Exception:
            logging.getLogger(__name__).exception("HyperFrames approved work recovery failed")
    threading.Thread(target=run, name="hyperframes-recovery", daemon=True).start()


def recover_hyperframes_work(root, *, service=None, jobs=None, finalizer=None, dispatch=None,
                            channel_allowed=None, alive=None):
    """Reconcile dead workers; resume only queued or approved finalizing work.

    Interrupted renders and recovery_required conflicts require an explicit UI
    retry/repair. Archived/unknown owners are reconciled, then blocked from new
    execution. Dispatch counts mean scheduled, never claimed success/completion.
    """
    root = Path(root).resolve()
    report = {"interrupted": [], "queued_dispatched": [], "finalize_dispatched": [],
              "blocked_channels": [], "errors": [], "counts": {"interrupted": 0, "queued": 0, "finalizing": 0}}
    if not (root / "_Docs/store.db").is_file() and not (root / "_Docs/hyperframes_render_jobs.json").is_file():
        return report
    try:
        rows = read_hyperframes_jobs(root)
    except Exception as error:
        report["errors"].append({"phase": "read", "message": str(error)})
        return report
    if not rows:
        return report
    from scripts.channel_store import ChannelStore, is_valid_channel_id
    from scripts.hyperframes_render import HyperFramesRenderJobs
    jobs = jobs or getattr(service, "renders", None) or HyperFramesRenderJobs(root)
    if hasattr(jobs, "root") and Path(jobs.root).resolve() != root:
        report["errors"].append({"phase": "adapter", "message": "Render store root differs from recovery root"})
        return report
    if finalizer is not None and hasattr(finalizer, "root") and Path(finalizer.root).resolve() != root:
        report["errors"].append({"phase": "adapter", "message": "Finalizer root differs from recovery root"})
        return report
    dispatch = dispatch or _dispatch
    if channel_allowed is None:
        registry = ChannelStore(root / "_Docs/channels.json", project_root=root)
        def channel_allowed(owner):
            record = registry.find(owner)
            return bool(record and record.get("status") == "active")
    owners = sorted({row["channel_id"] for row in rows if is_valid_channel_id(row.get("channel_id"))})
    for owner in owners:
        try:
            report["interrupted"].extend(jobs.recover_interrupted(owner, **({"alive": alive} if alive else {})))
            if not channel_allowed(owner):
                report["blocked_channels"].append(owner)
                continue
            for job in jobs.list(owner):
                if job["status"] == "queued":
                    dispatch(jobs.execute, owner, job["id"])
                    report["queued_dispatched"].append(job["id"])
                elif job["status"] == "finalizing" and job.get("finalize_intent"):
                    if finalizer is None:
                        from scripts.hyperframes_finalize import HyperFramesFinalizer
                        finalizer = getattr(service, "finalizer", None) or HyperFramesFinalizer(root, jobs=jobs)
                    dispatch(finalizer.resume, owner, job["id"])
                    report["finalize_dispatched"].append(job["id"])
        except Exception as error:
            report["errors"].append({"channel_id": owner, "phase": "recover", "message": str(error)})
    report["counts"] = {"interrupted": len(report["interrupted"]), "queued": len(report["queued_dispatched"]),
                        "finalizing": len(report["finalize_dispatched"])}
    return report

"""Idempotent local projections for an exact, reviewed publication event.

Files stay at their canonical registered path. This records publication; it
does not move media, submit to TikTok, reuse acknowledgement effects, or grant
a new posting attempt. Each projection commits before its observation marker.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from scripts.channel_store import ChannelError, normalize_handle
from scripts.db import DocumentTable, _connection_for
from scripts.posting_jobs import PostingJobStore, fingerprint
from scripts.publication_observations import PublicationObservationStore, EFFECT_PHASES

TABLE_FILES = {"posts": "post_log.json", "export_registry": "export_registry.json",
               "schedule_queue": "schedule_queue.json", "products": "products.json"}


class PublicationEffects:
    def __init__(self, root: Path, *, observations=None, jobs=None, tables=None):
        if root is None:
            raise ValueError("An explicit storage root is required")
        self.root = Path(root)
        self.jobs = jobs or PostingJobStore(self.root)
        self.observations = observations or PublicationObservationStore(self.root, jobs=self.jobs)
        if self.observations.root.resolve() != self.root.resolve() or self.jobs.root is None or self.jobs.root.resolve() != self.root.resolve():
            raise ValueError("All publication services must share one explicit root")
        self.tables = tables if tables is not None else {
            name: DocumentTable(name, lambda: self.root / "_Docs" / "store.db",
                                lambda filename=filename: self.root / "_Docs" / filename)
            for name, filename in TABLE_FILES.items()}
        for name in TABLE_FILES:
            table = self.tables[name]
            if table._db_path_fn().resolve() != (self.root / "_Docs" / "store.db").resolve() or table._json_path_fn().resolve() != (self.root / "_Docs" / TABLE_FILES[name]).resolve():
                raise ValueError("Projection tables must use the explicit publication root")

    @staticmethod
    def _error(code, message):
        raise ChannelError(409, code, message)

    @staticmethod
    def _stamp():
        return datetime.now(timezone.utc).isoformat()

    def _job(self, event):
        job = self.jobs.get(event["channel_id"], event["job_id"])
        if job.get("receipt_hash") != event["scheduled_receipt_hash"] or fingerprint(job.get("receipt")) != event["scheduled_receipt_hash"]:
            self._error("publication_receipt_changed", "Scheduled receipt changed after observation")
        if job.get("export_id") != event["export_id"] or job.get("status") != "scheduled_on_platform":
            self._error("publication_job_changed", "Original scheduled job no longer matches observation")
        if normalize_handle(job["receipt"]["source_account"]) != event["source_account"]:
            self._error("account_handle_mismatch", "Scheduled account differs from publication")
        return job

    def _export(self, event):
        export = next((row for row in self.tables["export_registry"].scoped_load(event["channel_id"])
                       if row.get("id") == event["export_id"]), None)
        if export is None:
            self._error("publication_export_missing", "Frozen export is missing from this channel")
        job = self._job(event)
        for field in ("product_id", "angle_id"):
            if job.get(field) and export.get(field) != job[field]:
                self._error("publication_parent_conflict", "Export parent differs from frozen scheduled job")
        return export

    def _post_log(self, event):
        job, export = self._job(event), self._export(event)
        channel, video_id = event["channel_id"], event["platform_video_id"]
        url = f"https://www.tiktok.com/{event['source_account']}/video/{video_id}"
        with self.tables["posts"].scoped_mutate(channel) as rows:
            candidates = [r for r in rows if r.get("export_id") == event["export_id"]
                          or str(r.get("platform_video_id") or r.get("platform_post_id") or "") == video_id
                          or r.get("tiktok_url") == url]
            if len(candidates) > 1:
                self._error("publication_post_ambiguous", "More than one exact post matches this observation")
            if candidates:
                row = candidates[0]
                if row.get("export_id") not in {None, "", event["export_id"]}:
                    self._error("publication_post_conflict", "Platform post belongs to a different export")
                if row.get("source_account") and normalize_handle(row["source_account"]) != event["source_account"]:
                    self._error("account_handle_mismatch", "Post account differs from observation")
                if row.get("platform_video_id") and str(row["platform_video_id"]) != video_id:
                    self._error("publication_post_conflict", "Export already has another platform video")
                if row.get("tiktok_url") and row["tiktok_url"] != url:
                    self._error("publication_post_conflict", "Export post already references another exact public URL")
            else:
                row = {"id": "pub_" + sha256((channel + ":" + event["export_id"]).encode()).hexdigest()[:24],
                       "channel_id": channel, "platform": "tiktok", "metrics": None,
                       "metrics_filled_at": None, "source": "publication_observation"}
                rows.append(row)
            row.update(export_id=event["export_id"], platform_video_id=video_id, platform_post_id=video_id,
                       source_account=event["source_account"], tiktok_url=url,
                       publication_observation_id=event["id"])
            defaults = {"posted_at": event["observed_published_at"], "clip_file": str(export.get("path") or job.get("video_path") or ""),
                        "product_id": job.get("product_id"), "product_name": job.get("product_name"),
                        "angle_key": job.get("angle_id"), "caption": job.get("caption") or "",
                        "hashtags": (job.get("hashtags").split() if isinstance(job.get("hashtags"), str) else job.get("hashtags") or []), "scheduled_at": job.get("scheduled_at")}
            for key, value in defaults.items():
                if not row.get(key):
                    row[key] = value

    def _export_registry(self, event):
        self._job(event)
        with self.tables["export_registry"].scoped_mutate(event["channel_id"]) as rows:
            row = next((r for r in rows if r.get("id") == event["export_id"]), None)
            if row is None:
                self._error("publication_export_missing", "Frozen export disappeared")
            if row.get("publication_observation_id") not in {None, event["id"]}:
                self._error("publication_export_conflict", "Export has another publication observation")
            row.update(status="posted", posted_at=row.get("posted_at") or event["observed_published_at"],
                       publication_observation_id=event["id"], platform_video_id=event["platform_video_id"],
                       updated_at=self._stamp())

    def _schedule_queue(self, event):
        job = self._job(event)
        if not job.get("queue_id"):
            return
        with self.tables["schedule_queue"].scoped_mutate(event["channel_id"]) as rows:
            row = next((r for r in rows if r.get("id") == job["queue_id"]), None)
            if row is None:
                self._error("publication_queue_missing", "Original scheduled queue is missing")
            if row.get("export_id") != event["export_id"] or row.get("posting_job_id") != job["id"] or row.get("status") not in {"scheduled_on_platform", "posted"}:
                self._error("publication_queue_changed", "Queue no longer identifies the exact accepted scheduled job")
            row.update(status="posted", posted_at=row.get("posted_at") or event["observed_published_at"],
                       publication_observation_id=event["id"], updated_at=self._stamp())

    def _angle(self, event):
        job = self._job(event)
        if (job.get("source_binding") or {}).get("type") == "gadget_project":
            from scripts.hyperframes_publication import apply_gadget_publication
            apply_gadget_publication(self.root, job, event)
            return
        if not job.get("product_id") or not job.get("angle_id"):
            return
        # Import the registry before starting the product transaction; inside
        # BEGIN IMMEDIATE use the same connection's SELECT, never nested load.
        self.tables["export_registry"].scoped_load(event["channel_id"])
        with self.tables["products"].scoped_mutate(event["channel_id"]) as rows:
            product = next((r for r in rows if r.get("id") == job["product_id"]), None)
            if product is None:
                self._error("publication_product_missing", "Original product is missing")
            matches = [a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == job["angle_id"]
                       and (job.get("batch") is None or a.get("batch") == job["batch"])]
            if len(matches) != 1:
                self._error("publication_angle_ambiguous", "Exact original angle/batch cannot be resolved")
            angle = matches[0]
            if angle.get("export_id") and angle["export_id"] != event["export_id"]:
                return  # historical export truth must not retarget the current angle
            conn = _connection_for(self.root / "_Docs" / "store.db")
            exports = [json.loads(r[0]) for r in conn.execute("SELECT data FROM export_registry")]
            candidates = [r for r in exports if r.get("channel_id") == event["channel_id"]
                          and r.get("product_id") == job["product_id"] and r.get("angle_id") == job["angle_id"]]
            expected = next((r for r in candidates if r.get("id") == event["export_id"]), None)
            if expected is None:
                self._error("publication_parent_conflict", "Frozen export does not belong to the original angle")
            try:
                created = datetime.fromisoformat(expected["created_at"])
                if any(datetime.fromisoformat(r["created_at"]) >= created for r in candidates if r["id"] != expected["id"]):
                    return
            except (KeyError, ValueError, TypeError):
                return  # abstain rather than inventing chronology from UUIDs
            def mtime(record):
                path = Path(str(record.get("path") or ""))
                path = path if path.is_absolute() else self.root / path
                if not path.resolve().is_relative_to(self.root.resolve()):
                    self._error("publication_path_invalid", "Registry media path escapes explicit project root")
                return path.stat().st_mtime if path.is_file() else -1
            expected_mtime = mtime(expected)
            if any(mtime(r) > expected_mtime for r in candidates if r["id"] != expected["id"]):
                return
            angle.update(status="posted", posted_at=angle.get("posted_at") or event["observed_published_at"],
                         publication_observation_id=event["id"], status_updated_at=self._stamp())
            product["updated_at"] = self._stamp()

    def _job_projection(self, event):
        self._job(event)
        with self.jobs.table.scoped_mutate(event["channel_id"]) as rows:
            job = self.jobs._find(rows, event["job_id"])
            if job.get("receipt_hash") != event["scheduled_receipt_hash"] or job.get("export_id") != event["export_id"]:
                self._error("publication_job_changed", "Original scheduled job changed during projection")
            if job.get("publication_observation_id") not in {None, event["id"]}:
                self._error("publication_job_conflict", "Job already references another publication")
            if job.get("publication_observation_id") == event["id"]:
                return
            job.update(publication_status="published", publication_observation_id=event["id"],
                       published_at=event["observed_published_at"], platform_video_id=event["platform_video_id"],
                       revision=job["revision"] + 1, updated_at=self.jobs.clock())

    def apply(self, channel_id, observation_id):
        event = self.observations.get(channel_id, observation_id)
        if event["status"] != "verified":
            self._error("publication_waiting_linkage", "Exact platform linkage is not yet established")
        self._job(event)
        for phase in EFFECT_PHASES:
            event = self.observations.apply_effect(channel_id, observation_id, phase,
                                                   expected_revision=event["revision"], handler=getattr(self, "_" + phase))
        return event

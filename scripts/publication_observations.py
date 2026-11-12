"""Exact scheduled-publication observations, independent of publish attempts.

Evidence must come from the authenticated platform adapter. This module never
opens a browser, publishes, acquires a posting lease, or changes a receipt.
Effect handlers must upsert by observation ID: recovery may replay a handler
after a crash between its external commit and our durable completion marker.
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import re
import secrets
import time

from scripts.channel_store import ChannelError, HandleError, normalize_handle
from scripts.db import DocumentTable
from scripts.posting_jobs import PostingJobStore, account_check, fingerprint

EFFECT_PHASES = ("post_log", "export_registry", "schedule_queue", "angle", "job_projection")


class PublicationObservationStore:
    def __init__(self, root: Path, *, jobs=None, clock=time.time, effect_timeout=60):
        if root is None:
            raise ValueError("An explicit storage root is required")
        self.root = Path(root)
        self.jobs = jobs or PostingJobStore(self.root, clock=clock)
        if self.jobs.root is None or self.jobs.root.resolve() != self.root.resolve():
            raise ValueError("Posting jobs must use the same explicit storage root")
        self.clock = clock
        if effect_timeout <= 0:
            raise ValueError("Effect timeout must be positive")
        self.effect_timeout = effect_timeout
        self.path = self.root / "_Docs" / "publication_observations.json"
        self.table = DocumentTable("publication_observations", lambda: self.path.parent / "store.db", lambda: self.path)

    @staticmethod
    def _error(code, message, status=409):
        raise ChannelError(status, code, message)

    def _find(self, rows, observation_id):
        row = next((r for r in rows if r["id"] == observation_id), None)
        if row is None:
            self._error("resource_not_found", "Publication observation not found", 404)
        return row

    def _account(self, raw):
        try:
            return normalize_handle(raw)
        except HandleError:
            self._error("publication_account_invalid", "An exact valid platform account is required", 422)

    @staticmethod
    def caption_key(text, length=40):
        """Whitespace-insensitive prefix of a caption (TikTok re-wraps lines and may trim spaces)."""
        return re.sub(r"\s+", "", str(text or ""))[:length]

    def _check_content_linkage(self, job, evidence, stamp):
        linkage = evidence.get("linkage") or {}
        if linkage.get("method") != "content_row":
            self._error("publication_evidence_required", "Content-page linkage evidence is required", 422)
        expected = self.caption_key(job.get("caption"))
        seen = re.sub(r"\s+", "", str(linkage.get("caption_text") or ""))
        if len(expected) < 8 or expected not in seen:
            self._error("publication_linkage_mismatch", "Content row caption differs from this job")
        from scripts.episode_registry import tag_numbers
        episode = job.get("episode_no")
        shown = tag_numbers(linkage.get("caption_text"))
        # The EP hashtag is the clip's permanent identity (two clips of one product share a caption prefix):
        # a row showing another clip's EP is never this job; a row showing none is accepted on caption + time.
        if episode and shown and int(episode) not in shown:
            self._error("publication_linkage_mismatch", "Content row carries another clip's EP tag")
        if job.get("schedule_date") and job.get("schedule_time"):
            slot = datetime.fromisoformat(f"{job['schedule_date']}T{job['schedule_time']}:00+07:00")
            if abs((stamp - slot).total_seconds()) > 15 * 60:
                self._error("publication_linkage_mismatch", "Content row publish time differs from this job's slot")

    def get(self, channel_id, observation_id):
        return deepcopy(self._find(self.table.scoped_load(channel_id), observation_id))

    def for_job(self, channel_id, job_id):
        self.jobs.get(channel_id, job_id)
        return [deepcopy(r) for r in self.table.scoped_load(channel_id) if r["job_id"] == job_id]

    def observe(self, channel_id, job_id, source_account, platform_video_id,
                observed_published_at, evidence, *, idempotency_key, expected_job_revision=None):
        job = self.jobs.get(channel_id, job_id)
        receipt = job.get("receipt") or {}
        if job.get("status") != "scheduled_on_platform" or receipt.get("outcome") != "scheduled_on_platform":
            self._error("publication_job_not_scheduled", "Only platform-accepted scheduled jobs can be observed")
        if not job.get("receipt_hash") or job["receipt_hash"] != fingerprint(receipt):
            self._error("publication_receipt_invalid", "Accepted scheduled receipt integrity check failed")
        self._account(source_account)
        account = account_check(channel_id, job.get("target_handle"), source_account, strict=True)["source_account"]
        if self._account(receipt.get("source_account")) != account:
            self._error("account_handle_mismatch", "Observation account differs from accepted receipt")
        if not isinstance(idempotency_key, str) or not idempotency_key or len(idempotency_key) > 200:
            self._error("publication_idempotency_invalid", "Observation key is required", 422)
        video_id = str(platform_video_id) if platform_video_id is not None else None
        if video_id is not None and not re.fullmatch(r"[0-9]{8,32}", video_id):
            self._error("publication_video_id_invalid", "Invalid exact platform video ID", 422)
        try:
            stamp = datetime.fromisoformat(observed_published_at.replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError("Timezone required")
        except (ValueError, TypeError, AttributeError):
            self._error("publication_timestamp_invalid", "Publication timestamp needs a timezone", 422)
        if not isinstance(evidence, dict) or evidence.get("kind") != "platform_publication" or evidence.get("source") not in {"platform_api", "platform_detail", "reviewed_platform_record"}:
            self._error("publication_evidence_required", "Exact platform publication evidence is required", 422)
        if evidence.get("published") is not True or evidence.get("platform_video_id") != video_id or evidence.get("job_id") != job_id or evidence.get("channel_id") != channel_id:
            self._error("publication_evidence_mismatch", "Evidence must identify the same published video/job/channel", 422)
        if self._account(evidence.get("source_account")) != account:
            self._error("account_handle_mismatch", "Evidence account differs from observed account")
        accepted_id = (receipt.get("proof") or {}).get("platform_post_id")
        if accepted_id and video_id and str(accepted_id) != video_id:
            self._error("publication_linkage_mismatch", "Video ID differs from frozen scheduled receipt")
        # TikTok's "scheduled" toast never carries a video id, so a scheduled receipt usually has none. Then the link
        # is established by (a) a human who reviewed the exact public URL, or (b) the Content-page row whose caption and
        # publish time match this job exactly.
        linked = bool(accepted_id and video_id)
        if not accepted_id and video_id:
            if (evidence.get("source") == "reviewed_platform_record"
                    and evidence.get("review_confirmation") == "reviewed_published_video"
                    and str(evidence.get("evidence_url") or "").rstrip("/").endswith(f"/{account}/video/{video_id}")):
                # an operator opened that exact public video of this account and confirmed it is this clip
                linked = True
            elif evidence.get("source") == "platform_detail" and evidence.get("linkage"):
                self._check_content_linkage(job, evidence, stamp)
                linked = True
        state = "verified" if linked else "waiting_linkage"
        payload = {"job_id": job_id, "channel_id": channel_id, "source_account": account,
                   "platform_video_id": video_id, "observed_published_at": observed_published_at,
                   "evidence": deepcopy(evidence), "scheduled_receipt_hash": job.get("receipt_hash"),
                   "export_id": job.get("export_id")}
        digest = fingerprint(payload)
        with self.table.scoped_mutate(channel_id) as rows:
            if state == "verified" and any(r.get("platform_video_id") == video_id and r.get("status") == "verified" and r.get("job_id") != job_id for r in rows):
                self._error("publication_video_already_linked", "Platform video already belongs to another job")
            existing = next((r for r in rows if r["idempotency_key"] == idempotency_key), None)
            if existing:
                if existing["payload_hash"] != digest:
                    self._error("publication_idempotency_conflict", "Observation key already identifies different evidence")
                return deepcopy(existing)
            existing = next((r for r in rows if r["job_id"] == job_id and r["status"] == "verified"), None)
            if existing:
                if existing["platform_video_id"] != video_id:
                    self._error("publication_linkage_mismatch", "Job already has a different publication")
                return deepcopy(existing)
            if expected_job_revision is not None and job["revision"] != expected_job_revision:
                self._error("publication_job_revision_conflict", "Posting job revision changed")
            now = self.clock()
            row = {**payload, "id": secrets.token_hex(16), "idempotency_key": idempotency_key,
                   "payload_hash": digest, "status": state, "revision": 1,
                   "created_at": now, "updated_at": now, "effects_applied": False,
                   "effects": {phase: {"status": "pending"} for phase in EFFECT_PHASES}}
            rows.append(row)
            return deepcopy(row)

    def apply_effect(self, channel_id, observation_id, phase, *, expected_revision, handler):
        """Persist intent, run an idempotent adapter, then CAS its completion.

        A pending/error/expired phase may be repaired. In-flight competing calls
        cannot run the same handler until its timeout. No posting job lease is
        read or renewed here. Adapters receive frozen evidence and stable ID.
        """
        if phase not in EFFECT_PHASES:
            self._error("publication_effect_invalid", "Unknown publication effect", 422)
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, observation_id)
            if row["status"] != "verified":
                self._error("publication_waiting_linkage", "Exact linkage must be verified before effects")
            effect = row["effects"][phase]
            if effect["status"] == "applied":
                return deepcopy(row)
            if row["revision"] != expected_revision:
                self._error("publication_revision_conflict", "Publication observation revision changed")
            now = self.clock()
            if effect["status"] == "applying" and effect["expires_at"] > now:
                self._error("publication_effect_busy", "Publication effect is already running")
            token = secrets.token_hex(16)
            effect.update(status="applying", token=token, expires_at=now + self.effect_timeout, error=None)
            row.update(revision=row["revision"] + 1, updated_at=now)
            frozen = deepcopy(row)
        try:
            handler(frozen)
        except Exception as exc:
            with self.table.scoped_mutate(channel_id) as rows:
                row = self._find(rows, observation_id)
                effect = row["effects"][phase]
                if effect.get("token") == token:
                    effect.update(status="error", error=type(exc).__name__)
                    row.update(revision=row["revision"] + 1, updated_at=self.clock())
            raise
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, observation_id)
            effect = row["effects"][phase]
            if effect.get("token") != token:
                self._error("publication_effect_fenced", "A repair superseded this effect worker")
            effect.update(status="applied", applied_at=self.clock(), error=None)
            row.update(revision=row["revision"] + 1, updated_at=self.clock(),
                       effects_applied=all(e["status"] == "applied" for e in row["effects"].values()))
            return deepcopy(row)

"""Durable, channel-owned posting protocol; no network or browser side effects.

Publishing is a one-way boundary. An expired pre-publish claim can be retried;
an attempted publication can only be acknowledged/reconciled, never reclaimed.
Cross-store local effects run after receipt persistence and retry idempotently.
"""
from copy import deepcopy
from hashlib import sha256
import json
import re
from pathlib import Path
import secrets
import time
from typing import Callable

from scripts import config
from scripts.db import DocumentTable
from scripts.channel_store import ChannelError, normalize_handle

PROTOCOL_VERSION = 2
_PUBLISHED_NOTICE = r"(?:(?:video|post) (?:posted|published)(?: successfully)?|(?:posted|published) successfully|(?:โพสต์|เผยแพร่)(?:วิดีโอ)?สำเร็จ)[.!]?"
_SCHEDULED_NOTICE = r"(?:(?:video|post) scheduled(?: successfully)?|scheduled successfully|(?:ตั้งเวลา|กำหนดเวลา)(?:โพสต์|วิดีโอ)?สำเร็จ)[.!]?"

_DRAFT_NOTICE = r"(?:(?:video |post )?(?:draft saved|saved to drafts?|saved as draft)|บันทึกแบบร่าง(?:แล้ว|สำเร็จ)?)[.!]?"

# draft_saved is final but is NOT a post: TikTok Studio shows no toast after "Save draft", it just opens
# Content > Drafts, so the evidence is that page (kind drafts_page_confirmed) or a manual confirmation.
FINAL_OUTCOMES = {"published", "scheduled_on_platform", "confirmation_unknown", "draft_saved"}
DRAFT_PROOF_KINDS = {"drafts_page_confirmed", "platform_success_notice", "manual_user_confirmation", "user_confirmed"}

# What the operator meant to do with the clip. Stored in the job at prepare time; the worker states which button it
# is about to press (click_kind) and the backend refuses a mismatch, so a "draft" job can never press Post and a
# scheduled/immediate job can never save a draft. Jobs prepared by old clients have no intent (inferred from the schedule).
# publish_draft = open a draft that already sits on TikTok and publish it (scheduled when the job has date+time, live
# otherwise). It behaves like `schedule` / `post_now` for every outcome rule (see effective_intent) but never uploads.
INTENTS = {"schedule", "draft", "post_now", "publish_draft"}
CLICK_KINDS = {"post", "draft"}
# A job in one of these states pressed (or may have pressed) a publish/draft button: it can never be released or
# re-prepared by "force", only reconciled with evidence.
ATTEMPTED_STATUSES = {"publishing", "confirmation_unknown", "scheduled_on_platform", "draft_saved", "published"}
# Evidence kinds that need a human-readable notice: nothing may be confirmed with a bare {"kind": ...}.
NOTICE_REQUIRED_KINDS = {"content_page_reconciled", "manual_user_confirmation", "user_confirmed"}


def job_intent(row) -> str:
    """The job's intent, inferred for jobs prepared before intents existed."""
    stored = row.get("intent")
    if stored in INTENTS:
        return stored
    return "schedule" if (row.get("schedule_date") and row.get("schedule_time")) else "post_now"


def effective_intent(row) -> str:
    """The intent the OUTCOME rules apply to: a draft publication is a scheduled post when it carries a slot, else an
    immediate one. (`draft` and the other intents are unchanged.)"""
    intent = job_intent(row)
    if intent == "publish_draft":
        return "schedule" if (row.get("schedule_date") and row.get("schedule_time")) else "post_now"
    return intent


def fingerprint(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def account_check(channel_id: str, target_handle: str, source_account, *, strict: bool, allow_unknown=False) -> dict:
    """Posting always requires identity; compatibility stats may quarantine unknown rows."""
    source = normalize_handle(source_account) if source_account else None
    target = normalize_handle(target_handle) if target_handle else None
    if source is not None and (target is None or source != target):
        raise ChannelError(409, "account_handle_mismatch", "บัญชี TikTok ไม่ตรงกับช่องของงาน จึงหยุดการโพสต์")
    if source is None and (not allow_unknown or strict or channel_id != "main"):
        raise ChannelError(409, "source_account_required", "อ่านบัญชี TikTok ไม่ได้ จึงหยุดเพื่อป้องกันโพสต์ผิดช่อง")
    return {"source_account": source, "account_verified": source is not None,
            "warning": None if source else "อ่านบัญชีไม่ได้: เก็บรอตรวจสอบ ยังไม่จับคู่หรืออัปเดตสถิติ"}


class PostingJobStore:
    def __init__(self, root: Path | None = None, *, clock: Callable[[], float] = time.time,
                 lease_seconds: int = 300):
        self.root = Path(root) if root is not None else None
        self.clock = clock
        self.lease_seconds = lease_seconds
        self.table = DocumentTable("posting_jobs", lambda: self.path.parent / "store.db", lambda: self.path)

    @property
    def path(self):
        return (self.root or config.BASE_DIR) / "_Docs" / "posting_jobs.json"

    def get(self, channel_id, job_id):
        row = next((r for r in self.table.scoped_load(channel_id) if r["id"] == job_id), None)
        if row is None:
            raise ChannelError(404, "resource_not_found", "ไม่พบงานโพสต์ของช่องนี้")
        return row

    def pending(self, channel_id):
        rows = self.table.scoped_load(channel_id)
        eligible = [r for r in rows if r["status"] in {"prepared", "claimed"} and not r.get("publish_attempted_at")
                    and r.get("prepare_effects_applied", True)]
        return min(eligible, key=lambda r: (r["created_at"], r["id"])) if eligible else None

    def _audit(self, row, event, **metadata):
        row.setdefault("audit", []).append({"event": event, "at": self.clock(), **metadata})
        row["audit"] = row["audit"][-100:]

    def prepare(self, channel_id, payload: dict, *, idempotency_key: str | None = None):
        frozen = deepcopy(payload)
        digest = fingerprint(frozen)
        key = idempotency_key or digest
        if not isinstance(key, str) or not key or len(key) > 200:
            raise ChannelError(422, "idempotency_key_invalid", "รหัสเตรียมงานไม่ถูกต้อง")
        with self.table.scoped_mutate(channel_id) as rows:
            existing = next((r for r in rows if r["idempotency_key"] == key and r["status"] != "cancelled"), None)
            if existing:
                if existing.get("prepared_payload_hash", existing["payload_hash"]) != digest:
                    raise ChannelError(409, "posting_idempotency_conflict", "รหัสงานเดิมมีข้อมูลคลิปต่างกัน")
                return deepcopy(existing)
            # A second key must not turn an uncertain/finished publish into a new job.
            # The draft a publish_draft job is made from is not a competitor: it stays draft_saved until the publication
            # succeeds (so a cleared/failed publication can be retried from the same draft).
            draft_source = frozen.get("draft_source_job_id") if frozen.get("intent") == "publish_draft" else None
            existing_export = next((r for r in rows if r["export_id"] == frozen["export_id"]
                                    and r["status"] != "cancelled"
                                    and not (draft_source and r["id"] == draft_source and r["status"] == "draft_saved")), None)
            if existing_export:
                now = self.clock()
                if (not existing_export.get("publish_attempted_at")
                        and existing_export["status"] == "claimed"
                        and existing_export.get("lease_expires_at")
                        and existing_export["lease_expires_at"] <= now):
                    existing_export["status"] = "cancelled"
                    existing_export["updated_at"] = now
                    self._audit(existing_export, "cancel_expired_abandoned")
                else:
                    raise ChannelError(409, "posting_export_already_prepared", "คลิปนี้มีงานโพสต์อยู่แล้ว ต้องตรวจผลเดิมก่อน")
            now = self.clock()
            job_id = secrets.token_hex(16)
            row = {**frozen, "id": job_id, "job_id": job_id, "channel_id": channel_id,
                   "protocol_version": PROTOCOL_VERSION, "payload_hash": digest,
                   "prepared_payload_hash": digest, "payload_fields": list(frozen),
                   "idempotency_key": key, "status": "prepared", "revision": 1,
                   "lease_owner": None, "lease_token": None, "lease_expires_at": None,
                   "attempt": 0, "created_at": now, "updated_at": now, "effects_applied": False,
                   "prepare_effects_applied": not frozen.get("queue_id")}
            self._audit(row, "prepare")
            rows.append(row)
            return deepcopy(row)

    def _find(self, rows, job_id):
        row = next((r for r in rows if r["id"] == job_id), None)
        if row is None:
            raise ChannelError(404, "resource_not_found", "ไม่พบงานโพสต์ของช่องนี้")
        return row

    def _fence(self, row, owner, token, revision, *, allow_expired=False):
        if not owner or not token or row["lease_owner"] != owner or not secrets.compare_digest(row["lease_token"] or "", token):
            raise ChannelError(409, "posting_lease_invalid", "สิทธิ์ของ Extension ไม่ตรงกับงานโพสต์")
        if row["revision"] != revision:
            raise ChannelError(409, "revision_conflict", "งานโพสต์เปลี่ยนแล้ว กรุณาโหลดงานเดิมใหม่", current_revision=row["revision"])
        if not allow_expired and (row["lease_expires_at"] or 0) <= self.clock():
            raise ChannelError(409, "posting_lease_expired", "สิทธิ์โพสต์หมดอายุแล้ว ห้ามกดโพสต์ซ้ำ")

    def claim(self, channel_id, job_id, owner):
        if not isinstance(owner, str) or not owner or len(owner) > 128:
            raise ChannelError(422, "posting_owner_invalid", "ไม่พบรหัส Extension instance")
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            if not row.get("prepare_effects_applied", True):
                raise ChannelError(409, "posting_prepare_incomplete", "งานยังผูกกับคิวไม่สำเร็จ ต้องเตรียมงานเดิมใหม่ก่อน")
            if row.get("publish_attempted_at") or row["status"] not in {"prepared", "claimed"}:
                raise ChannelError(409, "posting_reconciliation_required", "งานนี้เลยขั้นกดโพสต์แล้ว ต้องตรวจผลก่อน ห้ามโพสต์ซ้ำ")
            now = self.clock()
            busy = next((r for r in [*rows, *rows.out_of_scope] if r.get("lease_owner") == owner
                         and r["id"] != job_id and r["status"] in {"claimed", "publishing"}
                         and (r.get("lease_expires_at") or 0) > now), None)
            if busy:
                raise ChannelError(409, "posting_instance_busy", "Extension นี้กำลังทำงานอื่นอยู่")
            if row["status"] == "claimed" and (row["lease_expires_at"] or 0) > now:
                if row["lease_owner"] != owner:
                    raise ChannelError(409, "posting_job_claimed", "งานนี้มี Extension อื่นรับไปแล้ว")
                return deepcopy(row)
            row.update(status="claimed", lease_owner=owner, lease_token=secrets.token_urlsafe(32),
                       lease_expires_at=now + self.lease_seconds, revision=row["revision"] + 1, updated_at=now)
            self._audit(row, "claim", lease_owner=owner)
            return deepcopy(row)

    def validate_action(self, channel_id, job_id, owner, token, revision, source_account, *, begin_publish=False, confirmation_token=None, click_kind=None):
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            self._fence(row, owner, token, revision)
            if row["status"] != "claimed" or row.get("publish_attempted_at"):
                raise ChannelError(409, "posting_reconciliation_required", "งานนี้ไม่อนุญาตให้กดโพสต์ซ้ำ")
            if begin_publish:
                intent = job_intent(row)
                if click_kind is not None and click_kind not in CLICK_KINDS:
                    raise ChannelError(422, "posting_click_kind_invalid", "ชนิดปุ่มที่จะกดไม่ถูกต้อง")
                # a draft job may only save a draft; any other job may only press Post. A worker that does not say
                # what it presses is treated as "post" (old workers) and is therefore refused for draft jobs.
                if (click_kind or "post") != ("draft" if intent == "draft" else "post"):
                    raise ChannelError(409, "posting_intent_mismatch", f"งานนี้ตั้งใจเป็น {intent} แต่ Extension กำลังจะกดปุ่ม {click_kind or 'post'} จึงหยุด")
            check = account_check(channel_id, row["target_handle"], source_account, strict=row["strict_mode"])
            row["updated_at"] = self.clock()
            row["lease_expires_at"] = self.clock() + self.lease_seconds
            if begin_publish:
                row.update(status="publishing", publish_attempted_at=self.clock(), attempt=row["attempt"] + 1,
                           attempted_source_account=check["source_account"], confirmation_token=confirmation_token)
                self._audit(row, "publish_attempt", **check)
            else:
                self._audit(row, "account_check", **check)
            row["revision"] += 1
            return deepcopy(row)

    def acknowledge(self, channel_id, job_id, owner, token, revision, source_account,
                    outcome, proof: dict, *, reconcile=False):
        if outcome not in FINAL_OUTCOMES:
            raise ChannelError(422, "posting_outcome_invalid", "ผลการโพสต์ไม่ถูกต้อง")
        kind = proof.get("kind")
        if outcome != "confirmation_unknown":
            notice = proof.get("notice")
            allowed_kinds = {
                "platform_success_notice",
                "content_page_reconciled",
                "manual_user_confirmation",
                "user_confirmed",
            }
            if outcome == "draft_saved":
                allowed_kinds = DRAFT_PROOF_KINDS
            if kind not in allowed_kinds:
                raise ChannelError(422, "posting_confirmation_required", "ต้องมีข้อความยืนยันผลที่ตรงจาก TikTok ก่อนบันทึกผลสำเร็จ")
            if kind in NOTICE_REQUIRED_KINDS and not (isinstance(notice, str) and len(notice.strip()) >= 8):
                # "I looked at the Content page / I confirm" is only evidence when it says what was seen.
                raise ChannelError(422, "posting_confirmation_required", "หลักฐานแบบ reconcile/ยืนยันเองต้องระบุข้อความว่าเห็นอะไร (notice)")
            if kind == "platform_success_notice":
                # TikTok Studio shows a bare "Video published" toast (no "successfully"),
                # and shows it for scheduled posts too -- so the bare form is accepted for
                # `published`, and for `scheduled_on_platform` only when the job really had
                # a schedule (checked against the row below).
                patterns = {
                    "published": _PUBLISHED_NOTICE,
                    "scheduled_on_platform": _SCHEDULED_NOTICE,
                    "draft_saved": _DRAFT_NOTICE,
                }
                notice_text = notice.strip() if isinstance(notice, str) else ""
                bare_ok = outcome == "scheduled_on_platform" and re.fullmatch(_PUBLISHED_NOTICE, notice_text, flags=re.I)
                if not notice_text or not (re.fullmatch(patterns[outcome], notice_text, flags=re.I) or bare_ok):
                    raise ChannelError(422, "posting_confirmation_required", "ต้องมีข้อความยืนยันผลที่ตรงจาก TikTok ก่อนบันทึกผลสำเร็จ")
        receipt = {"outcome": outcome, "source_account": source_account, "proof": deepcopy(proof)}
        receipt_hash = fingerprint(receipt)
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            if (outcome == "scheduled_on_platform" and kind == "platform_success_notice"
                    and not re.fullmatch(_SCHEDULED_NOTICE, str(proof.get("notice") or "").strip(), flags=re.I)
                    and not (row.get("schedule_date") and row.get("schedule_time"))):
                raise ChannelError(422, "posting_confirmation_required", "ข้อความ 'published' ใช้ยืนยันงานตั้งเวลาได้เฉพาะงานที่มีเวลานัดโพสต์")
            intent = effective_intent(row)
            if outcome != "confirmation_unknown":
                # The result must be the one the job was prepared for: a draft job cannot become a post, a post job
                # cannot become a draft, an immediate post cannot become "scheduled".
                if intent == "draft" and outcome != "draft_saved":
                    raise ChannelError(422, "posting_intent_mismatch", "งานนี้เป็นแบบร่าง จึงบันทึกผลเป็นโพสต์/ตั้งเวลาไม่ได้")
                if intent != "draft" and outcome == "draft_saved" and row.get("intent"):
                    raise ChannelError(422, "posting_intent_mismatch", "งานนี้ไม่ใช่แบบร่าง จึงบันทึกผลเป็นแบบร่างไม่ได้")
                if intent == "post_now" and outcome == "scheduled_on_platform" and row.get("intent"):
                    raise ChannelError(422, "posting_intent_mismatch", "งานนี้เป็นโพสต์ทันที จึงบันทึกผลเป็นตั้งเวลาไม่ได้")
                if intent == "schedule" and outcome == "published" and kind == "platform_success_notice":
                    # TikTok shows the same bare "Video published" toast for a scheduled post: it says nothing about WHEN.
                    raise ChannelError(422, "posting_confirmation_required", "งานตั้งเวลาต้องบันทึกเป็น scheduled_on_platform ข้อความ toast เปล่าไม่พอยืนยันว่าเผยแพร่แล้ว")
            if outcome == "draft_saved" and (row.get("schedule_date") or row.get("schedule_time")):
                raise ChannelError(422, "posting_confirmation_required", "งานที่มีเวลานัดโพสต์ไม่ใช่งานแบบร่าง จึงบันทึกผลเป็นแบบร่างไม่ได้")
            if outcome != "confirmation_unknown" and row.get("confirmation_token") and proof.get("confirmation_token") != row["confirmation_token"]:
                if kind not in {"manual_user_confirmation", "user_confirmed", "content_page_reconciled"}:
                    raise ChannelError(422, "posting_confirmation_required", "ข้อความยืนยันไม่ตรงกับการกดโพสต์ของงานนี้")
            if row.get("receipt_hash") == receipt_hash:
                self._fence(row, owner, token, row["revision"], allow_expired=True)
                return deepcopy(row)
            if reconcile and row["status"] == "published":
                self._fence(row, owner, token, row["revision"], allow_expired=True)
                return deepcopy(row)
            self._fence(row, owner, token, revision, allow_expired=reconcile)
            if row["status"] not in ({"claimed", "publishing", "confirmation_unknown"} if reconcile else {"publishing"}):
                if not (reconcile and kind in {"manual_user_confirmation", "user_confirmed"} and row["status"] == "prepared"):
                    raise ChannelError(409, "posting_reconciliation_required", "สถานะงานไม่รับผลนี้ ต้องตรวจงานเดิมก่อน")
            if row["status"] == "confirmation_unknown" and not reconcile:
                raise ChannelError(409, "posting_reconciliation_required", "ต้องยืนยันผลผ่านการตรวจสอบงานเดิม")
            check = account_check(channel_id, row["target_handle"], source_account, strict=row["strict_mode"])
            if check["source_account"] != row.get("attempted_source_account") and row.get("attempted_source_account") is not None:
                raise ChannelError(409, "account_handle_mismatch", "บัญชีของผลลัพธ์ต่างจากบัญชีขณะกดโพสต์")
            now = self.clock()
            row.update(status=outcome, receipt=receipt, receipt_hash=receipt_hash,
                       publish_attempted_at=row.get("publish_attempted_at") or now,
                       attempt=row.get("attempt") or 1,
                       attempted_source_account=row.get("attempted_source_account") or check["source_account"],
                       revision=row["revision"] + 1, updated_at=now)
            self._audit(row, "reconcile" if reconcile else "outcome", outcome=outcome, **check)
            return deepcopy(row)

    def mark_effects_applied(self, channel_id, job_id):
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            row["effects_applied"] = True
            return deepcopy(row)

    def mark_prepare_effects(self, channel_id, job_id, *, error=None):
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            row["prepare_effects_applied"] = error is None
            self._audit(row, "prepare_queue_error" if error else "prepare_queue_applied", error=error)
            return deepcopy(row)

    def cancel(self, channel_id, job_id):
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            if row["status"] in {"cancelled", "published"}:
                return deepcopy(row)
            if row["status"] != "prepared":
                raise ChannelError(409, "posting_job_busy", "ยกเลิกงานที่รับหรือกดโพสต์แล้วไม่ได้ ต้องตรวจผลเดิมก่อน")
            row.update(status="cancelled", revision=row["revision"] + 1)
            self._audit(row, "cancel")
            return deepcopy(row)

    def release(self, channel_id, job_id, owner, token, revision, *, force: bool = False):
        """Cancel a fenced PRE-publish claim. An attempted/final job is never released, with or without force."""
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            self._fence(row, owner, token, row["revision"] if row["status"] in {"cancelled", "published"} else revision, allow_expired=True)
            if row["status"] in {"cancelled", "published"}:
                return deepcopy(row)
            if row.get("publish_attempted_at") or row["status"] in ATTEMPTED_STATUSES:
                # `force` used to override this and made an already-posted export preparable again (duplicate post).
                raise ChannelError(409, "posting_reconciliation_required", "งานที่กดโพสต์แล้วต้องตรวจผล ห้ามยกเลิกสิทธิ์ (force ใช้ไม่ได้)")
            if row["status"] != "claimed" and not force:
                raise ChannelError(409, "posting_reconciliation_required", "งานที่กดโพสต์แล้วต้องตรวจผล ห้ามยกเลิกสิทธิ์")
            row.update(status="cancelled", revision=row["revision"] + 1, updated_at=self.clock())
            self._audit(row, "release", lease_owner=owner, forced=force)
            return deepcopy(row)

    def release_draft(self, channel_id, job_id, *, reason="draft_deleted_by_operator"):
        """Cancel a draft_saved job (the operator deleted the draft on TikTok) so the export may be prepared again.
        Only drafts: a job that published or scheduled is never released here."""
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            if row["status"] == "cancelled":
                return deepcopy(row)
            if row["status"] != "draft_saved":
                raise ChannelError(409, "posting_reconciliation_required", "ยกเลิกได้เฉพาะงานที่บันทึกเป็นแบบร่าง")
            row.update(status="cancelled", revision=row["revision"] + 1, updated_at=self.clock())
            self._audit(row, "release_draft", reason=reason)
            return deepcopy(row)

    def retire_deleted(self, channel_id, job_id, *, reason="deleted_on_platform_by_operator"):
        """The operator deleted the scheduled post / draft on TikTok: retire its job so the export can be prepared again.
        Only a job TikTok had ACCEPTED as scheduled (or a saved draft). A published job is a live post: never retired here."""
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            if row["status"] == "cancelled":
                return deepcopy(row)
            if row["status"] not in {"scheduled_on_platform", "draft_saved"}:
                raise ChannelError(409, "posting_reconciliation_required", "ปิดงานด้วยวิธีนี้ได้เฉพาะงานที่ TikTok รับตั้งเวลา/เป็นแบบร่าง (โพสต์สดแล้วทำไม่ได้)")
            row.update(status="cancelled", revision=row["revision"] + 1, updated_at=self.clock())
            self._audit(row, "retire_deleted", reason=reason)
            return deepcopy(row)

    def update_cover(self, channel_id, job_id, cover_path, *, cover_sha256=None):
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            if row["status"] != "prepared":
                raise ChannelError(409, "posting_payload_locked", "งานที่ Extension รับแล้วแก้ไฟล์ปกไม่ได้ ต้องใช้ snapshot เดิม")
            row["cover_path"] = cover_path
            if "cover_sha256" in row["payload_fields"]:
                row["cover_sha256"] = cover_sha256
            row["revision"] += 1
            row["payload_hash"] = fingerprint({key: row[key] for key in row["payload_fields"]})
            # Prepared jobs may be edited; idempotency key still identifies
            # the original request, while action fencing uses current revision.
            self._audit(row, "cover_update")
            return deepcopy(row)

    def account_audit(self, channel_id, event, check):
        table = DocumentTable("posting_account_audit", lambda: self.path.parent / "store.db",
                              lambda: self.path.parent / "posting_account_audit.json")
        with table.scoped_mutate(channel_id) as rows:
            rows.append({"id": secrets.token_hex(16), "channel_id": channel_id,
                         "event": event, "at": self.clock(), **deepcopy(check)})

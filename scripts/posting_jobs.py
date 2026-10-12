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
FINAL_OUTCOMES = {"published", "scheduled_on_platform", "confirmation_unknown"}


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
            existing_export = next((r for r in rows if r["export_id"] == frozen["export_id"]
                                    and r["status"] != "cancelled"), None)
            if existing_export:
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

    def validate_action(self, channel_id, job_id, owner, token, revision, source_account, *, begin_publish=False, confirmation_token=None):
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            self._fence(row, owner, token, revision)
            if row["status"] != "claimed" or row.get("publish_attempted_at"):
                raise ChannelError(409, "posting_reconciliation_required", "งานนี้ไม่อนุญาตให้กดโพสต์ซ้ำ")
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
        if outcome != "confirmation_unknown":
            notice = proof.get("notice")
            patterns = {
                "published": r"(?:(?:video |post )?(?:posted|published) successfully|(?:โพสต์|เผยแพร่)(?:วิดีโอ)?สำเร็จ)[.!]?",
                "scheduled_on_platform": r"(?:(?:video |post )?scheduled successfully|(?:ตั้งเวลา|กำหนดเวลา)(?:โพสต์|วิดีโอ)?สำเร็จ)[.!]?",
            }
            if (proof.get("kind") != "platform_success_notice" or not isinstance(notice, str)
                    or not re.fullmatch(patterns[outcome], notice.strip(), flags=re.I)):
                raise ChannelError(422, "posting_confirmation_required", "ต้องมีข้อความยืนยันผลที่ตรงจาก TikTok ก่อนบันทึกผลสำเร็จ")
        receipt = {"outcome": outcome, "source_account": source_account, "proof": deepcopy(proof)}
        receipt_hash = fingerprint(receipt)
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            if outcome != "confirmation_unknown" and row.get("confirmation_token") and proof.get("confirmation_token") != row["confirmation_token"]:
                raise ChannelError(422, "posting_confirmation_required", "ข้อความยืนยันไม่ตรงกับการกดโพสต์ของงานนี้")
            if row.get("receipt_hash") == receipt_hash:
                self._fence(row, owner, token, row["revision"], allow_expired=True)
                return deepcopy(row)
            self._fence(row, owner, token, revision, allow_expired=reconcile)
            if row["status"] not in ({"publishing", "confirmation_unknown"} if reconcile else {"publishing"}):
                raise ChannelError(409, "posting_reconciliation_required", "สถานะงานไม่รับผลนี้ ต้องตรวจงานเดิมก่อน")
            if row["status"] == "confirmation_unknown" and not reconcile:
                raise ChannelError(409, "posting_reconciliation_required", "ต้องยืนยันผลผ่านการตรวจสอบงานเดิม")
            check = account_check(channel_id, row["target_handle"], source_account, strict=row["strict_mode"])
            if check["source_account"] != row.get("attempted_source_account"):
                raise ChannelError(409, "account_handle_mismatch", "บัญชีของผลลัพธ์ต่างจากบัญชีขณะกดโพสต์")
            row.update(status=outcome, receipt=receipt, receipt_hash=receipt_hash,
                       revision=row["revision"] + 1, updated_at=self.clock())
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
            if row["status"] != "prepared":
                raise ChannelError(409, "posting_job_busy", "ยกเลิกงานที่รับหรือกดโพสต์แล้วไม่ได้ ต้องตรวจผลเดิมก่อน")
            row.update(status="cancelled", revision=row["revision"] + 1)
            self._audit(row, "cancel")
            return deepcopy(row)

    def release(self, channel_id, job_id, owner, token, revision):
        """Cancel a fenced pre-publish claim; attempted jobs are never releasable."""
        with self.table.scoped_mutate(channel_id) as rows:
            row = self._find(rows, job_id)
            self._fence(row, owner, token, row["revision"] if row["status"] == "cancelled" else revision, allow_expired=True)
            if row["status"] == "cancelled":
                return deepcopy(row)
            if row["status"] != "claimed" or row.get("publish_attempted_at"):
                raise ChannelError(409, "posting_reconciliation_required", "งานที่กดโพสต์แล้วต้องตรวจผล ห้ามยกเลิกสิทธิ์")
            row.update(status="cancelled", revision=row["revision"] + 1, updated_at=self.clock())
            self._audit(row, "release", lease_owner=owner)
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

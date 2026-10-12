"""Explicit user-reviewed scheduled-publication reconciliation.

This is a manual review attestation, not an automated platform API assertion.
An exact public TikTok video URL must match the frozen accepted receipt. The
caller must explicitly confirm they reviewed that publication; metrics and
elapsed schedule time cannot establish publication.
"""
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from scripts import config
from scripts.channel_scope import ChannelScope, get_channel_scope, require_writable
from scripts.channel_workflows import get_workflow_scope
from scripts.channel_store import ChannelError, normalize_handle
from scripts.publication_observations import PublicationObservationStore
from scripts.publication_effects import PublicationEffects

router = APIRouter(prefix="/api/tiktok-autopost/jobs", tags=["publication-observations"])


class PublicationObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_account: str
    platform_video_id: str = Field(pattern=r"^[0-9]{8,32}$")
    observed_published_at: str
    evidence_url: str
    review_confirmation: Literal["reviewed_published_video"]
    idempotency_key: str = Field(min_length=1, max_length=200)
    expected_job_revision: int = Field(ge=1)


def _services():
    root = Path(config.BASE_DIR)
    observations = PublicationObservationStore(root)
    return observations, PublicationEffects(root, observations=observations, jobs=observations.jobs)


def _reviewed_evidence(req, channel_id, job_id):
    parts = urlsplit(req.evidence_url)
    account = normalize_handle(req.source_account)
    expected_path = f"/{account}/video/{req.platform_video_id}"
    if parts.scheme != "https" or parts.netloc.lower() not in {"www.tiktok.com", "tiktok.com"} or parts.path.rstrip("/") != expected_path or parts.query or parts.fragment:
        raise ChannelError(422, "publication_evidence_url_invalid", "ต้องใช้ลิงก์วิดีโอ TikTok ที่ตรงบัญชีและรหัสโพสต์ของงานนี้")
    return {"kind": "platform_publication", "source": "reviewed_platform_record", "published": True,
            "channel_id": channel_id, "job_id": job_id, "source_account": account,
            "platform_video_id": req.platform_video_id, "evidence_url": req.evidence_url,
            "review_confirmation": req.review_confirmation}


@router.get("/{job_id}/publication-observations")
def list_publication_observations(job_id: str, scope: ChannelScope = Depends(get_channel_scope)):
    observations, _ = _services()
    return {"items": observations.for_job(scope.channel_id, job_id)}


@router.post("/{job_id}/publication-observations")
def review_publication(job_id: str, req: PublicationObservationRequest,
                       scope: ChannelScope = Depends(get_workflow_scope)):
    require_writable(scope)
    observations, effects = _services()
    evidence = _reviewed_evidence(req, scope.channel_id, job_id)
    event = observations.observe(scope.channel_id, job_id, req.source_account, req.platform_video_id,
                                 req.observed_published_at, evidence, idempotency_key=req.idempotency_key,
                                 expected_job_revision=req.expected_job_revision)
    if event["status"] == "verified":
        event = effects.apply(scope.channel_id, event["id"])
    return {"observation": event, "review_mode": "manual_platform_review",
            "next_action": "review_exact_linkage" if event["status"] == "waiting_linkage" else None}

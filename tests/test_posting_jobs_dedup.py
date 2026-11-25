"""Unit tests for video_sha256 duplicate protection in scripts/posting_jobs.py (E3)."""
import hashlib
import pytest

from scripts.channel_store import ChannelError
from scripts.posting_jobs import PostingJobStore


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _payload(export_id: str, sha: str, **extra):
    base = {
        "export_id": export_id,
        "video_path": f"04_Exports/Ready_to_post/{export_id}.mp4",
        "target_handle": "@mainuser",
        "channel_revision": 1,
        "account_binding": {"status": "verified"},
        "strict_mode": False,
        "video_sha256": sha,
        "caption": "caption",
        "cover_path": None,
        "queue_id": None,
    }
    base.update(extra)
    return base


def test_prepare_blocks_duplicate_video_sha256_across_different_export_ids(tmp_path):
    jobs = PostingJobStore(tmp_path, clock=lambda: 1000.0, lease_seconds=30)
    sha = _sha("same-video-bytes")
    first = jobs.prepare("main", _payload("exp-old", sha))
    claimed = jobs.claim("main", first["job_id"], "ext-1")
    attempt = jobs.validate_action(
        "main",
        claimed["job_id"],
        claimed["lease_owner"],
        claimed["lease_token"],
        claimed["revision"],
        "@mainuser",
        begin_publish=True,
    )
    jobs.acknowledge(
        "main",
        attempt["job_id"],
        attempt["lease_owner"],
        attempt["lease_token"],
        attempt["revision"],
        "@mainuser",
        "scheduled_on_platform",
        {"kind": "platform_success_notice", "notice": "Video scheduled successfully"},
    )

    # Same video bytes re-registered under a different export_id must be rejected
    with pytest.raises(ChannelError) as exc:
        jobs.prepare("main", _payload("exp-reexport", sha))
    assert exc.value.status_code == 409
    assert exc.value.code == "posting_duplicate_video_sha256"


def test_prepare_blocks_duplicate_video_sha256_when_existing_is_published_or_prepared(tmp_path):
    jobs = PostingJobStore(tmp_path, clock=lambda: 1000.0, lease_seconds=30)
    sha_pub = _sha("published-bytes")
    j1 = jobs.prepare("main", _payload("exp-pub-1", sha_pub))
    c1 = jobs.claim("main", j1["job_id"], "ext-1")
    a1 = jobs.validate_action("main", c1["job_id"], c1["lease_owner"], c1["lease_token"], c1["revision"], "@mainuser", begin_publish=True)
    jobs.acknowledge("main", a1["job_id"], a1["lease_owner"], a1["lease_token"], a1["revision"], "@mainuser", "published", {"kind": "platform_success_notice", "notice": "Posted successfully"})

    with pytest.raises(ChannelError) as exc1:
        jobs.prepare("main", _payload("exp-pub-2", sha_pub))
    assert exc1.value.code == "posting_duplicate_video_sha256"

    sha_prep = _sha("prepared-bytes")
    jobs.prepare("main", _payload("exp-prep-1", sha_prep))
    with pytest.raises(ChannelError) as exc2:
        jobs.prepare("main", _payload("exp-prep-2", sha_prep))
    assert exc2.value.code == "posting_duplicate_video_sha256"


def test_prepare_allows_after_cancel_and_isolates_channels_and_distinct_sha(tmp_path):
    jobs = PostingJobStore(tmp_path, clock=lambda: 1000.0, lease_seconds=30)
    sha = _sha("reusable-after-cancel")
    j1 = jobs.prepare("main", _payload("exp-1", sha))
    jobs.cancel("main", j1["job_id"])

    # Cancelled job no longer blocks re-preparing under another export_id
    j2 = jobs.prepare("main", _payload("exp-2", sha))
    assert j2["status"] == "prepared"

    # Distinct SHA-256 is allowed on same channel
    j3 = jobs.prepare("main", _payload("exp-3", _sha("different-bytes")))
    assert j3["status"] == "prepared"

    # Same SHA-256 on another channel is channel-scoped (allowed)
    j_other = jobs.prepare("second", _payload("exp-other-ch", sha, target_handle="@seconduser", strict_mode=True))
    assert j_other["channel_id"] == "second"

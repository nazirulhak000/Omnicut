"""Episode (EP) numbers: the list, the "how many went out through the app" summary, and the counter setting."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from scripts.channel_scope import ChannelScope, get_channel_scope, require_writable
from scripts.episode_registry import EpisodeRegistry
from scripts.posting_jobs import PostingJobStore
from scripts import config

router = APIRouter(prefix="/api/episodes", tags=["episodes"])

# a job in one of these states means the clip really left through the app (a live post or a TikTok-accepted schedule)
SENT_STATUSES = {"published", "scheduled_on_platform"}


def _channel(scope: Any) -> str:
    return scope.channel_id if isinstance(scope, ChannelScope) else "main"


def registry() -> EpisodeRegistry:
    return EpisodeRegistry(config.BASE_DIR)


def build_listing(channel_id: str) -> Dict[str, Any]:
    reg = registry()
    items = reg.list(channel_id)
    by_export = {export_id: row["episode_no"] for row in items for export_id in row.get("export_ids", [])}
    sent: Dict[int, Dict[str, Any]] = {}
    for job in PostingJobStore(config.BASE_DIR).table.scoped_load(channel_id):
        number = by_export.get(job.get("export_id"))
        if number is None or job.get("status") not in SENT_STATUSES:
            continue
        previous = sent.get(number)
        if previous is None or float(job.get("updated_at") or 0) > float(previous.get("updated_at") or 0):
            sent[number] = {"status": job["status"], "job_id": job["job_id"], "updated_at": job.get("updated_at"),
                            "schedule_date": job.get("schedule_date"), "schedule_time": job.get("schedule_time")}
    for row in items:
        row["sent_via_app"] = sent.get(row["episode_no"])
    return {
        "next": reg.next_number(channel_id),
        "items": items,
        "summary": {
            "assigned": len(items),
            "sent_via_app": len(sent),
            "first": items[0]["episode_no"] if items else None,
            "last": items[-1]["episode_no"] if items else None,
        },
    }


@router.get("")
def list_episodes(scope: ChannelScope = Depends(get_channel_scope)):
    return build_listing(_channel(scope))


class NextNumberRequest(BaseModel):
    next: int = Field(ge=1, le=999_999_999)


@router.put("/next")
def set_next_number(req: NextNumberRequest, scope: ChannelScope = Depends(get_channel_scope)):
    if isinstance(scope, ChannelScope) and not scope.is_implicit_default:
        require_writable(scope)
    return {"next": registry().set_next(_channel(scope), req.next)}

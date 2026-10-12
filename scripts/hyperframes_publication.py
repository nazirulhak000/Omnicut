"""Project a verified publication onto the exact frozen Gadget render artifact.

Runs inside PublicationEffects' existing durable parent/angle phase. A later
approved master never receives the publication of an older historical artifact.
"""
from copy import deepcopy
from pathlib import Path

from scripts.channel_store import ChannelError
from scripts.gadget_media_campaign import CampaignStore, _CAMPAIGNS_LOCK
from scripts.hyperframes_sources import HyperFramesSources, slot_fingerprint
from scripts.posting_jobs import fingerprint


def apply_gadget_publication(root, job, event, *, repository=None):
    root = Path(root).resolve()
    binding = job.get("source_binding") or {}
    if binding.get("type") != "gadget_project":
        return {"applied": False, "reason": "not_gadget"}
    channel = event["channel_id"]
    receipt = job.get("receipt") or {}
    if (job.get("channel_id") != channel or job.get("id") != event.get("job_id")
            or job.get("export_id") != event.get("export_id") or job.get("status") != "scheduled_on_platform"
            or event.get("status") != "verified" or receipt.get("outcome") != "scheduled_on_platform"
            or job.get("receipt_hash") != event.get("scheduled_receipt_hash")
            or fingerprint(receipt) != event.get("scheduled_receipt_hash")
            or not (receipt.get("proof") or {}).get("platform_post_id")
            or str((receipt.get("proof") or {}).get("platform_post_id")) != event.get("platform_video_id")
            or receipt.get("source_account") != event.get("source_account")):
        raise ChannelError(409, "hyperframes_publication_conflict", "Publication does not match the frozen scheduled Gadget job")
    sources = HyperFramesSources(root, gadget_repository=repository)
    repo = sources.gadgets.for_channel(channel)
    with repo._lock:
        project = sources.gadget(channel, binding)
        matches = [item for item in project.artifacts if item.get("artifact_id") == job.get("source_artifact_id")
                   and item.get("kind") == "render"]
        if len(matches) != 1:
            raise ChannelError(409, "hyperframes_publication_artifact_missing", "The original Gadget render artifact is missing or ambiguous")
        artifact = matches[0]
        if (artifact.get("export_id") != event["export_id"] or not artifact.get("sha256")
                or artifact["sha256"] != job.get("video_sha256")):
            raise ChannelError(409, "hyperframes_publication_artifact_changed", "Frozen Gadget artifact/export hash no longer matches publication")
        if binding.get("slot_id") and (not job.get("source_slot_fingerprint")
                or artifact.get("source_slot_fingerprint") != job["source_slot_fingerprint"]):
            raise ChannelError(409, "hyperframes_publication_artifact_changed", "Frozen Gadget campaign slot differs from the original render snapshot")
        def path(value):
            result = Path(str(value or ""))
            return sources._safe(result if result.is_absolute() else root / result)
        if path(artifact.get("path")) != path(job.get("video_path")):
            raise ChannelError(409, "hyperframes_publication_artifact_changed", "Gadget artifact no longer refers to the original frozen video")
        previous = artifact.get("publication")
        url = f"https://www.tiktok.com/{event['source_account']}/video/{event['platform_video_id']}"
        identity = {"observation_id": event["id"], "job_id": event["job_id"], "export_id": event["export_id"],
                    "platform_video_id": event["platform_video_id"], "tiktok_url": url,
                    "published_at": event["observed_published_at"], "source_account": event["source_account"]}
        if previous and any(previous.get(key) != value for key, value in identity.items()):
            raise ChannelError(409, "hyperframes_publication_artifact_conflict", "Gadget artifact already identifies another publication")
        if previous and artifact.get("published") is True:
            # The source commit can precede the durable effect marker. Preserve
            # the first projection even if another master was approved later;
            # repair the repository's derived stage/index files from current data.
            for directory in repo.roots.project_layout(project.project_id).values():
                sources._safe(directory)
            sources._safe(repo.roots.docs)
            repo.save(project)
            return {"applied": True, "current_master": previous["current_master_at_projection"],
                    "slot_projection": deepcopy(previous["slot_projection"])}
        current_master = project.approved_master_id == artifact["artifact_id"] and artifact.get("approved") is True
        slot_result = {"status": "not_bound"}
        if binding.get("campaign_id"):
            slot_result = _project_slot(sources, channel, binding, project, job, current_master)
        publication = {**identity, "current_master_at_projection": current_master, "slot_projection": slot_result}
        artifact.update(publication=deepcopy(publication), publication_observation_id=event["id"],
                        published=True, published_at=event["observed_published_at"], tiktok_url=url)
        if current_master:
            project.status = "published"
            project.metrics.update(published_at=event["observed_published_at"],
                                   publication_observation_id=event["id"], platform_video_id=event["platform_video_id"],
                                   tiktok_url=url, published_export_id=event["export_id"])
        for directory in repo.roots.project_layout(project.project_id).values():
            sources._safe(directory)
        sources._safe(repo.roots.docs)
        repo.save(project)
        return {"applied": True, "current_master": current_master, "slot_projection": slot_result}


def _project_slot(sources, channel, binding, project, job, current_master):
    if not current_master:
        return {"status": "skipped", "reason": "newer_master"}
    link = {"campaign_id": binding["campaign_id"], "slot_id": binding["slot_id"]}
    if link not in project.campaign_links:
        return {"status": "skipped", "reason": "link_changed"}
    store = CampaignStore(sources._safe(sources.root / "_Docs/gadget_media_campaigns.json"), channel_id=channel)
    with _CAMPAIGNS_LOCK:
        try:
            campaign = store.get(binding["campaign_id"])
            slot = next(item for item in campaign.slots if item.slot_id == binding["slot_id"])
        except (KeyError, StopIteration):
            return {"status": "skipped", "reason": "slot_missing"}
        if campaign.channel_id != channel or slot.product_project_id != project.project_id:
            return {"status": "skipped", "reason": "slot_retargeted"}
        if not job.get("source_slot_fingerprint") or slot_fingerprint(slot.to_dict()) != job["source_slot_fingerprint"]:
            return {"status": "skipped", "reason": "slot_content_changed"}
        if not slot.ready_to_publish:
            return {"status": "skipped", "reason": "slot_not_ready"}
        if slot.status != "published":
            store.update_slot(binding["campaign_id"], binding["slot_id"], {"status": "published"})
        return {"status": "applied", **link}

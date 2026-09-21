"""Adapter between ProductVideoProject and the shared Timeline Document v2."""

from __future__ import annotations

from typing import Any, Dict, List

from scripts.gadget_media_project import ProductVideoProject, ProductVideoValidationError, utc_now


def _tracks() -> List[Dict[str, Any]]:
    return [
        {"id": "track-v1", "type": "video", "name": "Product Footage", "locked": False, "muted": False, "visible": True, "z_index": 10},
        {"id": "track-o1", "type": "overlay", "name": "Editorial Overlays", "locked": False, "muted": False, "visible": True, "z_index": 30},
        {"id": "track-o2", "type": "caption", "name": "Captions", "locked": False, "muted": False, "visible": True, "z_index": 40},
        {"id": "track-a1", "type": "audio", "name": "Voice", "locked": False, "muted": False, "visible": True, "volume": 1.0, "stem_key": "voice"},
        {"id": "track-a2", "type": "audio", "name": "SFX", "locked": False, "muted": False, "visible": True, "volume": 0.28, "stem_key": "sfx"},
        {"id": "track-a3", "type": "audio", "name": "BGM", "locked": False, "muted": False, "visible": True, "volume": 0.12, "stem_key": "bgm"},
    ]


def timeline_duration(clips: List[Dict[str, Any]]) -> float:
    total = 0.0
    for clip in clips:
        start = float(clip.get("trim_start") or 0)
        end = float(clip.get("trim_end") or start)
        speed = max(0.25, min(4.0, float(clip.get("speed") or 1)))
        total += max(0, end - start) / speed + max(0, float(clip.get("freeze_tail") or 0))
    return round(total, 3)


class GadgetMediaTimelineAdapter:
    @classmethod
    def build(cls, project: ProductVideoProject) -> Dict[str, Any]:
        identity = project.product_identity
        if not str(identity.get("brand") or "").strip() or not str(identity.get("model") or "").strip():
            raise ProductVideoValidationError("brand and model are required before building timeline")
        sources = {str(item.get("source_id")): item for item in project.source_assets}
        blocks = {str(item.get("block_id")): item for item in (project.story.get("blocks") or [])}
        shots = ((project.edit.get("edl") or {}).get("shots") or [])
        if not shots:
            raise ProductVideoValidationError("at least one EDL shot is required before building timeline")

        clips: List[Dict[str, Any]] = []
        for index, shot in enumerate(shots):
            source_id = str(shot.get("source_id") or "")
            source = sources.get(source_id)
            if not source:
                raise ProductVideoValidationError(f"EDL shot references unknown source_id: {source_id}")
            block_id = str(shot.get("story_block_id") or "")
            block = blocks.get(block_id, {})
            start = float(shot.get("source_start") or 0)
            end = float(shot.get("source_end") or 0)
            if end <= start:
                raise ProductVideoValidationError(f"EDL shot {index + 1} must have source_end after source_start")
            clips.append({
                "id": str(shot.get("shot_id") or f"shot-{index + 1:02d}"),
                "track_id": "track-v1",
                "source_id": source_id,
                "source_path": str(source.get("local_path") or ""),
                "trim_start": start,
                "trim_end": end,
                "duration": round(end - start, 3),
                "speed": float(shot.get("speed") or 1),
                "transition_in": str(shot.get("transition_in") or "cut"),
                "story_block_id": block_id,
                "claim_ids": list(block.get("claim_ids") or []),
                "evidence_ids": list(block.get("evidence_ids") or []),
                "reason": str(shot.get("reason") or ""),
                "keyframes": list(shot.get("keyframes") or []),
            })

        return {
            "schema_version": 2,
            "workspace_scope": "gadget_media",
            "project_id": project.project_id,
            "module": "gadget_media",
            "output": {"width": 1080, "height": 1920, "fps": 30},
            "tracks": _tracks(),
            "clips": clips,
            "clip_list": clips,
            "cues": [],
            "overlays": [],
            "duration": timeline_duration(clips),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }

    @classmethod
    def normalize_saved(cls, project_id: str, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ProductVideoValidationError("timeline must be an object")
        timeline = dict(value)
        timeline["schema_version"] = 2
        timeline["workspace_scope"] = "gadget_media"
        timeline["project_id"] = project_id
        timeline.setdefault("module", "gadget_media")
        timeline.setdefault("tracks", _tracks())
        clips = timeline.get("clips") or timeline.get("clip_list") or []
        if not isinstance(clips, list):
            raise ProductVideoValidationError("timeline clips must be a list")
        timeline["clips"] = clips
        timeline["clip_list"] = clips
        timeline["duration"] = timeline_duration(clips)
        timeline["updated_at"] = utc_now()
        timeline.setdefault("output", {"width": 1080, "height": 1920, "fps": 30})
        timeline.setdefault("cues", [])
        timeline.setdefault("overlays", [])
        return timeline


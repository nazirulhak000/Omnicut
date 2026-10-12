"""Domain model and persistence for the non-commerce Gadget Media campaign.

This module is intentionally separate from ProductStore and the affiliate
review workflow.  A Gadget Media campaign is a 21-slot editorial plan whose
source provenance must be reviewable before a slot can become publish-ready.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import uuid

from scripts.config import BASE_DIR
from scripts.channel_ownership import resolve_store_scope
from scripts.channel_store import ChannelError
import threading
from functools import wraps


CAMPAIGNS_FILE = BASE_DIR / "_Docs" / "gadget_media_campaigns.json"
CAMPAIGN_TYPE = "gadget_media"
ACCOUNT_ROLE = "gadget_media"
SERIES = (
    "watch_before_buy",
    "spec_in_plain_language",
    "real_vs_marketing",
)
STATUSES = ("planned", "scripted", "recorded", "edited", "published")
RIGHTS_BASES = (
    "self_recorded",
    "licensed_press_kit",
    "commentary_excerpt",
    "original_ai_visual",
)
DEFAULT_TARGET_AUDIENCE = "คนใช้มือถือทั่วไปที่อยากซื้อ Gadget คุ้มและเข้าใจง่าย"


class CampaignValidationError(ValueError):
    """Raised when campaign data cannot satisfy the domain contract."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, field_name: str, *, required: bool = True, max_length: int = 500) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise CampaignValidationError(f"{field_name} must be text")
    value = value.strip()
    if required and not value:
        raise CampaignValidationError(f"{field_name} is required")
    if len(value) > max_length:
        raise CampaignValidationError(f"{field_name} is too long")
    return value


@dataclass
class SourceRef:
    source_url: str
    rights_basis: str
    creator_or_brand: str = ""
    usage_note: str = ""
    rights_reviewed: bool = False
    source_id: str = field(default_factory=lambda: f"src-{uuid.uuid4().hex[:12]}")
    captured_at: str = field(default_factory=_now)

    def review_errors(self) -> List[str]:
        errors: List[str] = []
        if not self.source_url.strip():
            errors.append("source_url is required")
        if self.rights_basis not in RIGHTS_BASES:
            errors.append(f"rights_basis must be one of {', '.join(RIGHTS_BASES)}")
        if self.rights_basis in {"licensed_press_kit", "commentary_excerpt"} and not self.rights_reviewed:
            errors.append("source rights review is required")
        if self.rights_basis == "commentary_excerpt" and not self.usage_note.strip():
            errors.append("commentary_excerpt requires usage_note")
        return errors

    @property
    def publishable(self) -> bool:
        return not self.review_errors()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_url": self.source_url,
            "rights_basis": self.rights_basis,
            "creator_or_brand": self.creator_or_brand,
            "usage_note": self.usage_note,
            "rights_reviewed": self.rights_reviewed,
            "captured_at": self.captured_at,
            "publishable": self.publishable,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceRef":
        if not isinstance(data, dict):
            raise CampaignValidationError("source reference must be an object")
        return cls(
            source_id=str(data.get("source_id") or f"src-{uuid.uuid4().hex[:12]}"),
            source_url=str(data.get("source_url") or ""),
            rights_basis=str(data.get("rights_basis") or ""),
            creator_or_brand=str(data.get("creator_or_brand") or ""),
            usage_note=str(data.get("usage_note") or ""),
            rights_reviewed=bool(data.get("rights_reviewed", False)),
            captured_at=str(data.get("captured_at") or _now()),
        )


@dataclass
class ContentMetrics:
    views: int = 0
    completion_rate: float = 0.0
    comments: int = 0
    follows: int = 0

    @property
    def follows_per_1000_views(self) -> float:
        return round((self.follows / self.views) * 1000, 2) if self.views else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "views": self.views,
            "completion_rate": self.completion_rate,
            "comments": self.comments,
            "follows": self.follows,
            "follows_per_1000_views": self.follows_per_1000_views,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ContentMetrics":
        data = data or {}
        return cls(
            views=max(0, int(data.get("views", 0))),
            completion_rate=max(0.0, min(100.0, float(data.get("completion_rate", 0.0)))),
            comments=max(0, int(data.get("comments", 0))),
            follows=max(0, int(data.get("follows", 0))),
        )


@dataclass
class ContentSlot:
    slot_id: str
    series: str
    hook: str
    target_audience: str = DEFAULT_TARGET_AUDIENCE
    status: str = "planned"
    script: str = ""
    product_project_id: Optional[str] = None
    source_refs: List[SourceRef] = field(default_factory=list)
    metrics: ContentMetrics = field(default_factory=ContentMetrics)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def validate(self) -> None:
        _text(self.slot_id, "slot_id", max_length=80)
        if self.series not in SERIES:
            raise CampaignValidationError(f"series must be one of {', '.join(SERIES)}")
        if self.status not in STATUSES:
            raise CampaignValidationError(f"status must be one of {', '.join(STATUSES)}")
        _text(self.hook, "hook", max_length=240)
        _text(self.target_audience, "target_audience", max_length=300)
        if not isinstance(self.source_refs, list):
            raise CampaignValidationError("source_refs must be a list")
        if not isinstance(self.metrics, ContentMetrics):
            raise CampaignValidationError("metrics must be ContentMetrics")

    def publish_readiness_errors(self) -> List[str]:
        errors: List[str] = []
        try:
            self.validate()
        except CampaignValidationError as exc:
            errors.append(str(exc))
        if self.status not in {"edited", "published"}:
            errors.append("slot must be edited before publish readiness")
        if not self.script.strip():
            errors.append("script is required before publish readiness")
        if not self.source_refs:
            errors.append("at least one source reference is required")
        for source in self.source_refs:
            errors.extend(f"{source.source_id}: {error}" for error in source.review_errors())
        return errors

    @property
    def ready_to_publish(self) -> bool:
        return not self.publish_readiness_errors()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "series": self.series,
            "hook": self.hook,
            "target_audience": self.target_audience,
            "status": self.status,
            "script": self.script,
            "product_project_id": self.product_project_id,
            "source_refs": [source.to_dict() for source in self.source_refs],
            "metrics": self.metrics.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ready_to_publish": self.ready_to_publish,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentSlot":
        if not isinstance(data, dict):
            raise CampaignValidationError("content slot must be an object")
        slot = cls(
            slot_id=str(data.get("slot_id") or ""),
            series=str(data.get("series") or ""),
            hook=str(data.get("hook") or ""),
            target_audience=str(data.get("target_audience") or DEFAULT_TARGET_AUDIENCE),
            status=str(data.get("status") or "planned"),
            script=str(data.get("script") or ""),
            product_project_id=str(data.get("product_project_id") or "") or None,
            source_refs=[SourceRef.from_dict(item) for item in (data.get("source_refs") or [])],
            metrics=ContentMetrics.from_dict(data.get("metrics")),
            created_at=str(data.get("created_at") or _now()),
            updated_at=str(data.get("updated_at") or _now()),
        )
        slot.validate()
        return slot


@dataclass
class GadgetMediaCampaign:
    campaign_id: str
    name: str
    slots: List[ContentSlot]
    channel_id: Optional[str] = None
    campaign_type: str = CAMPAIGN_TYPE
    account_role: str = ACCOUNT_ROLE
    goal: str = "สร้างผู้ติดตามแบบ organic จากคอนเทนต์ Gadget ที่เข้าใจง่าย"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def validate(self) -> None:
        from scripts.channel_store import is_valid_channel_id
        if self.channel_id is not None and not is_valid_channel_id(self.channel_id):
            raise CampaignValidationError("invalid channel_id")
        _text(self.campaign_id, "campaign_id", max_length=100)
        _text(self.name, "name", max_length=200)
        if self.campaign_type != CAMPAIGN_TYPE:
            raise CampaignValidationError(f"campaign_type must be {CAMPAIGN_TYPE}")
        if self.account_role != ACCOUNT_ROLE:
            raise CampaignValidationError(f"account_role must be {ACCOUNT_ROLE}")
        if not isinstance(self.slots, list) or not self.slots:
            raise CampaignValidationError("campaign must contain content slots")
        slot_ids = set()
        for slot in self.slots:
            slot.validate()
            if slot.slot_id in slot_ids:
                raise CampaignValidationError(f"duplicate slot_id: {slot.slot_id}")
            slot_ids.add(slot.slot_id)

    def readiness_summary(self) -> Dict[str, Any]:
        self.validate()
        blockers = {
            slot.slot_id: slot.publish_readiness_errors()
            for slot in self.slots
            if not slot.ready_to_publish
        }
        return {
            "campaign_id": self.campaign_id,
            **({"channel_id": self.channel_id} if self.channel_id is not None else {}),
            "total_slots": len(self.slots),
            "ready_slots": len(self.slots) - len(blockers),
            "blocked_slots": len(blockers),
            "blockers": blockers,
        }

    def analytics_summary(self) -> Dict[str, Any]:
        self.validate()
        total_views = sum(slot.metrics.views for slot in self.slots)
        total_comments = sum(slot.metrics.comments for slot in self.slots)
        total_follows = sum(slot.metrics.follows for slot in self.slots)
        slots_with_views = [s for s in self.slots if s.metrics.views > 0]
        avg_completion = (
            round(sum(s.metrics.completion_rate for s in slots_with_views) / len(slots_with_views), 1)
            if slots_with_views else 0.0
        )
        overall_f_per_1k = (
            round((total_follows / total_views) * 1000, 2)
            if total_views > 0 else 0.0
        )
        series_breakdown: Dict[str, Any] = {}
        for s_key in SERIES:
            s_slots = [s for s in self.slots if s.series == s_key]
            s_views = sum(s.metrics.views for s in s_slots)
            s_follows = sum(s.metrics.follows for s in s_slots)
            s_comments = sum(s.metrics.comments for s in s_slots)
            s_with_views = [s for s in s_slots if s.metrics.views > 0]
            s_avg_completion = (
                round(sum(s.metrics.completion_rate for s in s_with_views) / len(s_with_views), 1)
                if s_with_views else 0.0
            )
            s_f_per_1k = round((s_follows / s_views) * 1000, 2) if s_views > 0 else 0.0
            series_breakdown[s_key] = {
                "total_slots": len(s_slots),
                "published_slots": len([s for s in s_slots if s.status == "published"]),
                "views": s_views,
                "follows": s_follows,
                "comments": s_comments,
                "avg_completion_rate": s_avg_completion,
                "follows_per_1000_views": s_f_per_1k,
            }
        return {
            "campaign_id": self.campaign_id,
            **({"channel_id": self.channel_id} if self.channel_id is not None else {}),
            "total_views": total_views,
            "total_comments": total_comments,
            "total_follows": total_follows,
            "avg_completion_rate": avg_completion,
            "follows_per_1000_views": overall_f_per_1k,
            "series": series_breakdown,
        }

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "campaign_id": self.campaign_id,
            **({"channel_id": self.channel_id} if self.channel_id is not None else {}),
            "name": self.name,
            "campaign_type": self.campaign_type,
            "account_role": self.account_role,
            "goal": self.goal,
            "slots": [slot.to_dict() for slot in self.slots],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GadgetMediaCampaign":
        if not isinstance(data, dict):
            raise CampaignValidationError("campaign must be an object")
        campaign = cls(
            campaign_id=str(data.get("campaign_id") or ""),
            channel_id=data.get("channel_id"),
            name=str(data.get("name") or ""),
            campaign_type=str(data.get("campaign_type") or ""),
            account_role=str(data.get("account_role") or ""),
            goal=str(data.get("goal") or ""),
            slots=[ContentSlot.from_dict(item) for item in (data.get("slots") or [])],
            created_at=str(data.get("created_at") or _now()),
            updated_at=str(data.get("updated_at") or _now()),
        )
        campaign.validate()
        return campaign


def create_starter_campaign(
    name: str = "Gadget Media — 30 วัน 21 คลิป",
    *,
    campaign_id: Optional[str] = None,
    target_audience: str = DEFAULT_TARGET_AUDIENCE,
) -> GadgetMediaCampaign:
    series_plan = ([SERIES[0]] * 9) + ([SERIES[1]] * 6) + ([SERIES[2]] * 6)
    hooks = {
        SERIES[0]: "คลิปนี้ดูเหมือนคุ้ม แต่มีจุดหนึ่งที่ต้องระวัง",
        SERIES[1]: "สเปกคำนี้แปลเป็นการใช้งานจริงว่าอะไร",
        SERIES[2]: "ของจริงทำได้ตามคำโฆษณาหรือไม่",
    }
    slots = [
        ContentSlot(
            slot_id=f"gadget-{index:02d}",
            series=series,
            hook=hooks[series],
            target_audience=target_audience,
        )
        for index, series in enumerate(series_plan, start=1)
    ]
    campaign = GadgetMediaCampaign(
        campaign_id=campaign_id or f"gadget-media-{uuid.uuid4().hex[:10]}",
        name=name,
        slots=slots,
    )
    campaign.validate()
    return campaign


_CAMPAIGNS_LOCK = threading.RLock()


def _locked(method):
    @wraps(method)
    def call(*args, **kwargs):
        with _CAMPAIGNS_LOCK:
            return method(*args, **kwargs)
    return call


class CampaignStore:
    """Atomic JSON persistence with an injectable path for deterministic tests."""

    def __init__(self, path: Optional[Path] = None, *, channel_id: Optional[str] = None):
        self.channel_id = channel_id
        self.path = Path(path or CAMPAIGNS_FILE)

    def _load_raw(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CampaignValidationError("campaign store is unreadable") from exc
        if not isinstance(data, list):
            raise CampaignValidationError("campaign store must contain a list")
        return data

    def list(self) -> List[GadgetMediaCampaign]:
        return [GadgetMediaCampaign.from_dict(item) for item in self._load_raw() if resolve_store_scope(self.channel_id).owns(item)]

    def get(self, campaign_id: str) -> GadgetMediaCampaign:
        for campaign in self.list():
            if campaign.campaign_id == campaign_id:
                return campaign
        raise KeyError(campaign_id)

    @_locked
    def save(self, campaign: GadgetMediaCampaign) -> GadgetMediaCampaign:
        campaign.validate()
        if not resolve_store_scope(self.channel_id).owns({"channel_id": campaign.channel_id}):
            raise ChannelError(404, "resource_not_found", "ไม่พบ campaign")
        campaigns = [GadgetMediaCampaign.from_dict(item) for item in self._load_raw()]
        replaced = False
        for index, existing in enumerate(campaigns):
            if existing.campaign_id == campaign.campaign_id:
                if existing.channel_id != campaign.channel_id:
                    raise ChannelError(422, "channel_id_immutable", "เปลี่ยนช่องเจ้าของ campaign ไม่ได้")
                campaigns[index] = campaign
                replaced = True
                break
        if not replaced:
            campaigns.append(campaign)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        temp_path.write_text(
            json.dumps([item.to_dict() for item in campaigns], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
        return campaign

    @_locked
    def create(self, campaign: GadgetMediaCampaign) -> GadgetMediaCampaign:
        campaign.channel_id = resolve_store_scope(self.channel_id).effective_owner
        if any(item.get("campaign_id") == campaign.campaign_id for item in self._load_raw()):
            raise CampaignValidationError(f"campaign_id already exists: {campaign.campaign_id}")
        return self.save(campaign)

    @_locked
    def update_slot(self, campaign_id: str, slot_id: str, changes: Dict[str, Any]) -> ContentSlot:
        campaign = self.get(campaign_id)
        slot = next((item for item in campaign.slots if item.slot_id == slot_id), None)
        if slot is None:
            raise KeyError(slot_id)
        allowed = {"series", "hook", "target_audience", "status", "script", "source_refs", "metrics", "product_project_id"}
        unknown = set(changes) - allowed
        if unknown:
            raise CampaignValidationError(f"unsupported slot fields: {', '.join(sorted(unknown))}")
        updated = slot.to_dict()
        updated.update(changes)
        updated["updated_at"] = _now()
        replacement = ContentSlot.from_dict(updated)
        if replacement.status == "published" and not replacement.ready_to_publish:
            raise CampaignValidationError(
                "slot cannot be published until readiness checks pass: "
                + "; ".join(replacement.publish_readiness_errors())
            )
        campaign.slots[campaign.slots.index(slot)] = replacement
        campaign.updated_at = _now()
        self.save(campaign)
        return replacement

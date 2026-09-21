"""Domain model for one-product/one-master Gadget Media projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import copy
import uuid


MODULE = "gadget_media"
STATUSES = (
    "brief",
    "sourcing",
    "source_ready",
    "research_ready",
    "script_ready",
    "in_production",
    "review_required",
    "ready_to_render",
    "rendered",
    "approved",
    "published",
)
PRESENTATION_MODES = ("creator_voice", "gemini_tts", "product_only")
FACT_TYPES = ("brand_claim", "verified_fact", "opinion", "caveat")
STORY_ROLES = ("hook", "product_reveal", "hero_benefit", "proof", "use_case", "caveat", "verdict", "cta")


class ProductVideoValidationError(ValueError):
    """Raised when persisted product-video data violates the domain contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _record(value: Any, field_name: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ProductVideoValidationError(f"{field_name} must be an object")
    return copy.deepcopy(value)


def _records(value: Any, field_name: str) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ProductVideoValidationError(f"{field_name} must be a list of objects")
    return copy.deepcopy(value)


def deep_merge(current: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(current)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


@dataclass
class ProductVideoProject:
    project_id: str
    product_identity: Dict[str, Any]
    audience: str = ""
    editorial_promise: str = ""
    status: str = "brief"
    source_assets: List[Dict[str, Any]] = field(default_factory=list)
    facts: List[Dict[str, Any]] = field(default_factory=list)
    story: Dict[str, Any] = field(default_factory=lambda: {"blocks": []})
    presentation: Dict[str, Any] = field(default_factory=lambda: {"mode": "gemini_tts", "voice": ""})
    edit: Dict[str, Any] = field(default_factory=lambda: {"edl": {"shots": []}, "timeline_path": "", "parity_verified": False})
    quality_report: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    approved_master_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    campaign_links: List[Dict[str, str]] = field(default_factory=list)
    module: str = MODULE
    schema_version: int = 1
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def validate(self) -> None:
        if self.module != MODULE:
            raise ProductVideoValidationError(f"module must be {MODULE}")
        if self.status not in STATUSES:
            raise ProductVideoValidationError(f"status must be one of {', '.join(STATUSES)}")
        brand = str(self.product_identity.get("brand") or "").strip()
        model = str(self.product_identity.get("model") or "").strip()
        if not brand or not model:
            raise ProductVideoValidationError("product_identity.brand and product_identity.model are required")
        mode = str(self.presentation.get("mode") or "gemini_tts")
        if mode not in PRESENTATION_MODES:
            raise ProductVideoValidationError(f"presentation.mode must be one of {', '.join(PRESENTATION_MODES)}")

        def unique(items: List[Dict[str, Any]], key: str, label: str) -> None:
            values = [str(item.get(key) or "") for item in items]
            if any(not value for value in values) or len(values) != len(set(values)):
                raise ProductVideoValidationError(f"{label} must have unique non-empty {key}")

        unique(self.source_assets, "source_id", "source_assets") if self.source_assets else None
        unique(self.facts, "fact_id", "facts") if self.facts else None
        blocks = _records(self.story.get("blocks"), "story.blocks")
        unique(blocks, "block_id", "story.blocks") if blocks else None
        unique(self.artifacts, "artifact_id", "artifacts") if self.artifacts else None

        if self.approved_master_id:
            approved = [a for a in self.artifacts if a.get("artifact_id") == self.approved_master_id and a.get("kind") == "render"]
            if len(approved) != 1:
                raise ProductVideoValidationError("approved_master_id must reference exactly one render artifact")
        if self.status in {"approved", "published"} and not self.approved_master_id:
            raise ProductVideoValidationError(f"{self.status} requires approved_master_id")
        if self.status == "published" and not self.metrics.get("published_at"):
            raise ProductVideoValidationError("published requires metrics.published_at")

    def transition_to(self, next_status: str) -> None:
        if next_status not in STATUSES:
            raise ProductVideoValidationError(f"unknown status: {next_status}")
        current_index = STATUSES.index(self.status)
        next_index = STATUSES.index(next_status)
        allowed_return = self.status in {"review_required", "ready_to_render", "rendered"} and next_status == "in_production"
        if next_status != self.status and next_index != current_index + 1 and not allowed_return:
            raise ProductVideoValidationError(f"invalid status transition: {self.status} -> {next_status}")
        self.status = next_status
        self.updated_at = utc_now()
        self.validate()

    def approve_render(self, artifact_id: str) -> None:
        render = next((item for item in self.artifacts if item.get("artifact_id") == artifact_id and item.get("kind") == "render"), None)
        if not render:
            raise ProductVideoValidationError("render artifact not found")
        for artifact in self.artifacts:
            if artifact.get("kind") == "render":
                artifact["approved"] = artifact.get("artifact_id") == artifact_id
        self.approved_master_id = artifact_id
        self.status = "approved"
        self.updated_at = utc_now()
        self.validate()

    def patched(self, changes: Dict[str, Any]) -> "ProductVideoProject":
        immutable = {"project_id", "module", "schema_version", "created_at", "approved_master_id", "artifacts"}
        blocked = immutable.intersection(changes)
        if blocked:
            raise ProductVideoValidationError(f"immutable fields cannot be patched: {', '.join(sorted(blocked))}")
        data = deep_merge(self.to_dict(), changes)
        requested_status = data.pop("status", self.status)
        data["status"] = self.status
        data["updated_at"] = utc_now()
        project = self.from_dict(data)
        if requested_status != self.status:
            project.transition_to(str(requested_status))
        return project

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "module": self.module,
            "product_identity": copy.deepcopy(self.product_identity),
            "audience": self.audience,
            "editorial_promise": self.editorial_promise,
            "status": self.status,
            "source_assets": copy.deepcopy(self.source_assets),
            "facts": copy.deepcopy(self.facts),
            "story": copy.deepcopy(self.story),
            "presentation": copy.deepcopy(self.presentation),
            "edit": copy.deepcopy(self.edit),
            "quality_report": copy.deepcopy(self.quality_report),
            "artifacts": copy.deepcopy(self.artifacts),
            "approved_master_id": self.approved_master_id,
            "metrics": copy.deepcopy(self.metrics),
            "campaign_links": copy.deepcopy(self.campaign_links),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductVideoProject":
        if not isinstance(data, dict):
            raise ProductVideoValidationError("project must be an object")
        project = cls(
            schema_version=int(data.get("schema_version", 1)),
            project_id=str(data.get("project_id") or ""),
            module=str(data.get("module") or MODULE),
            product_identity=_record(data.get("product_identity"), "product_identity"),
            audience=str(data.get("audience") or ""),
            editorial_promise=str(data.get("editorial_promise") or ""),
            status=str(data.get("status") or "brief"),
            source_assets=_records(data.get("source_assets"), "source_assets"),
            facts=_records(data.get("facts"), "facts"),
            story=_record(data.get("story") or {"blocks": []}, "story"),
            presentation=_record(data.get("presentation") or {"mode": "gemini_tts"}, "presentation"),
            edit=_record(data.get("edit") or {"edl": {"shots": []}}, "edit"),
            quality_report=_record(data.get("quality_report"), "quality_report"),
            artifacts=_records(data.get("artifacts"), "artifacts"),
            approved_master_id=data.get("approved_master_id") or None,
            metrics=_record(data.get("metrics"), "metrics"),
            campaign_links=_records(data.get("campaign_links"), "campaign_links"),
            created_at=str(data.get("created_at") or utc_now()),
            updated_at=str(data.get("updated_at") or utc_now()),
        )
        project.validate()
        return project


"""Atomic persistence for isolated Gadget Media product-video projects."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
from typing import Any, Dict, List, Optional
import uuid

from scripts.gadget_media_paths import GadgetMediaRoots, validate_project_id
from scripts.gadget_media_project import ProductVideoProject, ProductVideoValidationError, utc_now


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return value[:48] or "product"


class GadgetMediaRepository:
    """Owns project.json plus the materialized stage documents."""

    _lock = threading.RLock()

    def __init__(self, roots: Optional[GadgetMediaRoots] = None):
        self.roots = roots or GadgetMediaRoots.default()

    @property
    def index_path(self) -> Path:
        return self.roots.docs / "project_index.json"

    @staticmethod
    def _read_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _atomic_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

    def _manifest_path(self, project_id: str) -> Path:
        return self.roots.project_dir(project_id) / "project.json"

    def _ensure_layout(self, project_id: str) -> None:
        for path in self.roots.project_layout(project_id).values():
            path.mkdir(parents=True, exist_ok=True)
        self.roots.docs.mkdir(parents=True, exist_ok=True)

    def _materialize(self, project: ProductVideoProject) -> None:
        root = self.roots.project_dir(project.project_id)
        data = project.to_dict()
        self._atomic_json(root / "project.json", data)
        self._atomic_json(root / "product.json", {
            "project_id": project.project_id,
            "product_identity": data["product_identity"],
            "audience": data["audience"],
            "editorial_promise": data["editorial_promise"],
            "presentation": data["presentation"],
        })
        self._atomic_json(root / "sources.json", {"sources": data["source_assets"]})
        self._atomic_json(root / "evidence.json", {"facts": data["facts"]})
        self._atomic_json(root / "story.json", data["story"])
        self._atomic_json(root / "edl.json", data["edit"].get("edl") or {"shots": []})

    @staticmethod
    def _summary(project: ProductVideoProject) -> Dict[str, Any]:
        report = project.quality_report or {}
        master = next((item for item in project.artifacts if item.get("artifact_id") == project.approved_master_id), None)
        return {
            "project_id": project.project_id,
            "product_identity": project.product_identity,
            "status": project.status,
            "quality_passed": bool(report.get("passed")),
            "quality_score": int(report.get("editorial_score") or 0),
            "blocker_count": len(report.get("blockers") or []),
            "duration": float((project.edit or {}).get("duration") or (master or {}).get("duration") or 0),
            "approved_master_id": project.approved_master_id,
            "updated_at": project.updated_at,
        }

    def _write_index(self, projects: List[ProductVideoProject]) -> None:
        self._atomic_json(self.index_path, {
            "schema_version": 1,
            "updated_at": utc_now(),
            "projects": [self._summary(item) for item in sorted(projects, key=lambda p: p.updated_at, reverse=True)],
        })

    def list(self) -> List[ProductVideoProject]:
        if not self.roots.projects.exists():
            return []
        projects: List[ProductVideoProject] = []
        for path in self.roots.projects.iterdir():
            if not path.is_dir() or not (path / "project.json").is_file():
                continue
            try:
                projects.append(ProductVideoProject.from_dict(self._read_json(path / "project.json")))
            except (OSError, json.JSONDecodeError, ProductVideoValidationError):
                continue
        return sorted(projects, key=lambda project: project.updated_at, reverse=True)

    def create(
        self,
        product_identity: Dict[str, Any],
        *,
        audience: str = "",
        editorial_promise: str = "",
        presentation: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> ProductVideoProject:
        brand = str((product_identity or {}).get("brand") or "")
        model = str((product_identity or {}).get("model") or "")
        candidate = project_id or f"{datetime.now(timezone.utc):%Y%m%d}-{_slug(brand)}-{_slug(model)}-{uuid.uuid4().hex[:6]}"
        project_id = validate_project_id(candidate)
        with self._lock:
            if self._manifest_path(project_id).exists():
                raise ProductVideoValidationError(f"project already exists: {project_id}")
            project = ProductVideoProject(
                project_id=project_id,
                product_identity=dict(product_identity or {}),
                audience=audience,
                editorial_promise=editorial_promise,
                presentation=dict(presentation or {"mode": "gemini_tts", "voice": ""}),
            )
            project.validate()
            self._ensure_layout(project_id)
            self._materialize(project)
            self._write_index(self.list())
            return project

    def get(self, project_id: str) -> ProductVideoProject:
        path = self._manifest_path(project_id)
        if not path.is_file():
            raise KeyError(project_id)
        return ProductVideoProject.from_dict(self._read_json(path))

    def save(self, project: ProductVideoProject) -> ProductVideoProject:
        project.updated_at = utc_now()
        project.validate()
        with self._lock:
            self._ensure_layout(project.project_id)
            self._materialize(project)
            all_projects = [item for item in self.list() if item.project_id != project.project_id]
            self._write_index([project, *all_projects])
        return project

    def patch(self, project_id: str, changes: Dict[str, Any]) -> ProductVideoProject:
        with self._lock:
            return self.save(self.get(project_id).patched(changes))

    def save_timeline(self, project_id: str, timeline: Dict[str, Any]) -> ProductVideoProject:
        if timeline.get("workspace_scope") != "gadget_media" or timeline.get("project_id") != project_id:
            raise ProductVideoValidationError("timeline scope or project_id does not match")
        project = self.get(project_id)
        path = self.roots.project_dir(project_id) / "timeline.json"
        self._atomic_json(path, timeline)
        project.edit["timeline_path"] = str(path)
        project.edit["duration"] = float(timeline.get("duration") or 0)
        if project.status == "script_ready":
            project.transition_to("in_production")
        return self.save(project)

    def load_timeline(self, project_id: str) -> Dict[str, Any]:
        path = self.roots.project_dir(project_id) / "timeline.json"
        if not path.is_file():
            raise KeyError(f"timeline:{project_id}")
        return self._read_json(path)

    def save_quality_report(self, project_id: str, report: Dict[str, Any]) -> ProductVideoProject:
        project = self.get(project_id)
        project.quality_report = dict(report)
        if report.get("passed") and project.status == "review_required":
            project.transition_to("ready_to_render")
        return self.save(project)

    def add_render_artifact(self, project_id: str, artifact: Dict[str, Any]) -> ProductVideoProject:
        project = self.get(project_id)
        artifact_id = str(artifact.get("artifact_id") or "")
        if not artifact_id or any(item.get("artifact_id") == artifact_id for item in project.artifacts):
            raise ProductVideoValidationError("render artifact_id must be unique and non-empty")
        project.artifacts.append(dict(artifact))
        if project.status == "ready_to_render":
            project.transition_to("rendered")
        return self.save(project)

    def approve_render(self, project_id: str, artifact_id: str) -> ProductVideoProject:
        project = self.get(project_id)
        if project.status not in {"rendered", "approved"}:
            raise ProductVideoValidationError("project must be rendered before approval")
        project.approve_render(artifact_id)
        return self.save(project)

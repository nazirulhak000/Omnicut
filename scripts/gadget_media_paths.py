"""Owned filesystem namespace for Gadget Media product-video projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict

from scripts.config import (
    ARCHIVE_DIR,
    ASSETS_DIR,
    BASE_DIR,
    COVERS_DIR,
    EXPORTS_DIR,
    PROJECTS_DIR,
    RAW_DIR,
)


PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,79}$")


class GadgetMediaPathError(ValueError):
    """Raised when a client-controlled identifier could escape the namespace."""


def validate_project_id(project_id: str) -> str:
    value = str(project_id or "").strip().lower()
    if not PROJECT_ID_PATTERN.fullmatch(value):
        raise GadgetMediaPathError(
            "project_id must be 3-80 lowercase letters, numbers, hyphens, or underscores"
        )
    return value


def contained_path(root: Path, *parts: str) -> Path:
    """Resolve a descendant and fail closed on absolute/traversal input."""
    root = Path(root).resolve(strict=False)
    for part in parts:
        candidate = Path(str(part))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise GadgetMediaPathError("absolute paths and traversal are not allowed")
    target = root.joinpath(*parts).resolve(strict=False)
    if target != root and root not in target.parents:
        raise GadgetMediaPathError("path is outside the Gadget Media namespace")
    return target


@dataclass(frozen=True)
class GadgetMediaRoots:
    raw: Path
    assets: Path
    projects: Path
    exports: Path
    covers: Path
    archive: Path
    docs: Path

    @classmethod
    def default(cls) -> "GadgetMediaRoots":
        return cls(
            raw=RAW_DIR / "GadgetMedia",
            assets=ASSETS_DIR / "GadgetMedia",
            projects=PROJECTS_DIR / "GadgetMedia",
            exports=EXPORTS_DIR / "GadgetMedia",
            covers=COVERS_DIR / "GadgetMedia",
            archive=ARCHIVE_DIR / "GadgetMedia",
            docs=BASE_DIR / "_Docs" / "gadget_media",
        )

    @classmethod
    def under(cls, root: Path) -> "GadgetMediaRoots":
        """Test/helper layout that never touches the real project folders."""
        root = Path(root)
        return cls(
            raw=root / "01_Raw" / "GadgetMedia",
            assets=root / "02_Assets" / "GadgetMedia",
            projects=root / "03_Projects" / "GadgetMedia",
            exports=root / "04_Exports" / "Ready_to_post" / "GadgetMedia",
            covers=root / "05_Covers_Thumbnails" / "GadgetMedia",
            archive=root / "06_Archive" / "GadgetMedia",
            docs=root / "_Docs" / "gadget_media",
        )

    def project_dir(self, project_id: str) -> Path:
        return contained_path(self.projects, validate_project_id(project_id))

    def export_dir(self, project_id: str) -> Path:
        return contained_path(self.exports, validate_project_id(project_id))

    def cover_dir(self, project_id: str) -> Path:
        return contained_path(self.covers, validate_project_id(project_id))

    def raw_dir(self, project_id: str) -> Path:
        return contained_path(self.raw, validate_project_id(project_id))

    def project_layout(self, project_id: str) -> Dict[str, Path]:
        project = self.project_dir(project_id)
        return {
            "project": project,
            "media": project / "media",
            "proxy": project / "media" / "proxy",
            "selects": project / "media" / "selects",
            "generated": project / "media" / "generated",
            "audio": project / "audio",
            "voice": project / "audio" / "voice",
            "source_audio": project / "audio" / "source",
            "mix": project / "audio" / "mix",
            "review": project / "review",
            "raw_original": self.raw_dir(project_id) / "original",
            "exports": self.export_dir(project_id),
            "covers": self.cover_dir(project_id),
        }


"""Viral Lint API (roadmap M4): ``POST /api/viral-lint``.

Body: ``{"project_name": str?, "manifest": dict?}``

- ``project_name`` only: lint the stored manifest (channel-scoped load).
- ``project_name`` + ``manifest``: the editor's unsaved state (its save
  payload) is laid over the stored manifest, so the lint sees the current
  timeline while style_preset / script_data / target_duration still come
  from the project.
- ``manifest`` only: lint the body as given (pure computation, no data read).

Returns ``{"issues": [...], "summary": {"block", "warn", "info"}, "score"}``
-- see ``scripts/viral_lint.py`` for rules, thresholds and the score formula.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.channel_scope import ChannelScope
from scripts.channel_workflows import get_workflow_scope, require_project_owner
from scripts.viral_lint import lint_report

router = APIRouter(prefix="/api", tags=["viral-lint"])


class ViralLintRequest(BaseModel):
    project_name: Optional[str] = None
    manifest: Optional[Dict[str, Any]] = None


@router.post("/viral-lint")
def viral_lint(req: ViralLintRequest, channel_scope: ChannelScope = Depends(get_workflow_scope)):
    project_name = (req.project_name or "").strip()
    if not project_name and req.manifest is None:
        raise HTTPException(status_code=422, detail="ส่ง project_name หรือ manifest อย่างน้อยหนึ่งอย่าง")
    manifest: Dict[str, Any] = {}
    if project_name:
        manifest = dict(require_project_owner(channel_scope, project_name))
    if req.manifest:
        manifest.update(req.manifest)
    return lint_report(manifest)

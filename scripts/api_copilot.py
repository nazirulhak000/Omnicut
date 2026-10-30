"""
scripts/api_copilot.py — FastAPI Router for AI Production Co-Pilot & HyperFrames Pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from scripts.channel_scope import (
    ChannelScope,
    get_channel_scope,
    require_active_for_new_work,
    require_writable,
)
from scripts.copilot_engine import COPILOT_RENDER_UNSUPPORTED_MSG, CopilotEngine

logger = logging.getLogger("omnicut.api_copilot")

router = APIRouter(prefix="/api/copilot", tags=["AI Production Co-Pilot"])


def _guard_writable(scope: ChannelScope) -> None:
    if not scope.is_implicit_default:
        require_writable(scope)


def _guard_new_work(scope: ChannelScope) -> None:
    if not scope.is_implicit_default:
        require_active_for_new_work(scope)


class CreateSessionPayload(BaseModel):
    product_id: str = Field(..., description="Target Product ID in ProductStore")
    initial_prompt: Optional[str] = Field(None, description="Optional starting brief or user message")


class ChatPayload(BaseModel):
    message: str = Field(..., description="User message to the Co-Pilot")


class ScriptPayload(BaseModel):
    angle_title: Optional[str] = Field(None, description="Title of the angle to script")
    style: str = Field("couple_paper_chat", description="Visual style (default: couple_paper_chat)")


class BuildDraftPayload(BaseModel):
    clip_slug: Optional[str] = Field(None, description="Custom unique clip slug (optional)")
    dry_run_audio: bool = Field(False, description="Whether to stub audio without hitting remote TTS API")


@router.post("/sessions")
def create_session(
    payload: CreateSessionPayload,
    scope: ChannelScope = Depends(get_channel_scope)
) -> Dict[str, Any]:
    """Create a new conversational Co-Pilot session from an existing product."""
    _guard_new_work(scope)
    try:
        session = CopilotEngine.create_session(
            product_id=payload.product_id,
            channel_id=scope.channel_id,
            initial_prompt=payload.initial_prompt
        )
        return {"success": True, "session": session}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Failed to create Co-Pilot session: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการสร้าง session: {exc}")


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    scope: ChannelScope = Depends(get_channel_scope)
) -> Dict[str, Any]:
    """Retrieve session state, chat history, and created draft info."""
    session = CopilotEngine.get_session(session_id, channel_id=scope.channel_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"ไม่พบ session '{session_id}' ในช่องนี้")
    return {"success": True, "session": session}


@router.post("/sessions/{session_id}/chat")
def chat_with_copilot(
    session_id: str,
    payload: ChatPayload,
    scope: ChannelScope = Depends(get_channel_scope)
) -> Dict[str, Any]:
    """Send a message to the Co-Pilot; updates creative direction and angle proposals."""
    _guard_writable(scope)
    try:
        updated = CopilotEngine.chat(
            session_id=session_id,
            user_message=payload.message,
            channel_id=scope.channel_id
        )
        return {"success": True, "session": updated}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Chat error in session {session_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการสนทนากับ Co-Pilot: {exc}")


@router.post("/sessions/{session_id}/generate-script")
def generate_script(
    session_id: str,
    payload: ScriptPayload,
    scope: ChannelScope = Depends(get_channel_scope)
) -> Dict[str, Any]:
    """Generate structured turn-based script for the selected angle."""
    _guard_writable(scope)
    try:
        updated = CopilotEngine.generate_script(
            session_id=session_id,
            angle_title=payload.angle_title,
            style=payload.style,
            channel_id=scope.channel_id
        )
        return {"success": True, "session": updated}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Script generation error in session {session_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการสร้างสคริปต์: {exc}")


@router.post("/sessions/{session_id}/build-draft")
def build_hyperframes_draft(
    session_id: str,
    payload: BuildDraftPayload,
    scope: ChannelScope = Depends(get_channel_scope)
) -> Dict[str, Any]:
    """Scaffold HyperFrames composition (HTML + assets) and register to ContentTracker as draft_ready."""
    _guard_writable(scope)
    try:
        updated = CopilotEngine.build_hyperframes_draft(
            session_id=session_id,
            clip_slug=payload.clip_slug,
            channel_id=scope.channel_id,
            dry_run_audio=payload.dry_run_audio
        )
        return {"success": True, "session": updated}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Build draft error in session {session_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการสร้าง HyperFrames ดราฟต์: {exc}")


@router.post("/sessions/{session_id}/render")
async def render_session_draft(
    session_id: str,
    scope: ChannelScope = Depends(get_channel_scope)
) -> Dict[str, Any]:
    """Refuse to render a Co-Pilot draft to MP4.

    Co-Pilot drafts carry a placeholder tone track, not real TTS. Rendering one
    used to drop an unusable clip into 04_Exports/Ready_to_post and mark it
    "Rendered" -- violating rule 11 (no junk in exports) and rule 8 (status
    must reflect reality). Until the Co-Pilot is wired to the real voice line,
    this always answers 409 and writes nothing.
    """
    _guard_writable(scope)
    session = CopilotEngine.get_session(session_id, channel_id=scope.channel_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"ไม่พบ session '{session_id}' ในช่องนี้")
    raise HTTPException(status_code=409, detail=COPILOT_RENDER_UNSUPPORTED_MSG)

"""OmniCut Pro Studio - FastAPI Router for In-App Antigravity AI Agent (/api/agent/*)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from scripts.agent.agy_bridge import (
    CURRENT_CONVERSATION_ID,
    get_bridge_status,
    parse_action_proposals,
    stream_agent_response,
)
from scripts.agent.omnicut_agent_tools import (
    apply_action,
    get_timeline_summary,
)

logger = logging.getLogger("omnicut.api_agent")

router = APIRouter(prefix="/api/agent", tags=["Antigravity In-App AI Agent"])


class AgentChatRequest(BaseModel):
    message: str
    project_name: Optional[str] = None
    conversation_id: Optional[str] = CURRENT_CONVERSATION_ID


class ActionApplyRequest(BaseModel):
    action: Dict[str, Any]


@router.get("/status")
def api_agent_status() -> Dict[str, Any]:
    """Returns the live status of the Antigravity engine and local agent bridge."""
    return get_bridge_status()


@router.get("/timeline/{project_name}")
def api_agent_timeline(project_name: str) -> Dict[str, Any]:
    """Returns timeline inspection data for the agent and frontend."""
    try:
        return get_timeline_summary(project_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching timeline summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def api_agent_stream(payload: AgentChatRequest):
    """Server-Sent Events (SSE) streaming endpoint for agent thoughts, tokens, and action proposals."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    conv_id = payload.conversation_id or CURRENT_CONVERSATION_ID

    return StreamingResponse(
        stream_agent_response(
            prompt=payload.message,
            project_name=payload.project_name,
            conversation_id=conv_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/actions/apply")
def api_agent_apply_action(payload: ActionApplyRequest) -> Dict[str, Any]:
    """Applies an approved action proposal directly to the timeline."""
    try:
        result = apply_action(payload.action)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

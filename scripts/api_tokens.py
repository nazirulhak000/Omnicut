"""
Token Analytics Router
Provides API endpoints for token monitoring, cost savings, and historical audit logs.
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from scripts.token_tracker import TokenTracker

router = APIRouter(prefix="/api/tokens", tags=["Token Analytics"])


@router.get("/summary")
def get_token_summary():
    """Returns aggregated token metrics, model breakdown, and daily stats."""
    try:
        return TokenTracker.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch token summary: {e}")


@router.get("/history")
def get_token_history(limit: int = Query(50, ge=1, le=500)):
    """Returns recent token usage events."""
    try:
        return {"events": TokenTracker.get_history(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch token history: {e}")


@router.post("/reset")
def reset_token_analytics():
    """Resets all token analytics history."""
    try:
        TokenTracker.reset()
        return {"message": "รีเซ็ตสถิติโทเคนเรียบร้อยแล้ว", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset token analytics: {e}")

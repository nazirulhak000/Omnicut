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
def get_token_history(
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = Query(None, max_length=200),
    task: Optional[str] = Query(None, max_length=80),
    q: Optional[str] = Query(None, max_length=120),
):
    """Returns a cursor-paginated token history page."""
    try:
        return TokenTracker.get_history_page(limit=limit, before=before, task=task, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch token history: {e}")


@router.get("/alerts")
def get_token_alerts(limit: int = Query(20, ge=1, le=100)):
    """Returns recent AI quota / rate-limit alerts."""
    try:
        return {"alerts": TokenTracker.get_alerts(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {e}")


@router.post("/alerts/clear")
def clear_token_alerts():
    """Clears all token/quota alerts."""
    try:
        TokenTracker.clear_alerts()
        return {"message": "ล้างประวัติแจ้งเตือนเรียบร้อยแล้ว", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear alerts: {e}")


@router.post("/reset")
def reset_token_analytics():
    """Resets all token analytics history."""
    try:
        TokenTracker.reset()
        return {"message": "รีเซ็ตสถิติโทเคนเรียบร้อยแล้ว", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset token analytics: {e}")

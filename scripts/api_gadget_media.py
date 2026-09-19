"""API for the non-commerce Gadget Media campaign."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from scripts.gadget_media_campaign import (
    CAMPAIGNS_FILE,
    CampaignStore,
    CampaignValidationError,
    create_starter_campaign,
)


router = APIRouter(prefix="/api/gadget-media", tags=["Gadget Media"])


class CreateCampaignRequest(BaseModel):
    name: str = "Gadget Media — 30 วัน 21 คลิป"
    campaign_id: Optional[str] = None
    target_audience: str = "คนใช้มือถือทั่วไปที่อยากซื้อ Gadget คุ้มและเข้าใจง่าย"


class SlotPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series: Optional[str] = None
    hook: Optional[str] = None
    target_audience: Optional[str] = None
    status: Optional[str] = None
    script: Optional[str] = None
    source_refs: Optional[List[Dict[str, Any]]] = None
    metrics: Optional[Dict[str, Any]] = None


def _store() -> CampaignStore:
    return CampaignStore(CAMPAIGNS_FILE)


def _campaign_or_404(campaign_id: str):
    try:
        return _store().get(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ไม่พบ Gadget Media campaign") from exc
    except CampaignValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/campaigns")
def list_campaigns():
    try:
        campaigns = _store().list()
    except CampaignValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"campaigns": [campaign.to_dict() for campaign in campaigns]}


@router.post("/campaigns", status_code=201)
def create_campaign(payload: CreateCampaignRequest):
    campaign = create_starter_campaign(
        payload.name,
        campaign_id=payload.campaign_id,
        target_audience=payload.target_audience,
    )
    try:
        saved = _store().create(campaign)
    except CampaignValidationError as exc:
        raise HTTPException(status_code=409 if "already exists" in str(exc) else 400, detail=str(exc)) from exc
    return saved.to_dict()


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str):
    return _campaign_or_404(campaign_id).to_dict()


@router.get("/campaigns/{campaign_id}/readiness")
def get_campaign_readiness(campaign_id: str):
    campaign = _campaign_or_404(campaign_id)
    return campaign.readiness_summary()


@router.patch("/campaigns/{campaign_id}/slots/{slot_id}")
def update_slot(campaign_id: str, slot_id: str, payload: SlotPatch):
    _campaign_or_404(campaign_id)
    try:
        slot = _store().update_slot(campaign_id, slot_id, payload.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ไม่พบ content slot") from exc
    except CampaignValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return slot.to_dict()

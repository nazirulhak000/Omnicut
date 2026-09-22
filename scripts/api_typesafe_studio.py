"""
TypeSafe Studio API Router for OmniCut Pro Studio.
Exposes TypeSafe AI System One decision primitives to the frontend editor:
- B-roll / Script Matching (Strict Topic Hold Guard)
- Hook Variant Generation & 3-Second Retention Scoring
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scripts.typesafe_bridge import (
    evaluate_hook_retention,
    generate_and_rank_hook_variants,
    is_typesafe_available,
    match_broll_for_sentence,
)

logger = logging.getLogger("api_typesafe_studio")

router = APIRouter(prefix="/api/typesafe-studio", tags=["typesafe-studio"])


class MatchBrollRequest(BaseModel):
    sentence: str = Field(..., description="Voiceover sentence or script text")
    candidate_clips: List[Dict[str, Any]] = Field(
        ..., description="List of B-roll candidate clips with id, name, and description"
    )


class GenerateHooksRequest(BaseModel):
    product_name: str = Field(..., description="Product name")
    key_features: Optional[List[str]] = Field(
        default=None, description="Key features or selling points"
    )


class EvaluateHookRequest(BaseModel):
    hook_text: str = Field(..., description="Hook sentence to evaluate")


@router.get("/status")
def get_typesafe_status() -> Dict[str, Any]:
    """Check availability of TypeSafe AI integration."""
    return {
        "available": is_typesafe_available(),
        "provider": "TypeSafe System One (Jev)",
        "features": ["strict_topic_hold", "hook_retention_scoring", "broll_matching"],
    }


@router.post("/match-broll")
def api_match_broll(req: MatchBrollRequest) -> Dict[str, Any]:
    """Match candidate B-roll clips against a voiceover sentence adhering to Strict Topic Hold."""
    if not req.sentence.strip():
        raise HTTPException(status_code=400, detail="Voiceover sentence cannot be empty")
    if not req.candidate_clips:
        raise HTTPException(status_code=400, detail="Candidate clips list cannot be empty")

    result = match_broll_for_sentence(req.sentence, req.candidate_clips)
    return result


@router.post("/generate-hooks")
def api_generate_hooks(req: GenerateHooksRequest) -> Dict[str, Any]:
    """Generate 3 diverse hook variants and rank them by TypeSafe retention scores."""
    if not req.product_name.strip():
        raise HTTPException(status_code=400, detail="Product name cannot be empty")

    variants = generate_and_rank_hook_variants(req.product_name, req.key_features)
    return {
        "product_name": req.product_name,
        "variants": variants,
    }


@router.post("/evaluate-hook")
def api_evaluate_hook(req: EvaluateHookRequest) -> Dict[str, Any]:
    """Evaluate a single hook for TikTok retention and psychological trigger tone."""
    if not req.hook_text.strip():
        raise HTTPException(status_code=400, detail="Hook text cannot be empty")

    result = evaluate_hook_retention(req.hook_text)
    return result

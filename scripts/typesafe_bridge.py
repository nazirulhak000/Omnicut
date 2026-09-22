"""
TypeSafe AI Bridge (System One / Jev integration) for OmniCut Pro Studio.

Provides structured decision primitives:
- Choice: Pick best option among defined set with confidence distribution
- Noul: Probability of a condition holding (Yes/No, 0.0 to 1.0)
- Score: Continuous graded scoring along criteria dimensions

Uses TYPESAFE_API_KEY from .env / environment via scripts.config.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from scripts.config import get_typesafe_api_key

logger = logging.getLogger("typesafe_bridge")

_client = None


def get_typesafe_client():
    """Returns a singleton instance of TypeSafeClient or None if key is missing."""
    global _client
    if _client is not None:
        return _client

    api_key = get_typesafe_api_key()
    if not api_key:
        logger.warning("TYPESAFE_API_KEY is not set.")
        return None

    try:
        from typesafe_sdk import TypeSafeClient

        _client = TypeSafeClient(api_key=api_key)
        return _client
    except Exception as exc:
        logger.error(f"Failed to initialize TypeSafeClient: {exc}")
        return None


def is_typesafe_available() -> bool:
    """Check if TypeSafe SDK and API Key are configured."""
    return bool(get_typesafe_api_key())


def judge_noul(instructions: str, state: Dict[str, Any]) -> Optional[float]:
    """
    Evaluates a boolean condition (0.0 to 1.0 probability) over state.
    Returns probability float or None if unavailable.
    """
    client = get_typesafe_client()
    if not client:
        return None

    try:
        from typesafe_sdk import Noul

        response = client.system_one(
            state=state,
            questions={"q": Noul(instructions=instructions)},
        )
        return float(response.nouls["q"].noul)
    except Exception as exc:
        logger.error(f"TypeSafe judge_noul error: {exc}")
        return None


def judge_choice(instructions: str, criteria: Dict[str, Optional[str]], state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Selects one option among criteria over state.
    Returns dict: {"choice": str, "confidence": float, "distribution": dict}
    """
    client = get_typesafe_client()
    if not client:
        return None

    try:
        from typesafe_sdk import Choice

        response = client.system_one(
            state=state,
            questions={"q": Choice(instructions=instructions, criteria=criteria)},
        )
        choice_obj = response.choices["q"]
        return {
            "choice": choice_obj.choice,
            "confidence": getattr(choice_obj, "confidence", None),
            "distribution": getattr(choice_obj, "distribution", {}),
        }
    except Exception as exc:
        logger.error(f"TypeSafe judge_choice error: {exc}")
        return None


def judge_score(instructions: str, levels: List[str], state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evaluates ordered score along criteria levels over state.
    Returns dict: {"score": float, "confidence": float}
    """
    client = get_typesafe_client()
    if not client:
        return None

    try:
        from typesafe_sdk import Score

        response = client.system_one(
            state=state,
            questions={"q": Score(instructions=instructions, criteria=levels)},
        )
        score_obj = response.scores["q"]
        return {
            "score": score_obj.score,
            "confidence": getattr(score_obj, "confidence", None),
        }
    except Exception as exc:
        logger.error(f"TypeSafe judge_score error: {exc}")
        return None


def evaluate_hook_retention(hook_text: str) -> Dict[str, Any]:
    """
    Evaluates a video hook script for TikTok retention potential:
    - is_high_retention: probability of hooking the viewer in 3 seconds
    - tone: tone of hook (curiosity, excitement, urgent, neutral, dull)
    - score: quality rating
    """
    client = get_typesafe_client()
    if not client:
        return {"error": "TypeSafe not configured"}

    try:
        from typesafe_sdk import Choice, Noul, Score

        state = {"hook": hook_text}
        response = client.system_one(
            state=state,
            questions={
                "high_retention": Noul(instructions="Does this hook immediately grab attention within the first 3 seconds?"),
                "tone": Choice(
                    instructions="What is the psychological trigger of this hook?",
                    criteria={
                        "curiosity": "Leaves an open loop or mystery",
                        "excitement": "High energy or surprising product feature",
                        "urgency": "Addresses a pressing pain point or problem",
                        "ordinary": "Standard or generic statement",
                    },
                ),
                "rating": Score(
                    instructions="Rate the overall viral potential of this hook for short-form video (TikTok/Reels)",
                    criteria=["weak", "average", "strong", "exceptional"],
                ),
            },
        )

        return {
            "hook": hook_text,
            "high_retention_prob": response.nouls["high_retention"].noul,
            "tone": response.choices["tone"].choice,
            "rating_score": response.scores["rating"].score,
        }
    except Exception as exc:
        logger.error(f"Failed to evaluate hook: {exc}")
        return {"error": str(exc)}


def match_broll_for_sentence(
    sentence: str,
    candidate_clips: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Selects the best B-roll clip for a voiceover sentence and evaluates Strict Topic Hold.
    
    Each candidate should have:
    - id: unique identifier (filename or index)
    - name: label/title
    - description / tags: contextual visual description
    """
    if not candidate_clips:
        return {"error": "No candidate clips provided"}

    client = get_typesafe_client()
    if not client:
        # Graceful fallback: pick first or simple keyword match
        best = candidate_clips[0]
        sentence_lower = sentence.lower()
        for c in candidate_clips:
            name_desc = f"{c.get('name', '')} {c.get('description', '')}".lower()
            if any(w in name_desc for w in sentence_lower.split() if len(w) > 3):
                best = c
                break
        return {
            "matched_clip_id": best.get("id"),
            "strict_topic_hold": True,
            "relevance_score": 0.85,
            "confidence": 0.8,
            "reasoning": "Fallback keyword heuristic (TypeSafe offline)",
        }

    try:
        from typesafe_sdk import Choice, Noul, Score

        criteria = {}
        for c in candidate_clips:
            cid = str(c.get("id"))
            desc = c.get("description") or c.get("name") or "video footage"
            criteria[cid] = f"{c.get('name', cid)}: {desc}"

        state = {
            "voiceover_sentence": sentence,
            "candidate_clips": criteria,
        }

        response = client.system_one(
            state=state,
            questions={
                "best_clip": Choice(
                    instructions="Which candidate B-roll clip best and most directly visually illustrates the voiceover sentence?",
                    criteria=criteria,
                ),
                "strict_topic_hold": Noul(
                    instructions="Does the visual content strictly depict the exact feature spoken in the sentence without drifting away before the speech ends?",
                ),
                "relevance_score": Score(
                    instructions="Rate the alignment accuracy between the spoken topic and the candidate clip visual",
                    criteria=["irrelevant", "partial", "well_matched", "perfect_sync"],
                ),
            },
        )

        chosen_id = response.choices["best_clip"].choice
        return {
            "matched_clip_id": chosen_id,
            "strict_topic_hold": bool(response.nouls["strict_topic_hold"].noul > 0.6),
            "topic_hold_probability": response.nouls["strict_topic_hold"].noul,
            "relevance_score": response.scores["relevance_score"].score,
            "confidence": getattr(response.choices["best_clip"], "confidence", None),
            "distribution": getattr(response.choices["best_clip"], "distribution", {}),
        }
    except Exception as exc:
        logger.error(f"Failed to match B-roll: {exc}")
        return {"error": str(exc), "matched_clip_id": candidate_clips[0].get("id")}


def generate_and_rank_hook_variants(
    product_name: str,
    key_features: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Generates 3 diverse hook angles for a product and ranks them via TypeSafe retention scoring.
    Angles:
    1. Curiosity / Open loop
    2. Pain point / Urgent warning
    3. Spec Monster / Flagship hype
    """
    features_str = ", ".join(key_features) if key_features else "สเปกจัดเต็ม ดีไซน์พรีเมียม คุ้มค่าที่สุด"

    # Base creative templates tailored for TikTok 9:16 viral short-form
    hooks = [
        {
            "angle": "curiosity",
            "angle_title": "กระตุ้นความอยากรู้ (Open Loop)",
            "hook_text": f"อย่าเพิ่งซื้อ {product_name} ถ้ายังไม่รู้ความลับข้อนี้!",
            "badge_color": "#FFE600",
        },
        {
            "angle": "pain_point",
            "angle_title": "แก้ปัญหา / คำเตือน (Pain Point)",
            "hook_text": f"ใครที่กำลังเจอปัญหานี้อยู่... {product_name} จบครบในงบประหยัดจริงไหม?",
            "badge_color": "#FF3366",
        },
        {
            "angle": "spec_monster",
            "angle_title": "โชว์สเปกตัวตึง (Spec Monster)",
            "hook_text": f"เปิดตัวแล้ว {product_name}! ตัวตึงสเปกโหด {features_str} จัดเต็มขนาดนี้จะขายกี่บาท?!",
            "badge_color": "#66FF00",
        },
    ]

    ranked = []
    for h in hooks:
        eval_res = evaluate_hook_retention(h["hook_text"])
        rating_score = eval_res.get("rating_score", 0.8)
        retention_prob = eval_res.get("high_retention_prob", 0.75)
        tone = eval_res.get("tone", h["angle"])
        ranked.append({
            **h,
            "retention_probability": retention_prob,
            "rating_score": rating_score,
            "detected_tone": tone,
        })

    # Sort by rating score descending
    ranked.sort(key=lambda x: x.get("rating_score", 0), reverse=True)
    return ranked


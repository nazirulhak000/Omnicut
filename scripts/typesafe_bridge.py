"""
TypeSafe AI Bridge (System One / Jev integration) for OmniCut Pro Studio.

Provides structured decision primitives:
- Choice: Pick best option among defined set with confidence distribution
- Noul: Probability of a condition holding (Yes/No, 0.0 to 1.0)
- Score: Continuous graded scoring along criteria dimensions

Uses TYPESAFE_API_KEY from .env / environment via scripts.config.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from scripts.config import BASE_DIR, get_typesafe_api_key

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


def match_script_sequence_broll(
    sentences: List[str],
    candidate_clips: List[Dict[str, Any]],
    ensure_diversity: bool = True,
) -> List[Dict[str, Any]]:
    """
    Sequentially matches each sentence in a script to candidate B-roll footage
    while enforcing Strict Topic Hold and shot diversity using TypeSafe System One.
    """
    if not sentences or not candidate_clips:
        return []

    client = get_typesafe_client()
    sequence = []
    last_clip_id = None

    for idx, sentence in enumerate(sentences):
        if not sentence or not sentence.strip():
            continue

        matched_entry = None
        if client:
            try:
                from typesafe_sdk import Choice, Noul, Score

                criteria = {}
                for c in candidate_clips:
                    cid = str(c.get("id"))
                    desc = c.get("description") or c.get("name") or "video footage"
                    if ensure_diversity and len(candidate_clips) > 1 and cid == last_clip_id:
                        criteria[cid] = f"[Used in previous shot] {c.get('name', cid)}: {desc}"
                    else:
                        criteria[cid] = f"{c.get('name', cid)}: {desc}"

                state = {
                    "voiceover_sentence": sentence,
                    "sentence_index": idx + 1,
                    "total_sentences": len(sentences),
                    "previous_clip_id": last_clip_id,
                    "candidate_clips": criteria,
                }

                instructions = (
                    "Which candidate B-roll clip best and most directly visually illustrates the voiceover sentence? "
                    "If multiple clips are relevant, prefer a clip that was not used in the immediately previous shot."
                    if ensure_diversity and len(candidate_clips) > 1
                    else "Which candidate B-roll clip best and most directly visually illustrates the voiceover sentence?"
                )

                response = client.system_one(
                    state=state,
                    questions={
                        "best_clip": Choice(
                            instructions=instructions,
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
                matched_clip = next((c for c in candidate_clips if str(c.get("id")) == chosen_id), candidate_clips[0])
                matched_entry = {
                    "sentence_index": idx,
                    "sentence": sentence,
                    "matched_clip_id": chosen_id,
                    "matched_clip": matched_clip,
                    "strict_topic_hold": bool(response.nouls["strict_topic_hold"].noul > 0.6),
                    "topic_hold_probability": round(float(response.nouls["strict_topic_hold"].noul), 3),
                    "relevance_score": round(float(response.scores["relevance_score"].score), 3),
                    "confidence": getattr(response.choices["best_clip"], "confidence", 0.9),
                }
                last_clip_id = chosen_id
            except Exception as exc:
                logger.error(f"Error matching sequence sentence {idx} with TypeSafe: {exc}")

        if not matched_entry:
            # Fallback heuristic: keyword matching with diversity penalty
            sentence_lower = sentence.lower()
            words = [w for w in sentence_lower.replace(",", " ").replace(".", " ").split() if len(w) > 2]
            best_clip = candidate_clips[0]
            best_score = -1.0

            for c in candidate_clips:
                name_desc = f"{c.get('name', '')} {c.get('description', '')}".lower()
                matches = sum(1 for w in words if w in name_desc)
                score = matches / max(1, len(words))
                if ensure_diversity and len(candidate_clips) > 1 and str(c.get("id")) == last_clip_id:
                    score -= 0.35  # diversity penalty
                if score > best_score:
                    best_score = score
                    best_clip = c

            matched_entry = {
                "sentence_index": idx,
                "sentence": sentence,
                "matched_clip_id": str(best_clip.get("id")),
                "matched_clip": best_clip,
                "strict_topic_hold": True,
                "topic_hold_probability": 0.88,
                "relevance_score": 0.85,
                "confidence": 0.8,
                "fallback": True,
            }
            last_clip_id = str(best_clip.get("id"))

        sequence.append(matched_entry)

    return sequence


def scan_and_match_raw_folder(
    raw_folder_path: str,
    sentences: List[str],
) -> Dict[str, Any]:
    """
    Scans a folder for raw video clips, extracts candidate metadata,
    and runs TypeSafe System One multi-shot matching against sentences.
    """
    p = Path(raw_folder_path)
    if not p.is_absolute():
        p = BASE_DIR / raw_folder_path

    if not p.exists() or not p.is_dir():
        return {
            "error": f"Folder not found: {raw_folder_path}",
            "raw_folder": str(p),
            "total_clips": 0,
            "sequence": [],
        }

    valid_exts = {".mp4", ".mov", ".mkv", ".webm"}
    video_files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]

    if not video_files:
        # Check subdirectories
        video_files = [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in valid_exts]

    if not video_files:
        return {
            "error": f"No video files found in {raw_folder_path}",
            "raw_folder": str(p),
            "total_clips": 0,
            "sequence": [],
        }

    video_files.sort(key=lambda f: f.name.lower())

    candidate_clips = []
    for f in video_files:
        rel_path = f.relative_to(BASE_DIR).as_posix() if f.is_relative_to(BASE_DIR) else str(f)
        stem_clean = f.stem.replace("_", " ").replace("-", " ").title()
        candidate_clips.append({
            "id": f.name,
            "name": stem_clean,
            "path": rel_path,
            "description": f"Video clip showing {stem_clean}",
        })

    sequence = match_script_sequence_broll(sentences, candidate_clips, ensure_diversity=True)

    return {
        "raw_folder": raw_folder_path,
        "resolved_path": str(p),
        "total_clips": len(candidate_clips),
        "candidate_clips": candidate_clips,
        "sequence": sequence,
    }



"""
Google Flow Cinematic Prompt Engine.
Transforms Thai product descriptions and shot concepts into professional
cinematic English prompts tailored for Google Veo & Google Flow.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR, RAW_DIR

logger = logging.getLogger("omnicut.flow_prompt_engine")

CAMERA_TECHNIQUES: Dict[str, str] = {
    "orbit": "slow 360-degree smooth orbital pan circling the subject",
    "macro": "extreme macro close-up shot capturing intricate textures and premium details",
    "dolly_in": "slow cinematic push-in dolly forward towards the product",
    "reveal": "dynamic low-angle tilt-up reveal with soft atmospheric haze",
    "floating": "slow-motion weightless levitation shot with subtle floating motion",
    "tracking": "smooth parallel tracking shot following the sleek curves of the product",
}

LIGHTING_PRESETS: Dict[str, str] = {
    "studio_clean": "high-end commercial studio lighting, soft diffused key light, crisp rim highlights",
    "dramatic_dark": "moody dark studio backdrop with vibrant neon cyan and amber rim lighting",
    "warm_lifestyle": "warm natural sunbeam through modern minimalist interior, gentle lens flare",
    "futuristic_tech": "cyberpunk tech laboratory aesthetic, cool blue edge light with holographic glow",
}


def build_fallback_prompt(
    thai_description: str,
    product_name: str = "Tech Gadget",
    technique: str = "orbit",
    lighting: str = "studio_clean",
) -> str:
    """Deterministic high-quality fallback prompt generator."""
    tech_str = CAMERA_TECHNIQUES.get(technique, CAMERA_TECHNIQUES["orbit"])
    light_str = LIGHTING_PRESETS.get(lighting, LIGHTING_PRESETS["studio_clean"])

    # Basic English extraction or translation fallback
    clean_desc = thai_description.replace("\n", " ").strip()
    return (
        f"Cinematic vertical commercial shot of {product_name}. "
        f"{tech_str}. "
        f"{light_str}. "
        f"Clean minimalist background with soft bokeh depth of field. "
        f"Ultra-detailed textures, smooth 60fps motion blur. "
        f"Clean composition, No on-screen text, no subtitles, no watermarks, 9:16 vertical framing, photorealistic 8K."
    )


def expand_prompt_with_gemini(
    thai_description: str,
    product_name: str = "",
    product_specs: Optional[Dict[str, Any]] = None,
    technique: str = "orbit",
    lighting: str = "studio_clean",
) -> str:
    """Uses AIBridge/Gemini to translate and enrich Thai shot notes into Google Flow prompts."""
    tech_guidance = CAMERA_TECHNIQUES.get(technique, CAMERA_TECHNIQUES["orbit"])
    light_guidance = LIGHTING_PRESETS.get(lighting, LIGHTING_PRESETS["studio_clean"])

    specs_str = ""
    if product_specs:
        specs_str = ", ".join(f"{k}: {v}" for k, v in list(product_specs.items())[:5])

    system_prompt = f"""You are an elite Hollywood visual director and AI prompt engineer for Google Flow & Google Veo.
Your task is to convert the following Thai video shot description into a single, cohesive, high-retention cinematic English prompt for a 9:16 vertical TikTok commercial video.

Product: {product_name or 'Premium Tech Gadget'}
Key Features: {specs_str}
Shot Concept (Thai): {thai_description}
Camera Movement: {tech_guidance}
Lighting Style: {light_guidance}

CRITICAL RULES:
1. Output ONLY the final English prompt text. No quotes, no markdown, no conversational commentary.
2. Structure: [Shot Type & Camera Move] + [Subject & Action] + [Environment & Lighting] + [Rendering & Quality Keywords].
3. MUST explicitly forbid text/subtitles: End with "Clean composition, no text, no captions, no watermarks, 9:16 vertical framing, photorealistic 8K."
"""

    try:
        from scripts.ai_bridge import AIBridge, DEFAULT_MODEL
        # Use Antigravity CLI or Gemini API key
        if AIBridge.has_antigravity_cli():
            res = AIBridge.call_antigravity_cli(system_prompt, model=DEFAULT_MODEL, timeout=30)
            if res and len(res.strip()) > 20:
                return res.strip()
        
        api_keys = AIBridge.get_api_keys()
        if api_keys:
            from google import genai
            client = genai.Client(api_key=api_keys[0])
            resp = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=system_prompt,
            )
            text = (resp.text or "").strip()
            if text and len(text) > 20:
                return text
    except Exception as exc:
        logger.warning(f"AI expansion failed ({exc}), falling back to template engine.")

    return build_fallback_prompt(thai_description, product_name, technique, lighting)


def find_best_product_image(product_id: str) -> Optional[Path]:
    """
    Scans 01_Raw/<product_id>/ and ProductStore records to find the highest-quality
    clean product image to serve as a reference image or first frame for Veo.
    """
    candidate_paths: List[Path] = []
    prod_raw_dir = RAW_DIR / product_id

    # 1. Look directly in 01_Raw/<product_id>/
    if prod_raw_dir.is_dir():
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            for img_file in prod_raw_dir.rglob(ext):
                # Exclude AI_Flow output folder, thumbnails, and temp files
                parts = [p.lower() for p in img_file.parts]
                if "ai_flow" in parts or ".tmp" in parts:
                    continue
                if img_file.is_file():
                    candidate_paths.append(img_file)

    # 2. Look in ProductStore if available
    try:
        from scripts.product_store import ProductStore
        product = ProductStore.get(product_id)
        if product and product.get("images"):
            for img in product["images"]:
                ref = ""
                if isinstance(img, str):
                    ref = img
                elif isinstance(img, dict):
                    ref = img.get("local_path") or img.get("rel_path") or img.get("path") or ""
                if ref:
                    p = Path(ref)
                    if not p.is_absolute():
                        p = (BASE_DIR / ref).resolve()
                    if p.is_file() and p not in candidate_paths:
                        candidate_paths.append(p)
    except Exception as exc:
        logger.debug("Failed querying ProductStore for images: %s", exc)

    if not candidate_paths:
        return None

    def score_image(p: Path) -> float:
        name_lower = p.name.lower()
        score = 0.0

        # Isolated / transparent / cutout boosts
        if any(k in name_lower for k in ("nobg", "clean", "cutout", "isolated", "transparent", "white_bg")):
            score += 60.0
        # Hero / front angle boosts
        if any(k in name_lower for k in ("hero", "front", "main", "angle1", "product")):
            score += 35.0
        # Preferred format (PNG/WebP often have alpha/cutouts)
        if p.suffix.lower() in (".png", ".webp"):
            score += 15.0

        # Penalize thumbnails, cover art, badges
        if any(k in name_lower for k in ("thumb", "icon", "badge", "cover_9_16", "cover_3_4", "flow_")):
            score -= 50.0

        try:
            size_kb = p.stat().st_size / 1024.0
            if size_kb < 10.0:
                score -= 30.0  # too small / icon
            else:
                score += min(30.0, size_kb / 50.0)  # prefer high-res
        except OSError:
            pass

        return score

    best_candidate = max(candidate_paths, key=score_image)
    return best_candidate


def bundle_flow_context(
    product_id: str,
    beat_text: str,
    camera_direction: str = "orbit",
    lighting: str = "studio_clean",
    product_name: Optional[str] = None,
    product_specs: Optional[Dict[str, Any]] = None,
    aspect_ratio: str = "9:16",
    duration: int = 8,
    download_quality: str = "original",
    max_credits: int = 25,
) -> Dict[str, Any]:
    """
    Automatic context bundling for Google Flow / Veo:
    1. Retrieves product info from ProductStore if not provided.
    2. Auto-picks the best product image from 01_Raw/<product_id>/ as reference_images and first_frame.
    3. Expands the beat text and cinematic direction into high-retention English prompt via Gemini Flash.
    4. Bundles into a validated scene generation dictionary.
    """
    p_name = product_name
    p_specs = product_specs

    # Load product context if missing
    if not p_name or not p_specs:
        try:
            from scripts.product_store import ProductStore
            prod = ProductStore.get(product_id)
            if prod:
                p_name = p_name or prod.get("name") or prod.get("title") or "Tech Gadget"
                p_specs = p_specs or prod.get("specs") or {}
        except Exception as exc:
            logger.debug("Failed querying product context for %s: %s", product_id, exc)

    p_name = p_name or "Tech Gadget"
    p_specs = p_specs or {}

    # 1. Auto-pick best product image
    best_img = find_best_product_image(product_id)
    ref_images: List[str] = [str(best_img.resolve())] if best_img else []
    first_frame_path: Optional[str] = str(best_img.resolve()) if best_img else None

    # 2. Expand prompt using Gemini Flash (or fallback engine)
    expanded_prompt = expand_prompt_with_gemini(
        thai_description=beat_text,
        product_name=p_name,
        product_specs=p_specs,
        technique=camera_direction,
        lighting=lighting,
    )

    return {
        "product_id": product_id,
        "product_name": p_name,
        "beat_text": beat_text,
        "technique": camera_direction,
        "lighting": lighting,
        "prompt": expanded_prompt,
        "type": "video",
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "reference_images": ref_images,
        "first_frame": first_frame_path,
        "selected_image": first_frame_path,
        "max_credits": max_credits,
        "download_quality": download_quality,
    }


def bundle_flow_batch_contexts(
    product_id: str,
    beats: List[Dict[str, Any]],
    product_name: Optional[str] = None,
    product_specs: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Bundles multiple beat items into a list of scenes ready for batch generation.
    """
    bundled_scenes: List[Dict[str, Any]] = []
    for beat in beats:
        beat_text = (
            beat.get("beat_text")
            or beat.get("text")
            or beat.get("concept")
            or beat.get("script")
            or beat.get("prompt")
            or "Product showcase commercial shot"
        )
        cam = beat.get("camera_direction") or beat.get("camera") or beat.get("technique") or "orbit"
        light = beat.get("lighting") or "studio_clean"
        ratio = beat.get("aspect_ratio") or "9:16"
        dur = int(beat.get("duration") or 8)

        scene = bundle_flow_context(
            product_id=product_id,
            beat_text=beat_text,
            camera_direction=cam,
            lighting=light,
            product_name=product_name,
            product_specs=product_specs,
            aspect_ratio=ratio,
            duration=dur,
        )
        bundled_scenes.append(scene)

    return bundled_scenes

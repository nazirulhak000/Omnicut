"""
Google Flow Cinematic Prompt Engine.
Transforms Thai product descriptions and shot concepts into professional
cinematic English prompts tailored for Google Veo & Google Flow.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

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
        f"Photorealistic 8k resolution, ultra-detailed textures, smooth 60fps motion blur. "
        f"Vertical 9:16 aspect ratio. No on-screen text, no subtitles, no watermarks."
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

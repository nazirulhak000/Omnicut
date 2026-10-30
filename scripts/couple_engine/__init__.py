# -*- coding: utf-8 -*-
"""Parameterized Couple Paper Chat (#5) Production Engine."""

from scripts.couple_engine.audio import (
    assemble_clip_audio,
    sanitize_inter_turn_glitches,
    split_by_longest_gaps,
    trim_dead_air,
)
from scripts.couple_engine.compose import (
    CANONICAL_COUPLE_TEMPLATE,
    compose_clip_html,
    generate_clip,
    layout_thread,
    sanitize_display_text,
)
from scripts.couple_engine.config import (
    ALLOWED_TTS_MODELS,
    BAO_VOICE_CONFIG,
    CANONICAL_PRODUCT_CONFIGS,
    DEFAULT_TTS_MODEL,
    NUI_VOICE_CONFIG,
    load_couple_product_config,
    validate_tts_model,
)
from scripts.couple_engine.finalize import finalize_clip_export
from scripts.couple_engine.inspect import (
    MAX_SNAPSHOT_BYTES,
    capture_visual_gate_snapshots,
    extract_cta_timestamp,
)
from scripts.couple_engine.render import (
    DEFAULT_MAX_WORKERS,
    encode_with_nvenc_fallback,
    is_valid_mp4,
    render_clip_parallel,
)
from scripts.couple_engine.tts import (
    QuotaExhaustedError,
    build_single_take_prompt,
    synthesize_couple_clip_passes,
)
from scripts.couple_engine.verify import verify_clip_transcript

__all__ = [
    "ALLOWED_TTS_MODELS",
    "BAO_VOICE_CONFIG",
    "CANONICAL_COUPLE_TEMPLATE",
    "CANONICAL_PRODUCT_CONFIGS",
    "DEFAULT_MAX_WORKERS",
    "DEFAULT_TTS_MODEL",
    "MAX_SNAPSHOT_BYTES",
    "NUI_VOICE_CONFIG",
    "QuotaExhaustedError",
    "assemble_clip_audio",
    "build_single_take_prompt",
    "capture_visual_gate_snapshots",
    "compose_clip_html",
    "encode_with_nvenc_fallback",
    "extract_cta_timestamp",
    "finalize_clip_export",
    "generate_clip",
    "is_valid_mp4",
    "layout_thread",
    "load_couple_product_config",
    "render_clip_parallel",
    "sanitize_display_text",
    "sanitize_inter_turn_glitches",
    "split_by_longest_gaps",
    "synthesize_couple_clip_passes",
    "trim_dead_air",
    "validate_tts_model",
    "verify_clip_transcript",
]

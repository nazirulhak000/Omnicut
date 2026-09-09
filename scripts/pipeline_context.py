"""
Pipeline Context for OmniCut Pro Studio Pipeline.
Encapsulates parameters, mutable stage state, and helper methods across all pipeline stages.
"""

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from scripts.config import (
    DEFAULT_VOICE, DEFAULT_VOICE_RATE
)
from scripts.project_manifest import ProjectManifest


@dataclass
class PipelineContext:
    """Carries inputs, options, intermediate results, and progress hooks through stages."""

    # 1. Pipeline Inputs
    product_name: str
    raw_video_path: str
    project_name: Optional[str] = None
    key_features: str = "แม่เหล็กแรงดูดสูง เสียบง่าย ชาร์จเร็ว ไม่ทำร้ายแบต"
    pain_point: str = "สายชาร์จพังง่าย เสียบยากในที่มืด"
    price_deal: str = "ลดพิเศษวันนี้"
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None
    voice: str = DEFAULT_VOICE
    voice_rate: str = DEFAULT_VOICE_RATE
    voice_engine_type: str = "edge_tts"
    voice_preset: Optional[str] = "gemini_puck_male_hype"
    ad_tone: str = "commercial_premium"
    human_voice_audio_path: Optional[str] = None
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None
    hook_duration: float = 3.0
    hook_motion: Optional[Dict[str, Any]] = None
    hook_colors: Optional[Dict[str, str]] = None
    hook_style: Optional[Dict[str, object]] = None
    font_name: str = "IBMPlex"
    bilingual_subtitles: bool = True
    use_ai_vision: bool = True
    sticker_path: Optional[str] = None
    bgm_name: Optional[str] = None
    bgm_volume: Optional[float] = None
    bgm_ducking: bool = True
    audio_mutes: Optional[Dict[str, bool]] = None
    lut_name: Optional[str] = None
    lut_intensity: float = 1.0
    clip_list: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[str]] = None
    export_mp4: bool = True
    export_preset: str = "post"
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    caption_position: str = "bottom"
    caption_color: Optional[str] = None
    caption_scale: float = 1.0
    text_overlays: Optional[List[Dict[str, Any]]] = None
    sticker_position: str = "top_right"
    sticker_scale: float = 1.0
    sticker_start_time: Optional[float] = None
    sticker_end_time: Optional[float] = None
    sticker_norm_x: Optional[float] = None
    sticker_norm_y: Optional[float] = None
    stickers: Optional[List[Dict[str, Any]]] = None
    effects: Optional[List[Dict[str, Any]]] = None
    resume_from: Optional[str] = None
    product_meta: Optional[Dict[str, Any]] = None
    angle_meta: Optional[Dict[str, Any]] = None
    progress_callback: Optional[Callable[[str, float], None]] = None
    overlays: Optional[List[Dict[str, Any]]] = None
    cancel_event: Optional[threading.Event] = None

    # 2. Stage Execution State
    project_dir: Optional[Path] = None
    is_reroll: bool = False
    manifest: Optional[Dict[str, Any]] = None
    raw_video: Optional[Path] = None
    is_image_source: bool = False
    image_files: List[str] = field(default_factory=list)

    voice_engine_used: str = "edge_tts"
    script_data: Optional[Dict[str, Any]] = None
    cues: List[Dict[str, Any]] = field(default_factory=list)
    micro_cues: List[Dict[str, Any]] = field(default_factory=list)
    total_duration: float = 0.0
    voice_audio_path: Optional[Path] = None

    ass_sub_path: Optional[Path] = None
    effective_overlays: List[Dict[str, Any]] = field(default_factory=list)
    effective_text_overlays: Optional[List[Dict[str, Any]]] = None
    scrim_spans: List[tuple] = field(default_factory=list)

    effective_bgm_name: Optional[str] = None
    mixed_audio_path: Optional[Path] = None

    actual_clip_list: Optional[List[Dict[str, Any]]] = None
    ai_matched_shots: Optional[List[Dict[str, Any]]] = None
    shot_scales: Optional[List[float]] = None

    out_mp4: Optional[Path] = None
    result_paths: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def notify(self, msg: str, progress: float) -> None:
        """Invokes the progress callback safely if one was registered."""
        if self.progress_callback:
            try:
                self.progress_callback(msg, progress)
            except Exception:
                pass

    def should_run(self, stage: str) -> bool:
        """Checks if a stage should execute or if its artifacts should be reused."""
        return ProjectManifest.should_run(stage, self.resume_from)

    def out_path(self, stem: str, suffix: str) -> Path:
        """Returns a versioned path when rerolling or standard project dir path."""
        if self.is_reroll and self.project_name:
            return ProjectManifest.versioned_path(self.project_name, stem, suffix)
        if self.project_dir:
            return self.project_dir / f"{stem}{suffix}"
        raise ValueError("Cannot resolve out_path before project_dir is set")

    def reuse(self, key: str, label: str) -> Path:
        """Retrieves existing artifact path from manifest for partial rerolls."""
        if not self.manifest:
            raise FileNotFoundError(f"สุ่มใหม่ไม่ได้ — ไม่พบ manifest สำหรับ {label}")
        existing = ProjectManifest.artifact_path(self.manifest, key)
        if not existing:
            raise FileNotFoundError(
                f"สุ่มใหม่ไม่ได้ — ไม่พบไฟล์ {label} ของรอบก่อน ต้อง render เต็มรอบใหม่"
            )
        return existing

"""
Pydantic Request and Response Schemas for OmniCut Pro Studio API.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class ScriptGenerateRequest(BaseModel):
    product_name: str
    key_features: str = "แม่เหล็กแรงดูดสูง เสียบง่าย ชาร์จเร็ว ไม่ทำร้ายแบต"
    pain_point: str = "สายชาร์จพังง่าย เสียบยากในที่มืด"
    price_deal: str = "ลดพิเศษวันนี้"
    template_key: str = "problem_solution"


class VoicePreviewRequest(BaseModel):
    text: Optional[str] = None
    voice_gender: Optional[str] = "male"
    speed: Optional[float] = 1.20
    ad_tone: Optional[str] = "commercial_hype"


class RenderRequest(BaseModel):
    product_name: str
    raw_video_path: str
    project_name: Optional[str] = None
    key_features: str
    pain_point: str
    price_deal: str
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None
    hook_motion: Optional[Dict[str, Any]] = None
    hook_colors: Optional[Dict[str, str]] = None
    hook_style: Optional[Dict[str, Any]] = None
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None
    voice_mode: str = "gemini_tts"
    voice_gender: str = "male"
    voice_rate: str = "+15%"
    voice_preset: Optional[str] = "gemini_fenrir_male_strong"
    ad_tone: Optional[str] = "commercial_hype"
    style_preset: str = "clean_tech_review"
    human_voice_audio: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    color_theme: Optional[Dict[str, Any]] = None
    spotlight: Optional[Dict[str, Any]] = None
    background_isolation: Optional[Dict[str, Any]] = None
    font_name: str = "IBMPlex"
    bilingual_subtitles: bool = True
    show_watermark: bool = True
    use_ai_vision: bool = True
    sticker_badge: Optional[str] = None
    bgm_name: Optional[str] = None
    bgm_volume: Optional[float] = None
    bgm_ducking: bool = False
    audio_mutes: Optional[Dict[str, bool]] = None
    lut_name: Optional[str] = None
    clip_list: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[Any]] = None
    export_mp4: bool = True
    caption_position: Optional[str] = "bottom"
    caption_color: Optional[str] = None
    caption_scale: Optional[float] = 1.0
    sticker_position: Optional[str] = "top_right"
    sticker_scale: Optional[float] = 1.0
    sticker_start_time: Optional[float] = None
    sticker_end_time: Optional[float] = None
    sticker_norm_x: Optional[float] = None
    sticker_norm_y: Optional[float] = None
    stickers: Optional[List[Dict[str, Any]]] = None
    effects: Optional[List[Dict[str, Any]]] = None
    text_overlays: Optional[List[Dict[str, Any]]] = None
    overlays: Optional[List[Dict[str, Any]]] = None
    shot_list_id: Optional[str] = None
    manual_shot_map: Optional[List[Dict[str, Any]]] = None


class DeleteFileRequest(BaseModel):
    file_path: str
    export_id: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None


class AddPostRequest(BaseModel):
    product_name: str
    clip_file: str
    platform: str = "tiktok"
    product_url: Optional[str] = ""
    angle_key: Optional[str] = ""
    angle_title: Optional[str] = ""
    hook: Optional[str] = ""
    caption: Optional[str] = ""
    hashtags: Optional[List[str]] = None
    posted_at: Optional[str] = None


class UpdatePostMetricsRequest(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    cart_clicks: Optional[int] = None
    orders: Optional[int] = None
    commission_thb: Optional[float] = None


class OpenFolderRequest(BaseModel):
    target: str


class TranscribeRequest(BaseModel):
    media_path: str
    lang: Optional[str] = "th"
    mode: str = "bilingual"
    words_per_line: int = 5
    fast: bool = True


class RenameVideoPayload(BaseModel):
    video_path: str
    new_name: str
    product_id: Optional[str] = None


class ReassignVideoPayload(BaseModel):
    video_path: str
    target_product_id: Optional[str] = None
    source_product_id: Optional[str] = None


class BatchDeleteVideosPayload(BaseModel):
    video_paths: List[str]


class LinkAngleRequest(BaseModel):
    video_path: str
    export_id: Optional[str] = None
    product_id: str
    angle_id: str


class OverlayLayoutRequest(BaseModel):
    text: str
    font_name: str = "Kanit"
    font_size_px: float = 75.0
    norm_x: float = 0.5
    norm_y: float = 0.5
    video_w: int = 1080
    video_h: int = 1920

"""Gemini TTS narration jobs owned by a Gadget Media project."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from scripts import render_jobs
from scripts.gadget_media_project import ProductVideoValidationError
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.gemini_tts_engine import GeminiFlashTTSEngine
from scripts.media_service import measure_wav_duration


def _clean_script(text: str) -> str:
    """Keep forbidden ellipses out of generated narration and subtitles."""
    return " ".join(str(text or "").replace("...", " ").replace("…", " ").split())


def project_narration_text(project: Any, override: str = "") -> str:
    if str(override or "").strip():
        return _clean_script(override)
    blocks = project.story.get("blocks") or []
    return _clean_script(" ".join(str(block.get("text") or "") for block in blocks))


def _next_voice_path(repository: GadgetMediaRepository, project_id: str) -> Path:
    voice_dir = repository.roots.project_layout(project_id)["voice"]
    version = 1
    while True:
        candidate = voice_dir / f"gemini_narration_v{version:02d}.wav"
        if not candidate.exists():
            return candidate
        version += 1


def execute_gadget_media_narration(
    job_id: str,
    project_id: str,
    repository: GadgetMediaRepository,
    *,
    script_text: str = "",
    voice_preset: str = "gemini_fenrir_male_strong",
    ad_tone: str = "commercial_expert",
    speed: float = 1.15,
) -> None:
    """Generate one versioned Gemini narration and attach it to the project."""
    try:
        with render_jobs.render_slot(job_id, channel_id=repository.channel_id):
            project = repository.get(project_id)
            text = project_narration_text(project, script_text)
            if not text:
                raise ProductVideoValidationError("Story ต้องมีบทพูดก่อนสร้าง Gemini TTS")

            output = _next_voice_path(repository, project_id)
            output.parent.mkdir(parents=True, exist_ok=True)
            render_jobs.update_progress(job_id, 0.1, "กำลังเตรียมบทพูด Gemini TTS", channel_id=repository.channel_id)
            GeminiFlashTTSEngine.generate_speech(
                text=text,
                output_path=str(output),
                voice_preset=voice_preset,
                ad_tone=ad_tone,
                speed=float(speed),
            )
            if not output.is_file():
                raise ProductVideoValidationError("Gemini TTS ไม่ได้สร้างไฟล์เสียง")

            duration = round(float(measure_wav_duration(output)), 3)
            presentation: Dict[str, Any] = {
                **project.presentation,
                "mode": "gemini_tts",
                "voice": voice_preset,
                "ad_tone": ad_tone,
                "speed": float(speed),
                "audio_path": str(output.resolve()),
                "audio_duration": duration,
                "audio_job_id": job_id,
            }
            repository.patch(project_id, {"presentation": presentation})
            render_jobs.complete_job(
                job_id,
                {
                    "project_id": project_id,
                    "audio_path": str(output.resolve()),
                    "duration": duration,
                },
                message="สร้าง Gemini TTS สำหรับ Product Project เสร็จแล้ว",
             channel_id=repository.channel_id)
    except render_jobs.RenderCancelled:
        render_jobs.cancel_job(job_id, channel_id=repository.channel_id)
    except Exception as exc:
        render_jobs.fail_job(job_id, exc, channel_id=repository.channel_id)

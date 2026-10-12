"""Background renderer that keeps every Gadget Media artifact in its namespace."""

from __future__ import annotations

from datetime import datetime
import subprocess
from pathlib import Path
from typing import Any, Dict

from scripts import render_jobs
from scripts.export_registry import ExportRegistry
from scripts.gadget_media_project import ProductVideoValidationError, new_id, utc_now
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.video_editor import VideoEditor
from scripts.subtitle_engine import SubtitleEngine
from scripts.channel_identity import resolve_channel_identity


EMPTY_ASS = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,82,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _run_audio_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"เตรียมเสียงสำหรับ Gadget Media ไม่สำเร็จ: {(result.stderr or '')[-500:]}")


def _prepare_audio(repository: GadgetMediaRepository, project_id: str, duration: float) -> Path:
    project = repository.get(project_id)
    layout = repository.roots.project_layout(project_id)
    output = layout["mix"] / "render_mix.wav"
    configured = str(project.presentation.get("audio_path") or "").strip()
    project_root = layout["project"].resolve(strict=False)
    configured_path = Path(configured) if configured else None
    source = (
        configured_path.resolve(strict=False)
        if configured_path and configured_path.is_absolute()
        else (project_root / configured_path).resolve(strict=False)
        if configured_path
        else None
    )
    if source and source.is_file() and (source == project_root or project_root in source.parents):
        _run_audio_command([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-af", "apad", "-t", f"{duration:.3f}", "-ac", "2", "-ar", "44100", str(output),
        ])
    elif project.presentation.get("mode") == "product_only":
        _run_audio_command([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", f"{duration:.3f}", str(output),
        ])
    else:
        raise ProductVideoValidationError(
            "โหมดเสียงที่เลือกต้องมี audio_path ซึ่งอยู่ภายในโฟลเดอร์ Product Project"
        )
    return output


def _next_output(repository: GadgetMediaRepository, project_id: str) -> tuple[Path, int]:
    project = repository.get(project_id)
    identity = project.product_identity
    stem = "-".join(
        part.strip().lower().replace(" ", "-")
        for part in (str(identity.get("brand") or "product"), str(identity.get("model") or "video"))
    )
    version = 1 + sum(1 for item in project.artifacts if item.get("kind") == "render")
    filename = f"{datetime.now():%Y%m%d}_{stem}_master_v{version:02d}.mp4"
    output = repository.roots.export_dir(project_id) / filename
    while output.exists():
        version += 1
        output = output.with_name(f"{datetime.now():%Y%m%d}_{stem}_master_v{version:02d}.mp4")
    return output, version


def execute_gadget_media_render(
    job_id: str,
    project_id: str,
    repository: GadgetMediaRepository,
    *,
    export_preset: str = "post",
) -> None:
    """Render one saved timeline and register the result only after FFmpeg succeeds."""
    try:
        with render_jobs.render_slot(job_id, channel_id=repository.channel_id):
            project = repository.get(project_id)
            if not project.quality_report.get("passed"):
                raise ProductVideoValidationError("quality gates must pass before rendering")
            timeline = repository.load_timeline(project_id)
            clips = timeline.get("clips") or []
            duration = float(timeline.get("duration") or 0)
            if not clips or duration <= 0:
                raise ProductVideoValidationError("timeline has no renderable clips")
            for clip in clips:
                source = Path(str(clip.get("source_path") or "")).resolve(strict=False)
                if not source.is_file():
                    raise ProductVideoValidationError(f"source file is missing: {source}")

            output, version = _next_output(repository, project_id)
            output.parent.mkdir(parents=True, exist_ok=True)
            ass_path = repository.roots.project_layout(project_id)["review"] / "empty_subtitles.ass"
            if repository.channel_id is not None:
                job = render_jobs.get_job(job_id, channel_id=repository.channel_id) or {}
                identity = resolve_channel_identity(job.get("channel_identity_snapshot"), channel_id=repository.channel_id)
                SubtitleEngine.generate_ass(
                    cues=[], output_ass_path=str(ass_path), bilingual=False,
                    channel_identity_snapshot=identity,
                )
            else:
                ass_path.write_text(EMPTY_ASS, encoding="utf-8")
            audio_path = _prepare_audio(repository, project_id, duration)
            cancel_event = render_jobs.get_cancel_event(job_id, channel_id=repository.channel_id)

            def on_progress(current: float, total: float) -> None:
                ratio = current / total if total else 0
                render_jobs.update_progress(
                    job_id,
                    0.08 + min(0.88, max(0.0, ratio) * 0.88),
                    f"กำลัง Render Gadget Media {int(ratio * 100)}%",
                 channel_id=repository.channel_id)

            render_jobs.update_progress(job_id, 0.05, "กำลังเตรียม Timeline และเสียง", channel_id=repository.channel_id)
            VideoEditor.assemble_tiktok_video(
                raw_video_paths=[str(clip["source_path"]) for clip in clips],
                total_duration=duration,
                mixed_audio_path=str(audio_path),
                ass_subtitle_path=str(ass_path),
                output_mp4_path=str(output),
                clip_list=clips,
                transitions=[clip.get("transition_in") or "cut" for clip in clips[1:]],
                export_preset=export_preset,
                style_preset="clean_tech_review",
                progress_callback=on_progress,
                cancel_event=cancel_event,
            )
            artifact = {
                "artifact_id": new_id("render"),
                "kind": "render",
                "version": version,
                "path": str(output),
                "duration": duration,
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "approved": False,
                "created_at": utc_now(),
                "job_id": job_id,
                **({"channel_identity_snapshot": identity} if repository.channel_id is not None else {}),
            }
            repository.add_render_artifact(project_id, artifact)
            job = render_jobs.get_job(job_id, channel_id=repository.channel_id) or {}
            if repository.channel_id is not None:
                ExportRegistry.ensure(str(output), project_name="GadgetMedia/" + project_id, channel_id=repository.channel_id, job_scope={key: value for key, value in job.items() if key.startswith("channel_")} or None)
            render_jobs.complete_job(job_id, {
                "mp4_video": str(output),
                "duration": duration,
                "manifest": str(repository.roots.project_dir(project_id) / "project.json"),
            }, message="Render Gadget Media เสร็จสมบูรณ์", channel_id=repository.channel_id)
            job = render_jobs.get_job(job_id, channel_id=repository.channel_id)
            if job and isinstance(job.get("result"), dict):
                job["result"].update({"project_id": project_id, "artifact_id": artifact["artifact_id"]})
    except render_jobs.RenderCancelled:
        render_jobs.cancel_job(job_id, channel_id=repository.channel_id)
    except Exception as exc:
        render_jobs.fail_job(job_id, exc, channel_id=repository.channel_id)

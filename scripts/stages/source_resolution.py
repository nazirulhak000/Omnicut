"""
Source Resolution Stage for OmniCut Pro Studio.
Resolves raw video / image assets, verifies integrity, establishes project folder and manifest state.
"""

import re
from pathlib import Path
from typing import List

from scripts.config import BASE_DIR, RAW_DIR, INBOX_DIR, PROJECTS_DIR
from scripts.project_manifest import ProjectManifest
from scripts.pipeline_context import PipelineContext


class SourceResolutionStage:
    """Resolves and validates input media files, creates project directory, loads manifest for reroll."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        raw_video = None
        raw_video_path = ctx.raw_video_path
        if raw_video_path:
            p = Path(raw_video_path)
            if p.exists():
                raw_video = p.resolve()
            elif (BASE_DIR / raw_video_path).exists():
                raw_video = (BASE_DIR / raw_video_path).resolve()
            elif (RAW_DIR / p.name).exists():
                raw_video = (RAW_DIR / p.name).resolve()
            elif (INBOX_DIR / p.name).exists():
                raw_video = (INBOX_DIR / p.name).resolve()
            else:
                matched_raw = list(RAW_DIR.glob(f"**/{p.name}"))
                matched_inbox = list(INBOX_DIR.glob(f"**/{p.name}"))
                if matched_raw:
                    raw_video = matched_raw[0].resolve()
                elif matched_inbox:
                    raw_video = matched_inbox[0].resolve()
                else:
                    raw_video = p.resolve()

        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        is_image_source = False
        image_files: List[str] = []

        if raw_video and raw_video.is_dir():
            image_files = [str(f) for f in raw_video.iterdir() if f.suffix.lower() in image_extensions]
            if image_files:
                is_image_source = True
        elif raw_video and raw_video.is_file() and raw_video.suffix.lower() in image_extensions:
            is_image_source = True
            image_files = [str(raw_video)]
        elif not raw_video or not raw_video.exists():
            candidate_imgs = list((INBOX_DIR / "product_images").glob("**/*.*")) + list(INBOX_DIR.glob("*.*"))
            valid_imgs = [str(f) for f in candidate_imgs if f.suffix.lower() in image_extensions]
            if valid_imgs:
                is_image_source = True
                image_files = valid_imgs[:6]
            else:
                raise FileNotFoundError(f"ไม่พบไฟล์วิดีโอดิบหรือรูปสินค้า: '{raw_video_path}' กรุณาตรวจสอบตำแหน่งไฟล์")

        if raw_video and raw_video.is_file() and not is_image_source:
            if raw_video.stat().st_size < 1024:
                raise ValueError(f"ไฟล์วิดีโอ '{raw_video.name}' มีขนาด 0 bytes หรือเสียหาย กรุณาตรวจสอบไฟล์ต้นฉบับ")

        if ctx.clip_list:
            for c_idx, c_item in enumerate(ctx.clip_list):
                c_src = c_item.get("source_path")
                if c_src:
                    c_path = Path(c_src)
                    if not c_path.is_absolute():
                        c_path = BASE_DIR / c_src
                    if c_path.exists() and c_path.is_file() and c_path.stat().st_size < 1024:
                        raise ValueError(f"คลิปที่ {c_idx + 1} ('{c_path.name}') มีขนาด 0 bytes หรือเสียหาย")

        # Determine Project Name
        project_name = ctx.project_name
        if not project_name:
            cleaned = re.sub(r'\[[^\]]*\]', ' ', ctx.product_name or '')
            cleaned = re.sub(r'\([^)]*\)', ' ', cleaned)
            words = [w for w in re.sub(r'[^a-zA-Z0-9ก-๙\s_-]', ' ', cleaned).strip().split() if w]
            short_prod = "_".join(words[:3]).lower() if words else "video"
            base = short_prod
            candidate = f"{base}_1"
            v = 1
            while (PROJECTS_DIR / candidate).exists():
                v += 1
                candidate = f"{base}_{v}"
            project_name = candidate
            ctx.project_name = project_name

        project_dir = PROJECTS_DIR / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        ctx.project_dir = project_dir

        is_reroll = bool(ctx.resume_from)
        ctx.is_reroll = is_reroll
        ctx.manifest = ProjectManifest.require(project_name) if is_reroll else None
        ctx.raw_video = raw_video
        ctx.is_image_source = is_image_source
        ctx.image_files = image_files

        print(f"\n=======================================================")
        print(f"🎬 Starting OmniCut Pro Studio for: {ctx.product_name}")
        print(f"📁 Project Folder: {project_dir}")
        if is_reroll:
            print(f"♻️  Re-roll from stage: {ctx.resume_from}")
        print(f"=======================================================\n")

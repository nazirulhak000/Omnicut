"""
Project manifest — what makes a partial re-roll possible.

The pipeline used to keep script_data, cues, micro_cues and total_duration as
locals and throw them away when it returned, and it overwrote voiceover.wav /
subtitles.ass / mixed_audio.wav in place on every run. That left "change only
the hook" no cheaper than rebuilding the whole clip.

This module writes those four values plus every artifact path to
03_Projects/<name>/project.json, and hands out versioned filenames so an
earlier take is never destroyed.
"""

import json
import shutil
import datetime
import threading
import uuid
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import PROJECTS_DIR

MANIFEST_NAME = "project.json"
MANIFEST_VERSION = 1

# Ordered stages of the pipeline. Re-rolling from a stage reruns it and
# everything after it; everything before is reused from disk.
# "mix" sits between voice and subtitles: swapping the music bed, its level or
# ducking only needs the audio re-mixed, never the voiceover re-synthesized.
STAGES = ("script", "voice", "mix", "subtitles", "video")

# Which stage each re-roll button starts from.
#
# Note micro_cues depend only on `cues` — font, bilingual and hook_title do not
# move any timing (see SubtitleEngine.generate_ass). So a hook or subtitle
# re-roll keeps mixed_audio.wav untouched and only redraws the .ass, which is
# why those are the cheap buttons.
REROLL_STAGE = {
    "hook": "subtitles",
    "subtitles": "subtitles",
    "voice": "voice",
    # Music changes re-mix the audio and rebuild everything after it, but
    # reuse the voiceover that is already on disk.
    "bgm": "mix",
    "script": "script",
    "video": "video",
}


class ProjectManifest:
    """Reads and writes the per-project state the re-roll endpoints depend on."""

    # ------------------------------------------------------------------
    # Locating
    # ------------------------------------------------------------------
    @classmethod
    def dir_for(cls, project_name: str) -> Path:
        return PROJECTS_DIR / project_name

    @classmethod
    def path_for(cls, project_name: str) -> Path:
        return cls.dir_for(project_name) / MANIFEST_NAME

    # ------------------------------------------------------------------
    # Reading / writing
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, project_name: str) -> Optional[Dict[str, Any]]:
        path = cls.path_for(project_name)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return data if isinstance(data, dict) else None

    @classmethod
    def require(cls, project_name: str) -> Dict[str, Any]:
        manifest = cls.load(project_name)
        if not manifest:
            raise ValueError(
                f"ไม่พบ manifest ของโปรเจกต์ '{project_name}' — ต้อง render เต็มรอบอย่างน้อย 1 ครั้งก่อนถึงจะสุ่มใหม่ได้"
            )
        return manifest

    _SAVE_LOCK = threading.Lock()

    @classmethod
    def save(cls, project_name: str, **fields: Any) -> Dict[str, Any]:
        """Merge `fields` into the manifest and write it out safely with lock and retry."""
        with cls._SAVE_LOCK:
            project_dir = cls.dir_for(project_name)
            project_dir.mkdir(parents=True, exist_ok=True)

            manifest = cls.load(project_name) or {
                "manifest_version": MANIFEST_VERSION,
                "project_name": project_name,
                "created_at": cls._now(),
                "artifacts": {},
            }

            artifacts = fields.pop("artifacts", None)
            manifest.update(fields)
            if artifacts:
                manifest.setdefault("artifacts", {}).update(artifacts)
            manifest["updated_at"] = cls._now()

            path = cls.path_for(project_name)
            tmp = path.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
            tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            last_err = None
            for attempt in range(5):
                try:
                    tmp.replace(path)
                    last_err = None
                    break
                except PermissionError as e:
                    last_err = e
                    time.sleep(0.04 * (attempt + 1))

            if last_err is not None:
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass
                raise last_err

            return manifest

    @classmethod
    def record_artifact(cls, project_name: str, key: str, path: Any) -> None:
        """Note that an artifact was (re)generated, with the time it happened."""
        cls.save(project_name, artifacts={key: {"path": str(path), "created_at": cls._now()}})

    # ------------------------------------------------------------------
    # Versioned filenames
    # ------------------------------------------------------------------
    @classmethod
    def versioned_path(cls, project_name: str, stem: str, suffix: str) -> Path:
        """
        Return the next free `<stem>_vN<suffix>` in the project folder.

        Re-rolling a voice should not destroy the take the user might want back,
        so every regenerated artifact lands on a new number.
        """
        project_dir = cls.dir_for(project_name)
        project_dir.mkdir(parents=True, exist_ok=True)

        version = 1
        while (project_dir / f"{stem}_v{version}{suffix}").exists():
            version += 1
        return project_dir / f"{stem}_v{version}{suffix}"

    # ------------------------------------------------------------------
    # Resume helpers
    # ------------------------------------------------------------------
    @classmethod
    def stage_index(cls, stage: str) -> int:
        try:
            return STAGES.index(stage)
        except ValueError:
            raise ValueError(f"stage '{stage}' ไม่ถูกต้อง — ต้องเป็นหนึ่งใน {', '.join(STAGES)}")

    @classmethod
    def should_run(cls, stage: str, resume_from: Optional[str]) -> bool:
        """True when `stage` must be (re)generated for a run starting at `resume_from`."""
        if not resume_from:
            return True
        return cls.stage_index(stage) >= cls.stage_index(resume_from)

    @classmethod
    def artifact_path(cls, manifest: Dict[str, Any], key: str) -> Optional[Path]:
        """The recorded path for an artifact, if it is still on disk."""
        entry = (manifest.get("artifacts") or {}).get(key)
        if not entry:
            return None
        path = Path(entry["path"])
        return path if path.exists() else None

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------
    @classmethod
    def list_projects(cls) -> List[Dict[str, Any]]:
        """Every project that has a manifest, newest first."""
        projects = []
        if not PROJECTS_DIR.exists():
            return projects

        for child in PROJECTS_DIR.iterdir():
            if not child.is_dir():
                continue
            manifest = cls.load(child.name)
            if not manifest:
                continue
            projects.append({
                "project_name": manifest.get("project_name", child.name),
                "product_name": (manifest.get("product") or {}).get("name", ""),
                "angle_title": (manifest.get("angle") or {}).get("title", ""),
                "duration": manifest.get("total_duration"),
                "updated_at": manifest.get("updated_at", ""),
                "mp4_video": (manifest.get("artifacts") or {}).get("mp4_video", {}).get("path"),
                # so the UI can say how much deleting one frees
                "size_mb": cls.folder_size_mb(child),
            })

        return sorted(projects, key=lambda p: p.get("updated_at", ""), reverse=True)

    @staticmethod
    def folder_size_mb(folder: Path) -> float:
        total = 0
        try:
            for f in folder.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        except OSError:
            return 0.0
        return round(total / (1024 * 1024), 2)

    @classmethod
    def delete(cls, project_name: str) -> Dict[str, Any]:
        """
        Remove a project folder and everything in it.

        Only the working files live here -- script, voiceover, subtitles, the
        mixed audio. A rendered mp4 sits in 04_Exports and is deliberately left
        alone: deleting the project you edited should never take away the video
        you already posted.
        """
        target = (PROJECTS_DIR / project_name).resolve()
        root = PROJECTS_DIR.resolve()

        # a name like "../02_Assets" would otherwise resolve outside the folder
        if root not in target.parents:
            raise ValueError(f"'{project_name}' อยู่นอกโฟลเดอร์โปรเจกต์")
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError(f"ไม่พบโปรเจกต์ '{project_name}'")
        if target.name.startswith("_"):
            raise ValueError(f"'{target.name}' เป็นโฟลเดอร์ระบบ ลบไม่ได้")

        size = cls.folder_size_mb(target)
        files = sum(1 for f in target.rglob("*") if f.is_file())
        shutil.rmtree(target)
        return {"project_name": target.name, "size_mb": size, "files_removed": files}

    # ------------------------------------------------------------------
    @staticmethod
    def _now() -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    for project in ProjectManifest.list_projects():
        print(json.dumps(project, ensure_ascii=False))

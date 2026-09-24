"""
Project manifest — what makes a partial re-roll possible.

The pipeline used to keep script_data, cues, micro_cues and total_duration as
locals and throw them away when it returned, and it overwrote voiceover.wav /
subtitles.ass / mixed_audio.wav in place on every run. That left "change only
the hook" no cheaper than rebuilding the whole clip.

This module writes those four values plus every artifact path to
03_Projects/<name>/project.json, and hands out versioned filenames so an
earlier take is never destroyed.

Artifact paths (manifest["artifacts"][key]["path"]) are normalized to
BASE_DIR-relative on the way in (`save()`) and resolved back to an absolute
Path on the way out (`artifact_path()`) -- see scripts/path_utils.py for the
full convention and SAAS_READINESS_PLAN.md P0 item 4 for why. Callers
(video_assembly_stage.py and friends) still just pass whatever path str()
gives them; this module is the one place that funnels every artifact write,
so the normalization lives here rather than at each caller.
"""

import gc
import json
import shutil
import datetime
import threading
import uuid
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from scripts.config import PROJECTS_DIR, BASE_DIR, ARCHIVE_DIR
from scripts import path_utils

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
        target = (PROJECTS_DIR / project_name).resolve()
        root = PROJECTS_DIR.resolve()

        # Same containment check delete() already uses (see below): a
        # project_name containing ".." -- or, on Windows, a literal
        # backslash smuggled past a forward-slash-only routing regex, e.g.
        # via a %5C-encoded route parameter -- would otherwise resolve
        # outside 03_Projects/. load()/save()/versioned_path() all fall
        # through this one choke point, so guarding it here is what makes
        # them safe too, not just delete().
        if root not in target.parents:
            raise ValueError(f"'{project_name}' อยู่นอกโฟลเดอร์โปรเจกต์")
        return target

    @classmethod
    def path_for(cls, project_name: str) -> Path:
        return cls.dir_for(project_name) / MANIFEST_NAME

    # ------------------------------------------------------------------
    # Reading / writing
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, project_name: str) -> Optional[Dict[str, Any]]:
        path = cls.path_for(project_name)
        bak_path = path.with_suffix(".json.bak")
        rolling_backups = [
            path.with_suffix(".json.bak1"),
            path.with_suffix(".json.bak2"),
            path.with_suffix(".json.bak3"),
        ]
        if not path.exists() and not bak_path.exists() and not any(backup.exists() for backup in rolling_backups):
            return None
        last_err = None
        for attempt in range(8):
            try:
                if path.exists():
                    content = path.read_text(encoding="utf-8")
                    if content.strip():
                        data = json.loads(content)
                        if isinstance(data, dict):
                            return data
                time.sleep(0.04 * (attempt + 1))
            except (json.JSONDecodeError, OSError) as err:
                last_err = err
                time.sleep(0.04 * (attempt + 1))

        # Fallback to .bak sequence (.bak1, .bak, .bak2, .bak3) if primary file is corrupted or empty
        candidate_baks = [rolling_backups[0], bak_path, *rolling_backups[1:]]
        for b_path in candidate_baks:
            if b_path.exists():
                try:
                    bak_content = b_path.read_text(encoding="utf-8")
                    if bak_content.strip():
                        data = json.loads(bak_content)
                        if isinstance(data, dict):
                            print(f"🛡️ [ProjectManifest.load] Recovered valid manifest for '{project_name}' from backup ({b_path.name}).")
                            return data
                except Exception as bak_err:
                    last_err = bak_err

        if last_err:
            print(f"[ProjectManifest.load] Warning: Failed to read manifest at {path} after retries: {last_err}")
        return None

    @classmethod
    def require(cls, project_name: str) -> Dict[str, Any]:
        manifest = cls.load(project_name)
        if not manifest:
            path = cls.path_for(project_name)
            if path.exists():
                time.sleep(0.1)
                manifest = cls.load(project_name)
                if manifest:
                    return manifest
            raise ValueError(
                f"ไม่พบ manifest ของโปรเจกต์ '{project_name}' — ต้อง render เต็มรอบอย่างน้อย 1 ครั้งก่อนถึงจะสุ่มใหม่ได้"
            )
        return manifest

    _SAVE_LOCK = threading.Lock()

    @staticmethod
    def _normalize_artifacts(artifacts: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Rewrite every artifact entry's `path` to BASE_DIR-relative before
        it is persisted. Callers today (video_assembly_stage.py,
        rename_projects_with_product_code.py) build these entries as
        `{"path": str(some_absolute_path), ...other fields}` -- this leaves
        every other field untouched and only touches `path`."""
        if not artifacts:
            return artifacts
        normalized: Dict[str, Any] = {}
        for key, entry in artifacts.items():
            if isinstance(entry, dict) and entry.get("path"):
                entry = dict(entry)
                entry["path"] = path_utils.to_relative(entry["path"], base_dir=BASE_DIR)
            normalized[key] = entry
        return normalized

    @classmethod
    def save(cls, project_name: str, **fields: Any) -> Dict[str, Any]:
        """Merge `fields` into the manifest and write it out safely with lock and retry."""
        with cls._SAVE_LOCK:
            return cls._save_locked(project_name, **fields)

    @classmethod
    def save_merge(cls, project_name: str, mutator: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        """Read-decide-write as one atomic unit under `_SAVE_LOCK`.

        `save()`'s own write is already atomic (it holds `_SAVE_LOCK` for its
        load+merge+write), but a caller that reads the manifest *before*
        calling `save()` -- to decide what new field values should be, based
        on the current state -- is not protected: another `save()` (an
        autosave, a render pipeline finishing, another reroll) can land in
        the gap between that read and this call's write, and this call's
        stale-derived fields then silently clobber it. `save_merge()` closes
        that gap by doing the read inside the same lock the write uses, so
        nothing else can interleave between them.

        `mutator` is called with the freshly-loaded manifest (or `{}` if none
        exists yet) and must return the `**fields` dict `save()` would have
        received -- same shape/semantics, just computed from inside the lock
        instead of before it.
        """
        with cls._SAVE_LOCK:
            current = cls.load(project_name) or {}
            fields = mutator(current)
            return cls._save_locked(project_name, **fields)

    @classmethod
    def _save_locked(cls, project_name: str, **fields: Any) -> Dict[str, Any]:
        """The actual write. Callers must already hold `_SAVE_LOCK` --
        `save()` acquires it itself and `save_merge()` holds it across its
        read+decide+write, so the two never interleave. Split out only so
        `save_merge()` has something to call without re-entering `_SAVE_LOCK`,
        which is a plain (non-reentrant) `threading.Lock`."""
        project_dir = cls.dir_for(project_name)
        project_dir.mkdir(parents=True, exist_ok=True)

        manifest = cls.load(project_name) or {
            "manifest_version": MANIFEST_VERSION,
            "project_name": project_name,
            "created_at": cls._now(),
            "artifacts": {},
        }

        artifacts = cls._normalize_artifacts(fields.pop("artifacts", None))
        manifest.update(fields)
        if artifacts:
            manifest.setdefault("artifacts", {}).update(artifacts)
        manifest["updated_at"] = cls._now()

        path = cls.path_for(project_name)
        bak_path = path.with_suffix(".json.bak")
        bak1 = path.with_suffix(".json.bak1")
        bak2 = path.with_suffix(".json.bak2")
        bak3 = path.with_suffix(".json.bak3")
        tmp = path.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
        try:
            tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            # A full disk can leave a partly written JSON temp file. Never
            # leave it beside the last good manifest or mask the write error.
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

        if path.exists():
            try:
                # Rolling 3-version snapshot: .bak2 -> .bak3, .bak1 -> .bak2, path -> .bak1 (and .bak for compat)
                if bak2.exists():
                    try:
                        shutil.copy2(bak2, bak3)
                    except Exception:
                        pass
                if bak1.exists():
                    try:
                        shutil.copy2(bak1, bak2)
                    except Exception:
                        pass
                shutil.copy2(path, bak1)
                shutil.copy2(path, bak_path)
            except Exception as bak_err:
                # Backup is best-effort but must never fail *silently*
                print(f"[ProjectManifest.save] Warning: failed to back up '{project_name}' before saving: {bak_err}")

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
        """The recorded path for an artifact, if it is still on disk.

        Resolves through path_utils.to_absolute() so this works whether the
        stored entry is BASE_DIR-relative (new data, or old data run through
        scripts/migrate_paths_to_relative.py) or a legacy absolute path (old,
        un-migrated project.json files still on disk)."""
        entry = (manifest.get("artifacts") or {}).get(key)
        if not entry or not entry.get("path"):
            return None
        path = path_utils.to_absolute(entry["path"], base_dir=BASE_DIR)
        return path if path and path.exists() else None

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
            mp4_entry = (manifest.get("artifacts") or {}).get("mp4_video")
            mp4_path = mp4_entry.get("path") if isinstance(mp4_entry, dict) else None
            projects.append({
                "project_name": manifest.get("project_name", child.name),
                "product_name": (manifest.get("product") or {}).get("name", ""),
                "angle_title": (manifest.get("angle") or {}).get("title", ""),
                "duration": manifest.get("total_duration"),
                "updated_at": manifest.get("updated_at", ""),
                "mp4_video": mp4_path,
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
        # A file inside this folder can still be briefly held open by the
        # media server (a <video>/<audio> range read that hasn't finished
        # closing yet) -- retry a couple times before surfacing WinError 32
        # to the caller, same shape as _move_with_retry in api_videos.py.
        for attempt in range(3):
            try:
                shutil.rmtree(target)
                break
            except OSError as err:
                if getattr(err, "winerror", None) != 32 or attempt == 2:
                    raise
                gc.collect()
                time.sleep(0.3)
        return {"project_name": target.name, "size_mb": size, "files_removed": files}

    @classmethod
    def archive(cls, project_name: str) -> Dict[str, Any]:
        """
        Move a project folder from 03_Projects to 06_Archive/Projects.
        Leaves exported MP4s in 04_Exports intact.
        """
        target = (PROJECTS_DIR / project_name).resolve()
        root = PROJECTS_DIR.resolve()

        if root not in target.parents:
            raise ValueError(f"'{project_name}' อยู่นอกโฟลเดอร์โปรเจกต์")
        if not target.exists() or not target.is_dir():
            raise FileNotFoundError(f"ไม่พบโปรเจกต์ '{project_name}'")
        if target.name.startswith("_"):
            raise ValueError(f"'{target.name}' เป็นโฟลเดอร์ระบบ ย้ายไม่ได้")

        archive_projects_dir = (ARCHIVE_DIR / "Projects").resolve()
        archive_projects_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_projects_dir / target.name

        size = cls.folder_size_mb(target)
        files = sum(1 for f in target.rglob("*") if f.is_file())

        for attempt in range(3):
            try:
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(target), str(dest))
                break
            except OSError as err:
                if getattr(err, "winerror", None) != 32 or attempt == 2:
                    raise
                gc.collect()
                time.sleep(0.3)

        return {
            "project_name": target.name,
            "archived_to": str(dest.relative_to(BASE_DIR)).replace("\\", "/"),
            "size_mb": size,
            "files_moved": files,
        }

    # ------------------------------------------------------------------
    # Snapshot / Backup Management
    # ------------------------------------------------------------------
    @classmethod
    def get_snapshots(cls, project_name: str) -> List[Dict[str, Any]]:
        """Returns list of available snapshot files (.bak1, .bak2, .bak3) for project."""
        path = cls.path_for(project_name)
        candidates = [
            ("bak1", path.with_suffix(".json.bak1")),
            ("bak2", path.with_suffix(".json.bak2")),
            ("bak3", path.with_suffix(".json.bak3")),
            ("bak", path.with_suffix(".json.bak")),
        ]
        snapshots = []
        seen_paths = set()
        for snap_id, s_path in candidates:
            if s_path.exists() and str(s_path) not in seen_paths:
                seen_paths.add(str(s_path))
                stat = s_path.stat()
                is_valid = False
                title = ""
                try:
                    data = json.loads(s_path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        is_valid = True
                        title = data.get("title") or data.get("project_name", "")
                except Exception:
                    pass
                snapshots.append({
                    "id": snap_id,
                    "filename": s_path.name,
                    "size_bytes": stat.st_size,
                    "updated_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    "is_valid": is_valid,
                    "title": title
                })
        return snapshots

    @classmethod
    def restore_snapshot(cls, project_name: str, snapshot_id: str) -> Dict[str, Any]:
        """Restores manifest from a specified snapshot (bak1, bak2, bak3, bak)."""
        with cls._SAVE_LOCK:
            path = cls.path_for(project_name)
            s_map = {
                "bak1": path.with_suffix(".json.bak1"),
                "bak2": path.with_suffix(".json.bak2"),
                "bak3": path.with_suffix(".json.bak3"),
                "bak": path.with_suffix(".json.bak"),
            }
            target_snap = s_map.get(snapshot_id.lower())
            if not target_snap or not target_snap.exists():
                raise ValueError(f"ไม่พบไฟล์สำรอง '{snapshot_id}' สำหรับโปรเจกต์ '{project_name}'")

            content = target_snap.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError(f"ไฟล์สำรอง '{snapshot_id}' ข้อมูลไม่ถูกต้อง")

            # Backup current broken/existing file before restoring
            if path.exists():
                corrupt_bak = path.with_suffix(f".json.corrupted_{int(time.time())}")
                try:
                    shutil.copy2(path, corrupt_bak)
                except Exception:
                    pass

            shutil.copy2(target_snap, path)
            print(f"🛡️ [ProjectManifest.restore_snapshot] Restored '{project_name}' from {snapshot_id}")
            return data

    # ------------------------------------------------------------------
    @staticmethod
    def _now() -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    for project in ProjectManifest.list_projects():
        print(json.dumps(project, ensure_ascii=False))

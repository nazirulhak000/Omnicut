"""Reprepare one saved editor project with streaming video cutout artifacts.

This never alters source media or deletes legacy cache. The project is saved
only after every required artifact is ready and its original bytes are backed
up under 06_Archive. Run from the repository root with a project JSON path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.background_isolation_video_worker import process_background_isolation_video  # noqa: E402
from scripts.config import PROJECTS_DIR  # noqa: E402


def _fingerprint(source: Path) -> str:
    stat = source.stat()
    payload = f"{source.as_posix()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def group_cutout_windows(clips: list[dict]) -> list[dict]:
    """Merge only overlapping windows with identical source and settings."""
    windows = []
    for index, clip in enumerate(clips):
        config = clip.get("background_isolation") or {}
        if config.get("enabled") is not True:
            continue
        source = Path(clip["source_path"])
        if not source.is_absolute():
            source = ROOT / source
        source = source.resolve(strict=True)
        start = float(clip.get("trim_start", 0))
        end = float(clip["trim_end"])
        if not (0 <= start < end):
            raise ValueError(f"invalid cutout trim in clip {index + 1}")
        settings = (str(source), config.get("engine", "rembg"),
                    config.get("model", "u2net"), config.get("quality", "balanced"),
                    config.get("temporal_mode", "legacy"),
                    int(clip.get("rotation") or 0))
        windows.append({"start": start, "end": end, "indices": [index],
                        "source": source, "config": config, "settings": settings})
    windows.sort(key=lambda item: (item["settings"], item["start"]))
    groups = []
    for window in windows:
        if (groups and groups[-1]["settings"] == window["settings"]
                and window["start"] <= groups[-1]["end"] + 1e-6):
            groups[-1]["end"] = max(groups[-1]["end"], window["end"])
            groups[-1]["indices"].extend(window["indices"])
        else:
            groups.append(dict(window))
    return groups


def reprepare_project(project_path: Path, *, dry_run: bool = False,
                      process_video=process_background_isolation_video) -> list[dict]:
    project_path = Path(project_path).resolve(strict=True)
    projects_root = Path(PROJECTS_DIR).resolve(strict=True)
    if not project_path.is_relative_to(projects_root) or project_path.name != "project.json":
        raise ValueError("project JSON must be under 03_Projects")
    original = project_path.read_bytes()
    project = json.loads(original.decode("utf-8"))
    groups = group_cutout_windows(project.get("clip_list", []))
    if not groups:
        raise ValueError("project has no enabled cutout clips")
    if dry_run:
        return groups

    cache_root = projects_root / ".cache"
    prepared = []
    for group in groups:
        source = group["source"]
        fingerprint = _fingerprint(source)
        duration = group["end"] - group["start"]
        print(f"Cutout video {len(prepared) + 1}/{len(groups)}: {source.name} {group['start']:.3f}–{group['end']:.3f}s", flush=True)

        def progress(event):
            if event.get("frame", 0) % 30 == 0:
                print(f"  {event['frame']} frames", flush=True)

        result = process_video(
            source, cache_root,
            {**group["config"], "artifact": {"id": None, "status": "missing"}},
            source_fingerprint=fingerprint,
            start=group["start"], duration=duration, fps=30, timebase="1/30",
            width=1080, height=1920, rotation=group["settings"][4],
            progress_callback=progress,
        )
        if result.get("status") != "ready":
            raise RuntimeError("video cutout artifact was not ready")
        manifest = json.loads((Path(result["output_directory"]) / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("source_fingerprint") != fingerprint or _fingerprint(source) != fingerprint:
            raise RuntimeError("source changed while preparing cutout")
        prepared.append((group, result, manifest))

    if project_path.read_bytes() != original:
        raise RuntimeError("project changed during cutout preparation; no project data was overwritten")
    for group, result, manifest in prepared:
        for index in group["indices"]:
            clip = project["clip_list"][index]
            config = dict(clip["background_isolation"])
            config["artifact"] = {
                "schema_version": 1, "id": result["artifact_id"], "status": "ready",
                "source_fingerprint": manifest["source_fingerprint"],
                "source_start": manifest["source_start"],
                "source_duration": manifest["source_duration"],
            }
            config["sequence"] = manifest
            clip["background_isolation"] = config

    archive_root = ROOT / "06_Archive" / "cutout_project_backups"
    if (ROOT.is_symlink() or archive_root.is_symlink()):
        raise ValueError("unsafe archive path")
    archive_root.mkdir(parents=True, exist_ok=True)
    backup = archive_root / f"{project_path.parent.name}-{uuid.uuid4().hex[:8]}.project.json"
    backup.write_bytes(original)
    if backup.read_bytes() != original:
        raise RuntimeError("project backup verification failed")
    temporary = project_path.with_name(f".project.json.cutout-{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if project_path.read_bytes() != original:
            raise RuntimeError("project changed before commit; backup retained")
        os.replace(temporary, project_path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Updated {project_path.name}; backup: {backup}", flush=True)
    return groups


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_json", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    for item in reprepare_project(arguments.project_json, dry_run=arguments.dry_run):
        print(f"{item['source'].name}: {item['start']:.3f}–{item['end']:.3f}s clips={item['indices']}")

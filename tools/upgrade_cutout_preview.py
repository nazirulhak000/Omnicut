"""Add verified alpha proxies to ready video artifacts without re-segmenting.

Does not change project.json or any master video. Publishes the optional proxy
before its manifest reference, with a byte-revision guard and manifest backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.background_isolation_video_worker import build_alpha_preview, VIDEO_NAMESPACE, VIDEO_NAME
from scripts.config import PROJECTS_DIR


def upgrade_artifact(directory: Path) -> dict:
    if directory.is_symlink() or directory.is_junction():
        raise ValueError("unsafe artifact directory")
    path = directory / "manifest.json"
    before = path.read_bytes()
    manifest = json.loads(before)
    if manifest.get("schema_version") != 2 or manifest.get("status") != "ready":
        raise ValueError("artifact is not a ready video")
    master = directory / VIDEO_NAME
    if master.is_symlink():
        raise ValueError("unsafe master")
    with master.open("rb") as handle:
        checksum = hashlib.file_digest(handle, "sha256").hexdigest()
    if checksum != manifest["sha256"]:
        raise ValueError("master checksum mismatch")
    if manifest.get("preview") and (directory / "preview.webm").is_file():
        return {"artifact_id": manifest["artifact_id"], "status": "existing"}
    numerator, denominator = map(int, manifest["fps"].split("/"))
    with tempfile.TemporaryDirectory(prefix=".proxy-upgrade-", dir=directory.parent) as temporary:
        staged = Path(temporary)
        shutil.copy2(master, staged / VIDEO_NAME)
        proxy = build_alpha_preview(staged / VIDEO_NAME, width=manifest["width"], height=manifest["height"],
                                    frame_count=manifest["frame_count"], fps=numerator / denominator)
        if proxy is None:
            return {"artifact_id": manifest["artifact_id"], "status": "master_already_small"}
        if path.read_bytes() != before:
            raise RuntimeError("artifact manifest changed during proxy generation")
        manifest["preview"] = {**proxy, "master_sha256": checksum, "fps": manifest["fps"]}
        (staged / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        backup = directory / "manifest.before-preview.json"
        if not backup.exists():
            backup.write_bytes(before)
        os.replace(staged / "preview.webm", directory / "preview.webm")
        os.replace(staged / "manifest.json", path)
    return {"artifact_id": manifest["artifact_id"], "status": "upgraded", "proxy_bytes": proxy["size_bytes"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project = json.loads(args.project.read_text(encoding="utf-8"))
    artifact_ids = {clip.get("background_isolation", {}).get("artifact", {}).get("id")
                    for clip in project.get("clip_list", [])}
    import re
    for artifact_id in sorted(artifact_ids - {None}):
        if not re.fullmatch(r"bgseq1-[0-9a-f]{16}", artifact_id):
            continue
        print(json.dumps(upgrade_artifact(PROJECTS_DIR / ".cache" / VIDEO_NAMESPACE / artifact_id)), flush=True)

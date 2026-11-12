"""Accept each project's current voiceover as the one its next render reuses.

A render stores a fingerprint of every artifact it produced. When a
voiceover.wav no longer matches the stored one (for example the files were
rewritten when the workspace moved to another machine), the next render from
the editor decides the voice is stale and synthesises a new take: an API
charge and a different performance from the one in the exported clip.

This tool re-stamps the fingerprints of such projects from the files that are
on disk now, through the same function a successful render uses
(render_jobs.finalize_incremental_render). It writes nothing but project.json,
and ProjectManifest keeps its usual rolling .bak copies.

Usage (from the repository root, with the project's .venv):
    python tools/restamp_voice_fingerprints.py            # list only
    python tools/restamp_voice_fingerprints.py --apply    # re-stamp
    python tools/restamp_voice_fingerprints.py --apply --project NAME
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import pipeline_context, render_jobs  # noqa: E402
from scripts.project_manifest import ProjectManifest  # noqa: E402

ARTIFACT = "voice_audio"


def voice_status(manifest: Dict[str, Any]) -> str:
    """'ok', 'stale', 'legacy' (no strict metadata) or 'no_voice' (nothing to accept)."""
    metadata = manifest.get("incremental_render") or {}
    if metadata.get("schema_version") != pipeline_context.INCREMENTAL_RENDER_SCHEMA_VERSION:
        return "legacy"
    current = pipeline_context._file_fingerprint(pipeline_context._manifest_artifact_path(manifest, ARTIFACT))
    if not current or not current.get("valid"):
        return "no_voice"
    fresh = pipeline_context.build_incremental_render_metadata(manifest)
    same_file = (metadata.get("artifact_fingerprints") or {}).get(ARTIFACT) == current
    # The stage fingerprint covers the inputs the voice was made from, which
    # include absolute paths: a moved workspace changes it with no file edit.
    same_inputs = (metadata.get("stage_fingerprints") or {}).get("voice") == fresh["stage_fingerprints"].get("voice")
    return "ok" if same_file and same_inputs else "stale"


def scan(only: Optional[str] = None) -> Dict[str, str]:
    names = [only] if only else sorted(p["project_name"] for p in ProjectManifest.list_projects())
    result = {}
    for name in names:
        manifest = ProjectManifest.load(name)
        result[name] = voice_status(manifest) if manifest else "missing"
    return result


def restamp(project_name: str) -> bool:
    """Re-stamp one project. True when its voice is accepted afterwards."""
    render_jobs.finalize_incremental_render(project_name)
    manifest = ProjectManifest.load(project_name)
    return bool(manifest) and voice_status(manifest) == "ok"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write project.json (default: list only)")
    parser.add_argument("--project", help="one project name instead of all")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    statuses = scan(args.project)
    stale = [name for name, status in statuses.items() if status == "stale"]
    counts: Dict[str, int] = {}
    for status in statuses.values():
        counts[status] = counts.get(status, 0) + 1
    print("โปรเจกต์ทั้งหมด:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for name in stale:
        print(f"  เสียงไม่ตรง fingerprint: {name}")
    if not args.apply:
        print("ยังไม่ได้เขียนอะไร — เพิ่ม --apply เพื่อประทับ fingerprint ใหม่")
        return 0

    failed = []
    for name in stale:
        try:
            accepted = restamp(name)
        except Exception as exc:  # noqa: BLE001 - one bad project must not stop the rest
            accepted = False
            print(f"  ❌ {name}: {exc}")
        if not accepted:
            failed.append(name)
    print(f"ประทับใหม่ {len(stale) - len(failed)} โปรเจกต์, ไม่สำเร็จ {len(failed)}")
    for name in failed:
        print(f"  ไม่สำเร็จ: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

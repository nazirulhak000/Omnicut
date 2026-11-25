"""
tools/batch_rerender_hook_safe_zone.py

Batch re-renders ALL unposted gadget clips in 03_Projects and 04_Exports/Ready_to_post
with the updated Hook Safe Zone coordinates (y = 260px for Hook Nameplate, y = 320px for Hook Line)
to clear the TikTok top search bar ("🔍 ค้นหา") and tabs ("Following | For You") completely.
"""

import sys
import json
import time
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.subtitle_engine import SubtitleEngine
from scripts.video_editor import VideoEditor


def main():
    print("=" * 70)
    print("🚀 OMNICUT PRO STUDIO: BATCH HOOK SAFE-ZONE RE-RENDER (ALL UNPOSTED)")
    print("   Target: ALL unposted gadget clips in 03_Projects and 04_Exports/Ready_to_post")
    print("   Goal: Move Hook text down safely (y >= 260px) below TikTok search bar")
    print("=" * 70)

    # 1. Collect all posted project names to protect them strictly
    posted_registry = set()
    reg_file = PROJECT_ROOT / "_Docs" / "export_registry.json"
    if reg_file.exists():
        try:
            reg_data = json.loads(reg_file.read_text(encoding="utf-8"))
            if isinstance(reg_data, list):
                for exp in reg_data:
                    if exp.get("status") == "posted":
                        posted_registry.add(exp.get("project_name"))
        except Exception:
            pass

    queue_file = PROJECT_ROOT / "_Docs" / "schedule_queue.json"
    if queue_file.exists():
        try:
            queue = json.loads(queue_file.read_text(encoding="utf-8"))
            for it in queue:
                if it.get("status") == "posted" and it.get("project_name"):
                    posted_registry.add(it.get("project_name"))
        except Exception:
            pass

    # 2. Find all projects in 03_Projects with an unposted export MP4
    projects = list((PROJECT_ROOT / "03_Projects").glob("*/project.json"))
    unposted_targets = []

    for p in projects:
        pname = p.parent.name
        if pname.startswith("_") or pname in posted_registry:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            art_mp4 = data.get("artifacts", {}).get("mp4_video", {}).get("path")
            if art_mp4:
                mp4_file = PROJECT_ROOT / art_mp4
                if mp4_file.exists() and "Posted" not in art_mp4:
                    unposted_targets.append({
                        "project_name": pname,
                        "project_file": p,
                        "video_path": mp4_file,
                        "manifest": data
                    })
        except Exception:
            pass

    unposted_targets.sort(key=lambda x: x["project_name"])
    total = len(unposted_targets)
    print(f"📦 Total unposted gadget projects found: {total}\n")

    cutoff_time = time.time() - 90 * 60  # 90 mins ago
    success_count = 0
    fail_count = 0
    start_time_all = time.time()

    for idx, item in enumerate(unposted_targets, start=1):
        pname = item["project_name"]
        vpath = item["video_path"]
        pfile = item["project_file"]
        pdir = pfile.parent

        # Check if already rendered recently
        if vpath.exists() and vpath.stat().st_mtime > cutoff_time and (pdir / "project.json.bak_hook").exists():
            print(f"[{idx}/{total}] ⏩ Skipping {pname} (already rendered with updated hook)")
            success_count += 1
            continue

        print(f"[{idx}/{total}] 🎬 Processing: {pname}")
        t0 = time.time()

        try:
            # 1. Update project.json overlays & heal legacy source paths
            manifest = json.loads(pfile.read_text(encoding="utf-8"))
            shutil.copy2(pfile, pdir / "project.json.bak_hook")

            for c in manifest.get("clip_list", []):
                sp = c.get("source_path") or c.get("file_path") or c.get("path")
                if sp and not Path(sp).exists():
                    if "Capcut" in sp:
                        rel = sp.split("Capcut\\")[-1].replace("\\", "/")
                        candidate = PROJECT_ROOT / rel
                        if candidate.exists():
                            c["source_path"] = str(candidate.resolve())

            overlays = manifest.get("overlays", [])
            for ov in overlays:
                ov_id = ov.get("id") or ""
                ov_kind = ov.get("kind") or ov.get("type") or ""
                ov_role = ov.get("role") or ""

                if ov_id == "ovl_hook" or ov_kind == "hook" or ov_kind == "hook_header":
                    ov["y"] = 260.0 / 1920.0
                    ov["anchor"] = "top"
                elif ov_id == "ovl_hook_line" or ov_role == "hook_line":
                    ov["y"] = 320.0 / 1920.0
                    ov["anchor"] = "middle"

            manifest["overlays"] = overlays
            manifest["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            pfile.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            # 2. Regenerate subtitles.ass
            ass_path = pdir / "subtitles.ass"
            SubtitleEngine.generate_ass(
                cues=manifest.get("micro_cues") or manifest.get("cues"),
                output_ass_path=str(ass_path),
                overlays=overlays,
                ghost_reveal=True,
                channel_identity_snapshot=manifest.get("channel_identity_snapshot"),
                font_name=manifest.get("font_name") or "IBM Plex Sans Thai",
                caption_position=manifest.get("caption_position") or "bottom",
                caption_color=manifest.get("caption_color"),
                caption_scale=manifest.get("caption_scale") or 1.0,
                style_preset=manifest.get("style_preset"),
                show_watermark=manifest.get("show_watermark", True),
            )

            # 3. Locate mixed audio
            mixed_audio = pdir / "mixed_audio_v1.wav"
            if not mixed_audio.exists():
                art_audio = manifest.get("artifacts", {}).get("mixed_audio", {}).get("path")
                if art_audio and (PROJECT_ROOT / art_audio).exists():
                    mixed_audio = PROJECT_ROOT / art_audio
                else:
                    raise FileNotFoundError(f"Mixed audio not found in {pdir}")

            # 4. Re-assemble and re-render MP4
            tmp_mp4 = vpath.with_name(vpath.stem + ".new_hook.mp4")
            VideoEditor.assemble_tiktok_video(
                raw_video_paths=[],
                total_duration=manifest.get("total_duration"),
                mixed_audio_path=str(mixed_audio),
                ass_subtitle_path=str(ass_path),
                output_mp4_path=str(tmp_mp4),
                cues=manifest.get("micro_cues") or manifest.get("cues"),
                clip_list=manifest.get("clip_list"),
                transitions=manifest.get("transitions"),
                effects=manifest.get("effects"),
                stickers=manifest.get("stickers"),
                style_preset=manifest.get("style_preset"),
                spotlight=manifest.get("spotlight"),
                background_isolation=manifest.get("background_isolation"),
            )

            if not tmp_mp4.exists() or tmp_mp4.stat().st_size < 1024 * 1024:
                raise RuntimeError(f"Render failed or file too small: {tmp_mp4}")

            # Atomically replace target MP4
            tmp_mp4.replace(vpath)

            # 5. Extract fresh thumbnail / preview webp for Gallery UI
            webp_path = vpath.with_suffix(".webp")
            cmd_webp = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", "2.0",
                "-i", str(vpath),
                "-vframes", "1",
                "-vf", "scale=540:960",
                str(webp_path)
            ]
            subprocess.run(cmd_webp, check=False)

            elapsed = time.time() - t0
            file_mb = vpath.stat().st_size / (1024 * 1024)
            print(f"   ✅ Done in {elapsed:.1f}s! ({file_mb:.1f} MB) -> {vpath.name}")
            success_count += 1

        except Exception as e:
            elapsed = time.time() - t0
            print(f"   ❌ FAILED in {elapsed:.1f}s: {e}")
            fail_count += 1

    total_time = time.time() - start_time_all
    print("\n" + "=" * 70)
    print(f"🏁 BATCH RE-RENDER FINISHED in {total_time/60:.1f} minutes!")
    print(f"   Success: {success_count}/{total}")
    print(f"   Failed:  {fail_count}/{total}")
    print("=" * 70)


if __name__ == "__main__":
    main()

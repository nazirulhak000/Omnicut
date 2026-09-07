"""
One-time migration: rename pre-existing CapCut project folders to prepend
their product_code (e.g. "essager_สายชาร์จแม่เหล็ก_ปัญหาก่อนใช้_1" -> "ESS01-ปัญหาก่อนใช้_1"),
matching the naming convention new projects now get automatically
(frontend/src/lib/projectName.js's buildProjectName).

Renames are hardcoded (not algorithmic) since this is a one-off fixup for
exactly 3 known, already-verified project folders -- not a general tool.

Out of scope (deliberately untouched): 04_Exports/ and its filenames.
Those exported .mp4/.webp files keep their old-name prefixes forever; only
the *_ass.py's secondary substring-matching fallback (matching an export
filename against a project name) weakens as a result -- accepted side effect.

Usage:
    python -m scripts.rename_projects_with_product_code            # dry-run (default)
    python -m scripts.rename_projects_with_product_code --apply    # actually mutates
"""

import sys
import json
import shutil
import datetime
from pathlib import Path

from scripts.config import PROJECTS_DIR, BASE_DIR
from scripts.project_manifest import ProjectManifest
from scripts.product_store import ProductStore

RENAMES = [
    # (old_folder_name, new_folder_name, product_id, angle_id)
    ("essager_สายชาร์จแม่เหล็ก_ปัญหาก่อนใช้_1", "ESS01-ปัญหาก่อนใช้_1", "20260905182956_2", "pain_point"),
    ("logitech_wave_keys_รีวิวสเปก_1", "LOG01-รีวิวสเปก_1", "20260904233315_1", "spec_review"),
    ("logitech_wave_keys_ปัญหาก่อนใช้_1", "LOG01-ปัญหาก่อนใช้_1", "20260904233315_1", "pain_point"),
    ("logitech_wave_keys_แกะกล่องว้าว_1", "LOG01-แกะกล่องว้าว_1", "20260904233315_1", "unboxing"),
]

ARTIFACT_KEYS_TO_REWRITE = ("voice_audio", "subtitles_ass", "mixed_audio")


def backup_products_json():
    products_path = BASE_DIR / "_Docs" / "products.json"
    bak_path = products_path.with_suffix(".json.bak")
    if bak_path.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        bak_path = products_path.with_suffix(f".json.bak.{timestamp}")
    shutil.copy2(products_path, bak_path)
    print(f"[backup] _Docs/products.json -> {bak_path.name}")


def process_entry(old_name, new_name, product_id, angle_id, apply: bool):
    old_dir = PROJECTS_DIR / old_name
    new_dir = PROJECTS_DIR / new_name

    print(f"\n=== {old_name!r} -> {new_name!r} ===")

    if new_dir.exists() and old_dir.exists():
        print(f"[SKIP-ERROR] both old and new folders exist — will not overwrite. Resolve manually.")
        return
    if new_dir.exists() and not old_dir.exists():
        print(f"[already renamed] {new_name!r} exists, {old_name!r} does not — proceeding to verify/fix JSON only.")
    elif not old_dir.exists() and not new_dir.exists():
        print(f"[SKIP] neither {old_name!r} nor {new_name!r} exists on disk — nothing to do.")
        return
    else:
        print(f"[rename] {old_dir} -> {new_dir}")
        if apply:
            old_dir.rename(new_dir)

    if not apply:
        print("[dry-run] would update project.json artifact paths + project_name")
        print("[dry-run] would update products.json angle.project_name + product.projects[]")
        return

    manifest = ProjectManifest.load(new_name)
    if manifest is None:
        print(f"[warn] could not load project.json for {new_name!r} — skipping manifest update.")
    else:
        artifacts = manifest.get("artifacts", {})
        rewritten = {}
        for key in ARTIFACT_KEYS_TO_REWRITE:
            entry = artifacts.get(key)
            if not entry or not entry.get("path"):
                continue
            old_path = Path(entry["path"])
            new_path = new_dir / old_path.name
            rewritten[key] = {**entry, "path": str(new_path)}
        # ProjectManifest.save()'s first positional param IS the folder-name
        # resolver, and it happens to share its name with the manifest's own
        # "project_name" field -- so that field can never be passed through
        # **fields (Python raises "multiple values" on any such call, since
        # save() re-loads the manifest from disk itself rather than taking
        # ours). Every existing caller in the repo only ever patches OTHER
        # fields for this exact reason. Update artifacts through save() as
        # normal, then fix just the stored project_name field by writing it
        # back out directly (same file save() would touch).
        ProjectManifest.save(new_name, artifacts=rewritten)
        fixed_manifest = ProjectManifest.load(new_name)
        fixed_manifest["project_name"] = new_name
        manifest_path = ProjectManifest.path_for(new_name)
        tmp_path = manifest_path.with_suffix(".json.rename_tmp")
        tmp_path.write_text(json.dumps(fixed_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(manifest_path)
        print(f"[project.json] project_name -> {new_name!r}, rewrote paths for: {list(rewritten.keys())}")

    product = ProductStore.get(product_id)
    if product is None:
        print(f"[warn] product {product_id!r} not found — skipping products.json update.")
        return

    angle = next((a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == angle_id), None)
    if angle is None:
        print(f"[warn] angle {angle_id!r} not found on product {product_id!r} — skipping angle update.")
    else:
        current_status = angle.get("status", "scripted")
        ProductStore.update_angle_status(
            product_id=product_id,
            angle_id=angle_id,
            status=current_status,
            project_name=new_name,
        )
        print(f"[products.json] angle {angle_id!r} project_name -> {new_name!r} (status kept as {current_status!r})")

    projects_list = product.get("projects", [])
    if old_name in projects_list:
        corrected = [new_name if p == old_name else p for p in projects_list]
        ProductStore.update(product_id, projects=corrected)
        print(f"[products.json] product.projects[] updated: {old_name!r} -> {new_name!r}")


def verify():
    print("\n=== Verification ===")
    for old_name, new_name, product_id, angle_id in RENAMES:
        new_dir = PROJECTS_DIR / new_name
        print(f"{new_name!r}: folder exists = {new_dir.exists()}")
        product = ProductStore.get(product_id)
        if product is None:
            print(f"  product {product_id!r} not found")
            continue
        angle = next((a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == angle_id), None)
        if angle is None:
            print(f"  angle {angle_id!r} not found")
            continue
        print(f"  angle.project_name = {angle.get('project_name')!r}, status = {angle.get('status')!r}, video_url unchanged = {angle.get('video_url')!r}")


def main():
    apply = "--apply" in sys.argv
    print(f"Mode: {'APPLY (mutating)' if apply else 'DRY-RUN (no changes)'}")

    if apply:
        backup_products_json()

    for old_name, new_name, product_id, angle_id in RENAMES:
        process_entry(old_name, new_name, product_id, angle_id, apply)

    if apply:
        verify()
    else:
        print("\nRe-run with --apply to actually rename folders and update JSON.")


if __name__ == "__main__":
    main()
